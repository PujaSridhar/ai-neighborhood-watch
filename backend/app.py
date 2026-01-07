# backend/app.py

import os
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import psycopg2
from dotenv import load_dotenv
import snowflake.connector
import feedparser
import requests

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

# --- Failure tracking for Gemini to avoid repeated 429s ---
GEMINI_FAILURE_COUNT = 0
GEMINI_LAST_FAILURE_AT = None
GEMINI_FAILURE_THRESHOLD = int(os.getenv('GEMINI_FAILURE_THRESHOLD', '5'))
GEMINI_FAILURE_RESET_SECONDS = int(os.getenv('GEMINI_FAILURE_RESET_SECONDS', str(60 * 5)))

def gemini_failure_register(exc=None):
    """Record a Gemini failure and return whether AI should be temporarily disabled."""
    global GEMINI_FAILURE_COUNT, GEMINI_LAST_FAILURE_AT
    try:
        GEMINI_FAILURE_COUNT += 1
        GEMINI_LAST_FAILURE_AT = datetime.utcnow()
        print(f'Gemini failure #{GEMINI_FAILURE_COUNT}: {exc}')
    except Exception:
        pass

def gemini_failure_should_disable():
    """Return True if Gemini failures exceeded threshold and cooldown hasn't expired."""
    global GEMINI_FAILURE_COUNT, GEMINI_LAST_FAILURE_AT
    if GEMINI_FAILURE_COUNT >= GEMINI_FAILURE_THRESHOLD:
        if not GEMINI_LAST_FAILURE_AT:
            return True
        elapsed = (datetime.utcnow() - GEMINI_LAST_FAILURE_AT).total_seconds()
        if elapsed < GEMINI_FAILURE_RESET_SECONDS:
            return True
        # reset after cooldown
        GEMINI_FAILURE_COUNT = 0
        GEMINI_LAST_FAILURE_AT = None
        return False
    return False

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


# save_report removed with Google News ingestion rollback

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
    # If many Gemini failures happened recently, temporarily avoid AI calls
    if gemini_failure_should_disable():
        print('Gemini temporarily disabled due to repeated failures; using local script.')
        return script

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

        if gemini_failure_should_disable():
            print('Gemini temporarily disabled at generation time; returning local script.')
            return script

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
        gemini_failure_register(e)
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


# --- NEW: Google News / RSS ingestion ---
# Google News ingestion removed

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
    if gemini_failure_should_disable():
        print('Gemini temporarily disabled for categorization; using local heuristic.')
        return (lambda s: ( 'Theft' if 'theft' in s or 'stolen' in s or 'robbery' in s or 'stole' in s or 'steal' in s else
                           'Vandalism' if 'vandal' in s or 'graffiti' in s else
                           'Accident' if 'accident' in s or 'crash' in s else
                           'Fire' if 'fire' in s or 'smoke' in s else
                           'Suspicious Activity' if 'suspicious' in s else 'Other'))((description or '').lower())

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
        gemini_failure_register(e)
        return "Uncategorized"


def geocode_place_text(text):
    """Optional simple geocode using Nominatim (OpenStreetMap). Enable with NOMINATIM_ENABLED=1.

    Returns (lat, lon) or (None, None).
    """
    # geocoding removed as part of Google News ingestion rollback
    return None, None


def local_categorize(description):
    """Local keyword-based categorization (explicitly avoids Gemini)."""
    s = (description or '').lower()
    if 'theft' in s or 'stolen' in s or 'robbery' in s or 'stole' in s or 'steal' in s: return 'Theft'
    if 'vandal' in s or 'graffiti' in s: return 'Vandalism'
    if 'accident' in s or 'crash' in s: return 'Accident'
    if 'fire' in s or 'smoke' in s: return 'Fire'
    if 'suspicious' in s or 'suspicion' in s: return 'Suspicious Activity'
    return 'Other'


