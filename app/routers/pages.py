from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "音乐在线播放平台"},
    )


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = Query(None, description="搜索关键词"),
    type: str = Query("all", description="搜索类型"),
):
    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "title": "搜索 - 音乐在线播放平台",
            "query": q or "",
            "search_type": type,
        },
    )


@router.get("/playlists", response_class=HTMLResponse)
async def playlists_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="playlists.html",
        context={
            "title": "我的歌单 - 音乐在线播放平台",
        },
    )


@router.get("/playlists/{playlist_id}", response_class=HTMLResponse)
async def playlist_detail_page(
    request: Request,
    playlist_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="playlist_detail.html",
        context={
            "title": "歌单详情 - 音乐在线播放平台",
            "playlist_id": playlist_id,
        },
    )
