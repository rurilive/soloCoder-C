from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from app.database import engine, Base
from app.routers.documents import router as documents_router
from app.routers.upload import router as upload_router
from app.routers.folders import router as folders_router
from app.routers.search import router as search_router


template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0,
)


def _escapejs(value):
    """Escape string for use in JavaScript strings."""
    if value is None:
        return ""
    value = str(value)
    value = value.replace('\\', '\\\\')
    value = value.replace("'", "\\'")
    value = value.replace('"', '\\"')
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value


jinja_env.filters['escapejs'] = _escapejs


def render_template(template_name: str, context: dict = None) -> HTMLResponse:
    if context is None:
        context = {}
    template = jinja_env.get_template(template_name)
    return HTMLResponse(template.render(**context))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="文档管理平台",
    description="支持上传解析Markdown、doc、excel、ppt文件，自动生成层级文档站",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(folders_router, prefix="/api/folders", tags=["folders"])
app.include_router(search_router, prefix="/api/search", tags=["search"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return render_template("index.html", {
        "request": request,
        "query": "",
    })


@app.get("/document/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: int):
    return render_template("document.html", {
        "request": request,
        "doc_id": doc_id,
        "query": "",
    })


@app.get("/folder/{folder_id}", response_class=HTMLResponse)
async def folder_detail(request: Request, folder_id: int):
    return render_template("folder.html", {
        "request": request,
        "folder_id": folder_id,
        "query": "",
    })


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    return render_template("search.html", {
        "request": request,
        "query": q,
    })
