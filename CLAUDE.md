## Project: GitStats
## Stack
- Backend: FastAPI + Python, port 8000
- Frontend: React + Vite + Tailwind, port 5173
- DB: PostgreSQL via Supabase (asyncpg + SQLAlchemy)
- LLM: Google Gemini Flash via google-generativeai
- Auth: GitHub OAuth2

## Commands
- cd backend && source venv/bin/activate && uvicorn main:app --reload
- cd frontend && npm run dev

## Key files
- backend/scraper.py → GitHub API scraping logic
- backend/classifier.py → Gemini classification logic
- backend/database.py → DB models and queries
- backend/genres.py → hardcoded genres and tags

## Conventions
- All GitHub API calls go through scraper.py
- All Gemini calls go through classifier.py
- All DB access goes through database.py
- Use async/await throughout the backend
