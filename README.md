# ai-neighborhood-watch

AI-Powered Neighborhood Watch

This is a small, local project that demonstrates: user-submitted incident reports shown on a map, automatic AI categorization of those reports, and a short AI-generated daily audio briefing.

Tech stack
- Frontend: single-page HTML, Tailwind CSS, Leaflet.js
- Backend: Python + Flask
- Database: PostgreSQL
- AI: Google Gemini (Generative Language) for categorization and script generation; ElevenLabs for text-to-speech

Podcast (multi-voice)
- The project now includes a short, conversational "Neighborhood Briefing" podcast generated from today's reports.
- The briefing is produced as a short dialogue between two hosts (Ava — female, Mateo — male). The backend attempts multi-voice synthesis by alternating speech segments and concatenating them; if that fails it falls back to single-voice audio.
- When the backend returns audio it will set the `X-Podcast-Hosts` response header so the frontend can show which hosts were used.

Highlights
- POST /api/reports — submit a new report (the backend will categorize it and store a `category` column)
- GET /api/reports — returns recent reports including `category`
- GET /api/podcast/today — generates an AI script for today's reports and returns an MP3 audio briefing (requires ElevenLabs API key)

Quickstart (local development)

1) Prerequisites
- Python 3.9+ (3.10 recommended)
- PostgreSQL running and reachable (set `DATABASE_URL` accordingly)
- Optional: a virtualenv

2) Copy environment template

```bash
cp .env.example backend/.env
# edit backend/.env and fill values (DATABASE_URL and any optional provider keys; do NOT commit secrets)
```

3) Install Python deps

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Note: `backend/requirements.txt` includes `pydub`. `pydub` uses `ffmpeg` to load and export audio formats like MP3. On macOS install ffmpeg with Homebrew:

```bash
brew install ffmpeg
```

4) Create DB table

```bash
cd backend
python db_setup.py
```

5) Run backend

```bash
# from project root
python backend/app.py
```

6) Run frontend

- The frontend is a static `frontend/index.html`. Open it in a browser or serve it with a static server (for example: `python -m http.server` in the `frontend/` folder).

Environment variables (backend/.env)
- DATABASE_URL — postgres connection string (required)
- Gemini/API key — optional; when present the backend will try to call Google Generative models for categorization and script generation. Add as `GEMINI_API_KEY=<your_key>` to `backend/.env` (do not commit).
- ElevenLabs API key — optional; required to synthesize audio for `/api/podcast/today`. Add as `ELEVENLABS_API_KEY=<your_key>` to `backend/.env` (do not commit).
- (Alternative for Google) GOOGLE_APPLICATION_CREDENTIALS — path to a service account JSON if you use application-default credentials for Generative Language

Security & secrets
- A lightweight pre-commit hook is included in the repository at `.githooks/pre-commit` to help block accidental commits that contain obvious secret patterns. To enable it locally run:

```bash
git config core.hooksPath .githooks
```

Notes about Google Gemini (Generative Language)
- The backend supports both a direct API key approach and the Google application-default / service-account credential approach. Which one to use depends on your Google Cloud setup.
- Typical errors when calling models: "404 models/<name> is not found" usually means the project or API key does not have access to that model or the Generative Language API is not enabled. If you see that:
  - Ensure the Generative Language API is enabled in Google Cloud Console for the project owning the credentials
  - Confirm the credentials (API key or service account) are correct and belong to the intended project
  - If using a service account JSON, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`


Database / Admin utilities
- The codebase includes helper scripts in `backend/` (for example `db_setup.py`). You may add a small admin route to re-run categorization on historical rows if you want to re-process old data after enabling Gemini.

Testing the podcast endpoint
- Start the backend (ensure venv is active):

```bash
python backend/app.py
```

- Probe the endpoint to confirm audio and check the hosts header:

```bash
curl -I http://127.0.0.1:5001/api/podcast/today
# Look for `Content-Type: audio/mpeg` and `X-Podcast-Hosts: Ava,Mateo` (if multi-voice was used)
```

Troubleshooting
- If pydub import fails or you see ffmpeg errors, ensure `ffmpeg` is installed and available on PATH. On macOS:

```bash
brew install ffmpeg
```

- If ElevenLabs fails for a voice ID the backend will try alternate voices or fall back to single-voice. Check backend logs for details.
