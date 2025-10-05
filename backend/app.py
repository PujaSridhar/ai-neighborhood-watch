# backend/app.py

import os
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import psycopg2
from dotenv import load_dotenv
import snowflake.connector

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
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')

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


def get_snowflake_connection():
    """Establish a connection to Snowflake using environment variables."""
    if not SNOWFLAKE_ACCOUNT or not SNOWFLAKE_USER or not SNOWFLAKE_PASSWORD:
        print('Snowflake credentials not fully configured; Snowflake disabled.')
        return None
    try:
        ctx = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        return ctx
    except Exception as e:
        print('Snowflake connection failed:', e)
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
    """Generate a natural-sounding, conversational podcast script summarizing reports.

    The script is formatted as a short dialogue between two hosts to add variety and make
    the audio feel more like a community podcast rather than a single monologue.
    """
    if not reports:
        return (
            "[Ava] Good morning, friends — it's a quiet day in our neighborhood. No new incidents reported in the last 24 hours. "
            "Stay safe, check your locks, and look out for each other. Have a great day!"
        )

    # Convert reports into short sentences and ensure punctuation
    report_lines = []
    for r in reports:
        cat = r.get('category') or 'Other'
        desc = (r.get('description') or '').strip()
        if desc and not desc.endswith(('.', '!', '?')):
            desc += '.'
        report_lines.append({'cat': cat, 'desc': desc})

    # Compose an intentionally conversational dialogue where Ava (female) opens and leads,
    # and Mateo (male) follows with short reactions, questions, and clarifications.
    parts = []
    parts.append("[Ava] Good morning — welcome to the Neighborhood Briefing. I'm Ava.")
    parts.append("[Mateo] And I'm Mateo. Here are the highlights from the last 24 hours.")

    for idx, item in enumerate(report_lines, start=1):
        # Ava summarizes, Mateo reacts or asks a clarifying question
        parts.append(f"[Ava] Report {idx}: {item['cat']}. {item['desc']}")
        parts.append("[Mateo] That's concerning — do we know if anyone was hurt?")
        parts.append("[Ava] Not reported; authorities were notified where appropriate.")

    parts.append("[Mateo] Quick reminder: secure your vehicles and keep an eye on neighbors.")
    parts.append("[Ava] Thanks for tuning in. We'll be back with another update tomorrow. Stay safe!")

    script = '\n'.join(parts)

    # If AI is available, ask Gemini to make the dialogue natural and conversational but keep the
    # two-host structure (Ava=female, Mateo=male). Ask for concise phrasing suitable for an audio
    # briefing (about 60-90 seconds).
    if not AI_ENABLED:
        return script

    try:
        prompt = (
            "You are an experienced radio editor. Rewrite the following dialogue to sound natural, "
            "warm, and conversational for a short 60-90 second neighborhood podcast. Keep two hosts: "
            "Ava (female, warm, reassuring) and Mateo (male, calm, curious). Keep exchanges brief and "
            "make the hosts discuss the reports — do not invent new incidents. Output only the cleaned dialogue." 
            "\n\nOriginal dialogue:\n" + script
        )

        if GENAI_AVAILABLE and GENAI_NEW and genai_client:
            model_name = globals().get('MODEL_NAME') or 'gemini-2.0-flash'
            resp = genai_client.models.generate_content(model=model_name, contents=prompt)
            text = getattr(resp, 'text', None) or (resp.get('candidates')[0].get('content') if isinstance(resp, dict) and resp.get('candidates') else None)
            return (text or script).strip()
        elif GENAI_AVAILABLE and not GENAI_NEW:
            m = genai.GenerativeModel('gemini-2.0-flash')
            resp = m.generate_content(prompt)
            return resp.text.strip()
    except Exception as e:
        print('Gemini script generation failed (fallback to local):', e)
        return script

