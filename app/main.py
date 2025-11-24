from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import api, crud
from app.db import get_session, init_db

app = FastAPI(title="Game Engagement Score")
templates = Jinja2Templates(directory="app/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session=Depends(get_session)):
    games = await crud.list_games(session)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "games": games,
        },
    )
