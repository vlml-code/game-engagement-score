# Game Engagement Score

FastAPI reference stack for storing game engagement information. It uses SQLAlchemy with an async
engine (ready for PostgreSQL) and ships with basic CRUD APIs plus a minimal UI shell to view stored
records.

## Features
- Async FastAPI application with auto-migrated metadata on startup
- SQLAlchemy models for games, achievements, guides, parsed guide content, HowLongToBeat (HLTB) time
  entries, and engagement scores
- CRUD endpoints under `/api` for all entities
- Pico.css-powered UI at `/` to preview games and relationships

## Getting started
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure the database URL (defaults to SQLite):
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/game_db"
   ```
3. Run the API server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open the interactive docs at `http://127.0.0.1:8000/docs` and use the `/api/*` routes to add
   data. The landing page at `/` renders a simple dashboard of stored games.

## Steam API configuration

To import achievements and guides directly from the Steam Web API, provide a Steam API key via an environment variable or `.env` file:

```
STEAM_API_KEY=your_api_key
STEAM_REQUEST_INTERVAL=0.35  # optional delay between Steam API calls
```

Use the `/api/steam/import` endpoint with a comma or newline separated list of app IDs to batch import games, achievements, and guide metadata.

## Data model
The app tracks:
- **Game**: core metadata such as title, genre, and platform.
- **Achievement**: in-game milestones linked to a game.
- **Guide**: external or internal guide metadata.
- **ParsedGuideContent**: processed guide text and section counts.
- **HLTBTime**: HowLongToBeat timing estimates.
- **EngagementScore**: derived score entries with methods and notes.
