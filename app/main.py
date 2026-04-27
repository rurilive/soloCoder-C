from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routers.documents import router as documents_router
from app.routers.upload import router as upload_router
from app.routers.folders import router as folders_router
from app.routers.search import router as search_router


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
templates = Jinja2Templates(directory="app/templates")

app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(folders_router, prefix="/api/folders", tags=["folders"])
app.include_router(search_router, prefix="/api/search", tags=["search"])


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/document/{doc_id}")
async def document_detail(request: Request, doc_id: int):
    return templates.TemplateResponse("document.html", {"request": request, "doc_id": doc_id})


@app.get("/folder/{folder_id}")
async def folder_detail(request: Request, folder_id: int):
    return templates.TemplateResponse("folder.html", {"request": request, "folder_id": folder_id})


@app.get("/search")
async def search_page(request: Request, q: str = ""):
    return templates.TemplateResponse("search.html", {"request": request, "query": q})
