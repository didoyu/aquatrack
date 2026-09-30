# AquaTrack Frontend (React + Vite)

1. Install Node.js 20+ (nodejs.org), then in this folder: `npm install`
2. `copy .env.example .env` (Windows) — set `VITE_API_URL` to your backend, default `http://127.0.0.1:8000/api`
3. Start the backend (`python manage.py runserver`) in another terminal, then `npm run dev`
4. Open http://localhost:5173 and log in with `demo@aquatrack.local` / `demo12345`

If you use another port or host, add it to `CORS_ALLOWED_ORIGINS` in the backend `.env`.
Files: `src/api.js` (login tokens + requests), `src/App.jsx` (all screens), `src/index.css` (theme).
