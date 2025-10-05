# backend/app.py

import os
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import psycopg2
from dotenv import load_dotenv

# Import Gemini SDK optionally so the app can run even if the package isn't installed
# Prefer the newer `from google import genai` client if available; otherwise fall back to
# the older `google.generativeai` package.
GENAI_AVAILABLE = False
GENAI_NEW = False
genai = None
genai_client = None
try:
    # New SDK entrypoint
    from google import genai as _genai_new
    GENAI_AVAILABLE = True
    GENAI_NEW = True
    genai = _genai_new
except Exception:
    try:
        import google.generativeai as _genai_old
        GENAI_AVAILABLE = True
        GENAI_NEW = False
        genai = _genai_old
    except Exception:
        genai = None
        GENAI_AVAILABLE = False

# NEW: Optional ElevenLabs import
ELEVEN_AVAILABLE = False
try:
    from elevenlabs.client import ElevenLabs
    ELEVEN_AVAILABLE = True
except Exception:
    ELEVEN_AVAILABLE = False

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini only if a key is provided and the SDK is available
AI_ENABLED = False
if not GENAI_AVAILABLE:
    print("No supported genai package installed; AI features disabled. Install 'google-generativeai' or the new 'google-genai' SDK.")
else:
    if GEMINI_API_KEY:
        try:
            if GENAI_NEW:
                os.environ.setdefault('GOOGLE_API_KEY', GEMINI_API_KEY)
                try:
                    genai_client = genai.Client(http_options={'api_version': 'v1alpha'})
                    AI_ENABLED = True
                    print('New genai client created: AI features enabled (v1alpha).')
                except Exception as e:
                    print(f"!!! NEW GENAI CLIENT ERROR: {e}")
                    AI_ENABLED = False
            else:
                genai.configure(api_key=GEMINI_API_KEY)
                AI_ENABLED = True
                print('google.generativeai configured: AI features enabled.')
        except Exception as e:
            print(f"!!! GEMINI CONFIG ERROR: {e}")
            AI_ENABLED = False
    else:
        print("No GEMINI_API_KEY found in environment; running without AI categorization.")


def validate_gemini_key_quick():
    """Optional quick check to validate the Gemini API key."""
    if not GENAI_AVAILABLE or not GEMINI_API_KEY:
        print(f"GENAI_AVAILABLE: {GENAI_AVAILABLE}, GEMINI_API_KEY: {'***' if GEMINI_API_KEY else 'None'}")
        return
    global AI_ENABLED, MODEL_NAME, genai_client
    MODEL_NAME = None
    candidates_new = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-flash-latest']
    candidates_old = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-flash-latest']
    print("Validating Gemini API key with a lightweight test request...")
    print(f"GENAI_NEW: {GENAI_NEW}, genai_client: {genai_client is not None}")
    if GENAI_AVAILABLE and GENAI_NEW and genai_client:
        for name in candidates_new:
            try:
                resp = genai_client.models.generate_content(model=name, contents='Respond with one word: Theft or Other')
                txt = getattr(resp, 'text', None) or (resp.get('candidates')[0].get('content') if isinstance(resp, dict) and resp.get('candidates') else None)
                print(f"New-client model candidate '{name}' responded.")
                MODEL_NAME = name
                AI_ENABLED = True
                print(f"Selected model (new genai): {MODEL_NAME}")
                break
            except Exception as e:
                print(f"New-client model '{name}' failed: {e}")
                continue
    elif GENAI_AVAILABLE and not GENAI_NEW:
        for name in candidates_old:
            try:
                m = genai.GenerativeModel(name)
                resp = m.generate_content('Respond with one word: Theft or Other')
                print(f"Old-client model candidate '{name}' responded.")
                MODEL_NAME = name
                AI_ENABLED = True
                print(f"Selected model (old genai): {MODEL_NAME}")
                break
            except Exception as e:
                print(f"Old-client model '{name}' failed: {e}")
                continue
    if not MODEL_NAME:
        print('No working model found with provided key; AI features disabled.')
        AI_ENABLED = False

# Validate API key if available
if GEMINI_API_KEY:
    validate_gemini_key_quick()
else:
    print("No GEMINI_API_KEY found - using fallback categorization only.")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"!!! DATABASE CONNECTION ERROR: {e}")
        return None

# --- NEW: Podcast Feature Functions ---