def synthesize_audio_elevenlabs(script_text, reports=None):
    """Synthesize multi-voice podcast using ElevenLabs.

    Strategy:
    - Split the script into short sentences.
    - Synthesize each sentence (or small group) with alternating voices to emulate a multi-host podcast.
    - Concatenate segments using pydub and return a single MP3 bytes buffer.

    Falls back to single-voice synthesis if ElevenLabs or pydub is unavailable or an error occurs.
    """
    if not ELEVEN_AVAILABLE or not os.getenv('ELEVENLABS_API_KEY'):
        print('ElevenLabs SDK not installed or API key not found; cannot synthesize audio.')
        return None, []

    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
    except Exception as e:
        print('Failed to create ElevenLabs client:', e)
        return None, []

    # Choose a small set of voice IDs to alternate between. These are common demo voices; if an ID
    # isn't available to your account the ElevenLabs call will raise and we'll gracefully fallback.
    # Map voice IDs to friendly display names
    voice_map = [
        ('21m00Tcm4TlvDq8ikWAM', 'Ava'),  # warm host
        ('EXAVITQu4vr4xnSDxMaL', 'Mateo')  # co-host
    ]
    voice_ids = [v[0] for v in voice_map]


    # Helper: single-segment synthesis
    def synth_segment(text, voice_id):
        try:
            gen = client.text_to_speech.convert(text=text, voice_id=voice_id, model_id='eleven_multilingual_v2')
            audio_bytes = b''.join(gen)
            return audio_bytes
        except Exception as e:
            print(f'ElevenLabs segment synth failed for voice {voice_id}:', e)
            raise

    # Try to use pydub for concatenation; if not available, fall back to single-call synthesis
    use_pydub = True
    try:
        from pydub import AudioSegment
    except Exception as e:
        print('pydub not available or failed to import; falling back to single-voice output.', e)
        use_pydub = False

    # Split script into sentences (naive split) and group small chunks to avoid many tiny requests.
    import re
    sentences = [s.strip() for s in re.split(r'(?<=[\.\!\?])\s+', script_text.strip()) if s.strip()]
    if not sentences:
        sentences = [script_text.strip()]

    # Group sentences into chunks of 1-3 sentences
    chunks = []
    i = 0
    while i < len(sentences):
        chunk = sentences[i]
        # try to keep chunk length reasonable
        if i + 1 < len(sentences):
            chunk += ' ' + sentences[i + 1]
            i += 2
        else:
            i += 1
        chunks.append(chunk)

    # If pydub available, synth each chunk with alternating voices and concatenate
    if use_pydub:
        segments = []
        for idx, chunk in enumerate(chunks):
            voice = voice_ids[idx % len(voice_ids)]
            try:
                b = synth_segment(chunk, voice)
            except Exception:
                # if a voice fails, try the other voice
                try:
                    voice = voice_ids[(idx + 1) % len(voice_ids)]
                    b = synth_segment(chunk, voice)
                except Exception:
                    print('All voice attempts failed for chunk; falling back to single-voice full synthesis')
                    use_pydub = False
                    break

            # load into AudioSegment
            try:
                seg = AudioSegment.from_file(io.BytesIO(b), format='mp3')
                segments.append(seg)
            except Exception as e:
                print('Failed to load segment into pydub AudioSegment:', e)
                use_pydub = False
                break

        if use_pydub and segments:
            combined = segments[0]
            for s in segments[1:]:
                combined += s

            out_buf = io.BytesIO()
            combined.export(out_buf, format='mp3')
            audio_bytes = out_buf.getvalue()
            print(f'Generated multi-voice podcast of {len(audio_bytes)} bytes')
            return audio_bytes, [n for (_, n) in voice_map][:len(segments) if len(segments) < len(voice_map) else len(voice_map)]

    # Fallback: single-call synthesis (previous behavior)
    try:
        print('Falling back to single-voice ElevenLabs synthesis...')
        gen = client.text_to_speech.convert(text=script_text, voice_id=voice_ids[0], model_id='eleven_multilingual_v2')
        audio_bytes = b''.join(gen)
        return audio_bytes, [voice_map[0][1]]
    except Exception as e:
        print('ElevenLabs single-voice synthesis failed:', e)
        return None, []

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
    
    # 3. Send the script to ElevenLabs to generate audio (may return chosen host names)
    audio_bytes, host_names = synthesize_audio_elevenlabs(script)

    if audio_bytes:
        print("Successfully generated audio bytes. Sending to client.")
        resp = send_file(io.BytesIO(audio_bytes), mimetype='audio/mpeg', as_attachment=False)
        # Expose chosen hosts via header so frontend can show them
        if host_names:
            resp.headers['X-Podcast-Hosts'] = ','.join(host_names)
        return resp
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


@app.route('/api/trends', methods=['GET'])
def get_trends():
    """Query Snowflake to fetch a simple trend: busiest hour of day for reports."""
    sf = get_snowflake_connection()
    if not sf:
        return jsonify({'error': 'Snowflake not configured or connection failed'}), 500

    try:
        with sf.cursor() as cur:
            # The user-created table name is REPORTS and has timestamp_tz column
            query = """
            SELECT EXTRACT(HOUR FROM timestamp_tz) as hour_of_day, COUNT(*) as report_count
            FROM REPORTS
            GROUP BY hour_of_day
            ORDER BY report_count DESC
            LIMIT 1
            """
            cur.execute(query)
            row = cur.fetchone()
            if not row:
                return jsonify({'busiest_hour': None, 'reports': 0})
            busiest_hour = int(row[0]) if row[0] is not None else None
            reports_count = int(row[1])
            return jsonify({'busiest_hour': busiest_hour, 'reports': reports_count})
    except Exception as e:
        print('Error querying Snowflake for trends:', e)
        return jsonify({'error': 'Failed to query Snowflake'}), 500
    finally:
        try:
            sf.close()
        except Exception:
            pass

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
            # Dual-write to Snowflake (optional)
            try:
                sf = get_snowflake_connection()
                if sf:
                    try:
                        with sf.cursor() as sfc:
                            insert_sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.REPORTS (id, description, latitude, longitude, category, timestamp_tz) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
                            sfc.execute(insert_sql, (int(new_id), data['description'], float(data['latitude']), float(data['longitude']), category))
                            sf.commit()
                    except Exception as e:
                        print('Snowflake insert failed:', e)
                    finally:
                        try:
                            sf.close()
                        except Exception:
                            pass

            except Exception as e:
                print('Snowflake dual-write error:', e)

            new_report = {'id': new_id, 'description': data['description'], 'latitude': data['latitude'], 'longitude': data['longitude'], 'category': category, 'created_at': created_at.isoformat()}
            return jsonify(new_report), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": "Failed to create report"}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)