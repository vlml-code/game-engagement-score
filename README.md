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
- OpenAI-powered detection of the main-story completion achievement
- Guide HTML parsing to persist guide text for downstream prompts
- HowLongToBeat lookup for main-story average time with throttling
- Engagement scoring with error notes surfaced in the UI

## Getting started
1. Copy the sample environment and fill in the credentials you have:
   ```bash
   cp .env.example .env
   # then edit .env to set API keys, throttling intervals, and database URL
   ```
2. Install dependencies (SQLite is the default and requires no extra drivers):
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the database URL (defaults to SQLite) if you need something different:
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/game_db"
   ```
   If you want to use PostgreSQL, install a driver separately depending on your URL scheme:
   ```bash
   # Async PostgreSQL (matches the example URL above)
   pip install "asyncpg>=0.30"  # compiled wheels are available for recent Python versions

   # Alternative async driver backed by psycopg 3
   pip install "psycopg[binary]>=3.2"
   export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/game_db"
   ```
4. Run the API server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open the interactive docs at `http://127.0.0.1:8000/docs` and use the `/api/*` routes to add
   data. The landing page at `/` renders an interactive dashboard that can call the APIs directly.

## Steam API configuration

To import achievements and guides directly from the Steam Web API, provide a Steam API key via an environment variable or `.env` file:

```
STEAM_API_KEY=your_api_key
STEAM_REQUEST_INTERVAL=0.35  # optional delay between Steam API calls
```

Use the `/api/steam/import` endpoint with a comma or newline separated list of app IDs to batch import games, achievements, and guide metadata.

## Analysis pipeline

1. Configure OpenAI and HowLongToBeat (optional but recommended):

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4o-mini             # optional
export OPENAI_REQUEST_INTERVAL=2.0          # optional delay between OpenAI calls
export GUIDE_REQUEST_INTERVAL=1.0           # optional delay between guide fetches
export HLTB_REQUEST_INTERVAL=1.2            # optional delay between HLTB searches
```

2. Trigger the analysis for a game by calling `POST /api/games/{id}/analyze`.

The pipeline will:
- Parse guide URLs and store their text.
- Ask OpenAI to tag the main-story completion achievement using achievements and guide excerpts.
- Fetch the main-story average time from HowLongToBeat.
- Compute an engagement score using the provided formula and store notes when data is missing.
- Display the latest results and any errors on the landing page.

## Data model
The app tracks:
- **Game**: core metadata such as title, genre, and platform.
- **Achievement**: in-game milestones linked to a game.
- **Guide**: external or internal guide metadata.
- **ParsedGuideContent**: processed guide text and section counts.
- **HLTBTime**: HowLongToBeat timing estimates.
- **EngagementScore**: derived score entries with methods and notes.