@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """Return a short report of Gemini availability and a lightweight test (non-destructive).

    This does not perform heavy requests and will avoid making many calls.
    """
    status = {
        'GENAI_AVAILABLE': GENAI_AVAILABLE,
        'GENAI_NEW': GENAI_NEW,
        'GEMINI_API_KEY_set': bool(GEMINI_API_KEY),
        'AI_ENABLED': AI_ENABLED,
        'MODEL_NAME': globals().get('MODEL_NAME') if 'MODEL_NAME' in globals() else None,
    }
    # Try a very small safety test if AI is enabled and hasn't been recently failing
    if GENAI_AVAILABLE and AI_ENABLED and not gemini_failure_should_disable():
        try:
            if GENAI_NEW and genai_client:
                resp = genai_client.models.generate_content(model=globals().get('MODEL_NAME') or 'gemini-2.0-flash', contents='Respond with one word: Theft or Other')
                txt = getattr(resp, 'text', None) or (resp.get('candidates')[0].get('content') if isinstance(resp, dict) and resp.get('candidates') else None)
                status['light_test'] = (txt or '').strip()
            elif GENAI_AVAILABLE and not GENAI_NEW:
                m = genai.GenerativeModel(globals().get('MODEL_NAME') or 'gemini-2.0-flash')
                resp = m.generate_content('Respond with one word: Theft or Other')
                status['light_test'] = getattr(resp, 'text', None)
        except Exception as e:
            status['light_test_error'] = str(e)
            gemini_failure_register(e)
    else:
        status['light_test'] = 'skipped'

    return jsonify(status)