def fetch_todays_reports():
    """Return list of report dicts created today (UTC)."""
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            # Fetch reports from the last 24 hours for a "daily" briefing
            cur.execute("SELECT description, latitude, longitude, category FROM reports WHERE created_at >= NOW() - INTERVAL '1 day' ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [{'description': r[0], 'latitude': r[1], 'longitude': r[2], 'category': r[3] or 'Uncategorized'} for r in rows]
    except Exception as e:
        print('Error fetching today\'s reports:', e)
        return []
    finally:
        if conn: conn.close()

def generate_podcast_script(reports):
    """Ask Gemini to create a short podcast script summarizing the reports."""
    if not reports:
        return "Good morning! It's been a quiet 24 hours in the neighborhood, with no new incidents reported. Remember to stay vigilant, and have a safe day."

    bullets = "\n".join([f"- {r['category']}: {r['description']}" for r in reports])
    prompt = (
        "You are a calm, friendly community radio host. Your tone is reassuring and informative. Create a 60-90 second morning briefing script summarizing the following neighborhood reports. "
        "Start with a friendly greeting. State the total number of incidents. Briefly describe each one in a single sentence. Do not mention coordinates. "
        "End with a short, positive safety tip. For example: 'Remember to lock your car doors' or 'Keep an eye out for your neighbors'.\n\n"
        f"Reports ({len(reports)} total):\n{bullets}"
    )
    
    if not AI_ENABLED:
        return "AI features are currently disabled. Unable to generate briefing."

    try:
        if GENAI_AVAILABLE and GENAI_NEW and genai_client:
            model_name = globals().get('MODEL_NAME') or 'gemini-2.0-flash'
            resp = genai_client.models.generate_content(model=model_name, contents=prompt)
            text = getattr(resp, 'text', None) or (resp.get('candidates')[0].get('content') if isinstance(resp, dict) and resp.get('candidates') else None)
            return (text or '').strip()
        elif GENAI_AVAILABLE and not GENAI_NEW:
            m = genai.GenerativeModel('gemini-2.0-flash')
            resp = m.generate_content(prompt)
            return resp.text.strip()
    except Exception as e:
        print('Gemini script generation failed:', e)
        return "Unable to generate today's briefing due to an internal error."

def synthesize_audio_elevenlabs(script_text):
    """Use ElevenLabs to synthesize audio (returns bytes of an mp3)."""
    if not ELEVEN_AVAILABLE or not os.getenv('ELEVENLABS_API_KEY'):
        print('ElevenLabs SDK not installed or API key not found; cannot synthesize audio.')
        return None
    try:
        # Use the new client-based approach
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        
        print('Generating audio with ElevenLabs...')
        audio = client.text_to_speech.convert(
            text=script_text,
            voice_id='21m00Tcm4TlvDq8ikWAM',  # Rachel voice
            model_id='eleven_multilingual_v2'
        )
        
        # Convert generator to bytes
        audio_bytes = b''.join(audio)
        print(f'Successfully generated {len(audio_bytes)} bytes of audio')
        return audio_bytes
        
    except Exception as e:
        print('ElevenLabs synthesis failed:', e)
        return None

# --- NEW: Podcast API Endpoint ---

@app.route('/api/podcast/today', methods=['GET'])
def podcast_today():
    """The main AI pipeline: Fetches reports, generates a script, then generates audio."""
    print("Request received for today's podcast.")
    
    # 1. Fetch data from the database
    reports = fetch_todays_reports()
    print(f"Found {len(reports)} reports for the briefing.")
    
    # 2. Send data to Gemini to generate a script
    script = generate_podcast_script(reports)
    print(f"Generated script: \"{script[:100]}...\"")
    
    # 3. Send the script to ElevenLabs to generate audio
    audio_bytes = synthesize_audio_elevenlabs(script)
    
    if audio_bytes:
        print("Successfully generated audio bytes. Sending to client.")
        # Send the MP3 audio bytes back to the client
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/mpeg', as_attachment=False)
    else:
        print("Failed to generate audio.")
        return jsonify({'error': 'Failed to generate audio', 'script': script}), 500

# --- Existing Report Endpoints (Unchanged from your version) ---

def categorize_report(description):
    """Uses Gemini to categorize an incident description."""
    if not AI_ENABLED:
        print("AI disabled — using local keyword heuristic for categorization.")
        s = (description or '').lower()
        if 'theft' in s or 'stolen' in s or 'robbery' in s or 'stole' in s or 'steal' in s: return 'Theft'
        if 'vandal' in s or 'graffiti' in s: return 'Vandalism'
        if 'accident' in s or 'crash' in s: return 'Accident'
        if 'fire' in s or 'smoke' in s: return 'Fire'
        if 'suspicious' in s: return 'Suspicious Activity'
        return 'Other'

    try:
        prompt = (f"Categorize this incident into ONE of: Theft, Vandalism, Accident, Fire, Suspicious Activity, or Other.\n\n" f"'{description}'")
        
        response = None
        if GENAI_AVAILABLE and GENAI_NEW and genai_client:
            model_name = globals().get('MODEL_NAME') or 'gemini-2.0-flash'
            response = genai_client.models.generate_content(model=model_name, contents=prompt)
        elif GENAI_AVAILABLE and not GENAI_NEW:
            m = genai.GenerativeModel('gemini-2.0-flash')
            response = m.generate_content(prompt)

        category = "Uncategorized"
        if response:
            raw_text = getattr(response, 'text', None) or (response.get('candidates')[0].get('content') if isinstance(response, dict) and response.get('candidates') else None)
            category = (raw_text or "Uncategorized").strip().title()
        
        print(f"Gemini categorized report as: {category}")
        return category
    except Exception as e:
        print(f"!!! GEMINI ERROR: {e}")
        return "Uncategorized"

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Fetches all reports from the database."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    reports = []
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, description, latitude, longitude, category, created_at FROM reports ORDER BY created_at DESC')
            for row in cur.fetchall():
                reports.append({"id": row[0], "description": row[1], "latitude": row[2], "longitude": row[3], "category": row[4] or "Uncategorized", "created_at": row[5].isoformat()})
        return jsonify(reports)
    except Exception as e:
        return jsonify({"error": "Failed to fetch reports"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/reports', methods=['POST'])
def create_report():
    """Creates a new report and saves it to the database."""
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cur:
            category = categorize_report(data['description'])
            cur.execute(
                'INSERT INTO reports (description, latitude, longitude, category) VALUES (%s, %s, %s, %s) RETURNING id, created_at',
                (data['description'], data['latitude'], data['longitude'], category)
            )
            new_id, created_at = cur.fetchone()
            conn.commit()
            
            new_report = {'id': new_id, 'description': data['description'], 'latitude': data['latitude'], 'longitude': data['longitude'], 'category': category, 'created_at': created_at.isoformat()}
            return jsonify(new_report), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": "Failed to create report"}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)