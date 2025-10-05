# ai-neighborhood-watch
AI-Powered Neighborhood Watch
This project is a real-time neighborhood watch application that uses AI to categorize incident reports submitted by users on a map. It also features an AI-generated daily audio briefing summarizing the day's events.

Tech Stack:

Frontend: HTML, Tailwind CSS, Leaflet.js

Backend: Python (Flask)

Database: PostgreSQL

AI: Google Gemini, ElevenLabs

Quick setup
1. Copy `.env.example` to `.env` and fill in `DATABASE_URL`.
2. (Optional) Add `GEMINI_API_KEY` to enable automatic categorization of reports.
3. From the `backend/` folder, create the DB tables:

	python db_setup.py

4. Install dependencies:

	pip install -r backend/requirements.txt

5. Run the backend:

	python backend/app.py

6. Open `frontend/index.html` in a browser (or serve it via a static server) and use the map.