@app.route('/api/news', methods=['GET'])
def get_news():
    """Fetches local news from Google RSS."""
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    # Default to New Brunswick if no location
    query = "new brunswick neighborhood crime"
    if lat and lon:
        # In a real app, we'd reverse geocode here. For now, let's just use a generic "local" query or keep it simple.
        # Or we can try to use the coordinates in the query if Google supports it (it supports "near ...").
        # Let's stick to the default query for stability, or maybe "neighborhood crime"
        pass

    rss_url = os.getenv('NEWS_RSS_URL') or 'https://news.google.com/rss/search?q=new+brunswick+neighborhood+crime&hl=en-US&gl=US&ceid=US:en'
    
    try:
        resp = requests.get(rss_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({'error': f'Failed to fetch RSS feed: {e}'}), 502

    feed = feedparser.parse(resp.content)
    entries = feed.entries or []
    
    news_items = []
    for entry in entries[:20]:
        news_items.append({
            'title': entry.get('title', ''),
            'summary': entry.get('summary', ''),
            'url': entry.get('link', ''),
            'published': entry.get('published', '')
        })
        
    return jsonify(news_items)

@app.route('/api/news/fetch', methods=['POST'])
def news_fetch_server():
    """Server-side RSS importer that explicitly avoids using Gemini for categorization.

    POST optional JSON { "rss_url": "..." }
    """
    payload = request.get_json(silent=True) or {}
    rss_url = payload.get('rss_url') or os.getenv('NEWS_RSS_URL') or 'https://news.google.com/rss/search?q=new+brunswick+neighborhood+crime&hl=en-US&gl=US&ceid=US:en'

    try:
        resp = requests.get(rss_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({'error': f'Failed to fetch RSS feed: {e}'}), 502

    feed = feedparser.parse(resp.content)
    entries = feed.entries or []
    max_process = int(os.getenv('NEWS_MAX_ITEMS', '25'))
    created = []
    skipped = []

    # Load existing descriptions to dedupe
    conn = get_db_connection()
    existing = set()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT description FROM reports')
                for row in cur.fetchall():
                    if row and row[0]: existing.add(row[0].strip().lower())
        except Exception as e:
            print('Failed to read existing reports for dedupe:', e)
        finally:
            conn.close()

    for entry in entries[:max_process]:
        title = entry.get('title') if isinstance(entry, dict) else getattr(entry, 'title', '')
        summary = entry.get('summary') if isinstance(entry, dict) else getattr(entry, 'summary', '')
        link = entry.get('link') if isinstance(entry, dict) else getattr(entry, 'link', '')
        desc = (title or '').strip()
        if summary and summary not in desc:
            desc = desc + ' — ' + (summary[:280] + '...' if len(summary) > 280 else summary)

        key = desc.strip().lower()
        if key in existing:
            skipped.append({'title': title, 'reason': 'duplicate'})
            continue

        # Try to get georss content
        lat = None; lon = None
        try:
            if isinstance(entry, dict):
                if entry.get('geo_lat') and entry.get('geo_long'):
                    lat = float(entry.get('geo_lat')); lon = float(entry.get('geo_long'))
                elif entry.get('georss_point'):
                    parts = entry.get('georss_point').split()
                    if len(parts) >= 2:
                        lat = float(parts[0]); lon = float(parts[1])
            else:
                if getattr(entry, 'geo_lat', None) and getattr(entry, 'geo_long', None):
                    lat = float(getattr(entry, 'geo_lat')); lon = float(getattr(entry, 'geo_long'))
        except Exception:
            lat = None; lon = None

        if lat is None or lon is None:
            try:
                lat = float(os.getenv('NEWS_DEFAULT_LAT', '40.5008'))
                lon = float(os.getenv('NEWS_DEFAULT_LON', '-74.4478'))
            except Exception:
                lat, lon = 40.5008, -74.4478

        # Use local categorization to avoid Gemini usage
        category = local_categorize(desc)

        # Truncate description to avoid DB column size errors
        max_len = int(os.getenv('REPORT_DESC_MAX_LEN', '100'))
        desc_trimmed = (desc or '')[:max_len]

        # Insert into Postgres
        conn = get_db_connection()
        if not conn:
            skipped.append({'title': title, 'reason': 'db_connect_failed'})
            continue
        try:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO reports (description, latitude, longitude, category) VALUES (%s, %s, %s, %s) RETURNING id, created_at', (desc_trimmed, float(lat), float(lon), category))
                new_id, created_at = cur.fetchone()
                conn.commit()
                created.append({'id': new_id, 'title': title, 'link': link})
                existing.add(key)
                # Optional dual-write to Snowflake (best-effort)
                try:
                    sf = get_snowflake_connection()
                    if sf:
                        try:
                            with sf.cursor() as sfc:
                                insert_sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.REPORTS (id, description, latitude, longitude, category, timestamp_tz) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
                                sfc.execute(insert_sql, (int(new_id), desc_trimmed, float(lat), float(lon), category))
                                sf.commit()
                        except Exception as e:
                            print('Snowflake insert failed (news fetch):', e)
                        finally:
                            try: sf.close()
                            except Exception: pass
                except Exception:
                    pass
        except Exception as e:
            print('Failed to insert news report:', e)
            try:
                conn.rollback()
            except Exception:
                pass
            skipped.append({'title': title, 'reason': 'insert_failed'})
        finally:
            try: conn.close()
            except Exception: pass

    return jsonify({'created': created, 'skipped': skipped, 'processed': min(len(entries), max_process)}), 200

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
    """Query Snowflake for trends, falling back to Postgres if Snowflake is unavailable."""
    
    # 1. Try Snowflake
    sf = get_snowflake_connection()
    if sf:
        try:
            with sf.cursor() as cur:
                query = """
                SELECT EXTRACT(HOUR FROM timestamp_tz) as hour_of_day, COUNT(*) as report_count
                FROM REPORTS
                GROUP BY hour_of_day
                ORDER BY report_count DESC
                LIMIT 1
                """
                cur.execute(query)
                row = cur.fetchone()
                if row:
                    busiest_hour = int(row[0]) if row[0] is not None else None
                    reports_count = int(row[1])
                    return jsonify({'busiest_hour': busiest_hour, 'reports': reports_count, 'source': 'snowflake'})
        except Exception as e:
            print('Snowflake query failed, falling back to Postgres:', e)
        finally:
            try: sf.close()
            except Exception: pass

    # 2. Fallback to Postgres
    print("Using Postgres fallback for trends...")
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with conn.cursor() as cur:
            # Postgres equivalent query
            query = """
            SELECT EXTRACT(HOUR FROM created_at) as hour_of_day, COUNT(*) as report_count
            FROM reports
            GROUP BY hour_of_day
            ORDER BY report_count DESC
            LIMIT 1
            """
            cur.execute(query)
            row = cur.fetchone()
            if not row:
                return jsonify({'busiest_hour': None, 'reports': 0, 'source': 'postgres'})
            
            busiest_hour = int(row[0]) if row[0] is not None else None
            reports_count = int(row[1])
            return jsonify({'busiest_hour': busiest_hour, 'reports': reports_count, 'source': 'postgres'})
            
    except Exception as e:
        print('Postgres trends query failed:', e)
        return jsonify({'error': 'Failed to fetch trends'}), 500
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
                        except Exception: pass
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
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)