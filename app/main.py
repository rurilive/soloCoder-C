from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.routers import pages, search, stream, playlists

settings = get_settings()

templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import Base, engine
    from app.models import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

app.include_router(pages.router)
app.include_router(search.router)
app.include_router(stream.router)
app.include_router(playlists.router)
