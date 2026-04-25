import os
import uuid
import math
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from sqlalchemy.orm import Session
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from app.database import get_db, init_db, Photo


app = FastAPI(title="简易相册")

os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/thumbnails", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 12

_vector_store = None
_embedding_service = None
_embedding_enabled = False


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from app.vector_store import VectorStore
        _vector_store = VectorStore()
    return _vector_store


def get_embedding_service():
    global _embedding_service, _embedding_enabled
    if _embedding_service is None and _embedding_enabled:
        try:
            from app.embedding_service import EmbeddingService
            _embedding_service = EmbeddingService()
        except Exception as e:
            print(f"Embedding service not available: {e}")
            _embedding_enabled = False
    return _embedding_service


@app.on_event("startup")
def startup_event():
    global _embedding_enabled
    init_db()
    
    from dotenv import load_dotenv
    load_dotenv()
    
    if os.getenv("OPENAI_API_KEY"):
        _embedding_enabled = True
        print("Vector search enabled with OpenAI API")
    else:
        print("OpenAI API key not found. Vector search is disabled.")
        print("Please set OPENAI_API_KEY in .env file to enable vector search.")


def generate_thumbnail(image_path: str, thumbnail_path: str, size: tuple = (300, 300)):
    with Image.open(image_path) as img:
        img.thumbnail(size, Image.LANCZOS)
        img.save(thumbnail_path)


def get_unique_filename(original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4().hex}{ext}"


def get_all_tags(db: Session) -> List[str]:
    photos = db.query(Photo).all()
    tags_set = set()
    for photo in photos:
        for tag in photo.get_tags_list():
            tags_set.add(tag)
    return sorted(list(tags_set))


def get_date_groups(db: Session) -> list:
    photos = db.query(Photo).order_by(Photo.created_at.desc()).all()
    groups = defaultdict(list)
    for photo in photos:
        date_key = photo.created_at.strftime("%Y-%m")
        groups[date_key].append(photo)
    return sorted(
        [{"date": k, "photos": v, "count": len(v)} for k, v in groups.items()],
        key=lambda x: x["date"],
        reverse=True
    )


def render_template(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(**context)


def get_pagination_info(total: int, page: int, page_size: int) -> dict:
    total_pages = math.ceil(total / page_size)
    has_prev = page > 1
    has_next = page < total_pages
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_page": page - 1 if has_prev else None,
        "next_page": page + 1 if has_next else None,
        "start_item": (page - 1) * page_size + 1 if total > 0 else 0,
        "end_item": min(page * page_size, total),
    }


def add_to_vector_store(
    photo_id: int,
    description: str,
    tags: str,
) -> bool:
    global _embedding_enabled
    if not _embedding_enabled:
        return False
    
    embedding_service = get_embedding_service()
    if embedding_service is None:
        return False
    
    text_embedding = embedding_service.embed_description(description, tags)
    
    if text_embedding:
        vector_store = get_vector_store()
        vector_store.add_entry(
            photo_id=photo_id,
            text_embedding=text_embedding,
            description=description,
            tags=tags,
        )
        return True
    
    return False


def remove_from_vector_store(photo_id: int):
    global _embedding_enabled
    if not _embedding_enabled:
        return
    
    try:
        vector_store = get_vector_store()
        vector_store.remove_entry(photo_id)
    except Exception as e:
        print(f"Error removing from vector store: {e}")


def vector_search(
    query: str,
    top_k: int = 20,
) -> List[Tuple[int, float]]:
    global _embedding_enabled
    if not _embedding_enabled:
        return []
    
    embedding_service = get_embedding_service()
    if embedding_service is None:
        return []
    
    query_embedding = embedding_service.embed_text(query)
    if query_embedding is None:
        return []
    
    vector_store = get_vector_store()
    results = vector_store.search_combined(query_embedding, top_k=top_k)
    return results


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
):
    query = db.query(Photo)
    
    if q:
        query = query.filter(Photo.description.like(f"%{q}%"))
    
    total = query.count()
    
    photos = (
        query.order_by(Photo.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "search" if q else "all",
            "search_query": q,
            "pagination": pagination,
            "vector_search_enabled": _embedding_enabled,
        },
    ))


@app.get("/vector-search", response_class=HTMLResponse)
async def vector_search_page(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="向量搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
):
    global _embedding_enabled
    
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    
    if not _embedding_enabled:
        return HTMLResponse(content=render_template(
            "vector_search.html",
            {
                "request": request,
                "photos": [],
                "tags": tags,
                "date_groups": date_groups,
                "current_view": "vector_search",
                "search_query": q,
                "pagination": get_pagination_info(0, 1, PAGE_SIZE),
                "vector_search_enabled": False,
                "error_message": "向量搜索未启用。请设置 OPENAI_API_KEY 环境变量。",
            },
        ))
    
    if not q:
        return HTMLResponse(content=render_template(
            "vector_search.html",
            {
                "request": request,
                "photos": [],
                "tags": tags,
                "date_groups": date_groups,
                "current_view": "vector_search",
                "search_query": q,
                "pagination": get_pagination_info(0, 1, PAGE_SIZE),
                "vector_search_enabled": True,
            },
        ))
    
    search_results = vector_search(q, top_k=100)
    
    total = len(search_results)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_results = search_results[start_idx:end_idx]
    
    photo_ids_with_score = {photo_id: score for photo_id, score in paged_results}
    photos = db.query(Photo).filter(Photo.id.in_(list(photo_ids_with_score.keys()))).all()
    
    photos_sorted = sorted(
        photos,
        key=lambda p: photo_ids_with_score.get(p.id, 0),
        reverse=True
    )
    
    photos_with_scores = []
    for photo in photos_sorted:
        score = photo_ids_with_score.get(photo.id, 0)
        photos_with_scores.append({
            "photo": photo,
            "similarity": round(score * 100, 1),
        })
    
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    return HTMLResponse(content=render_template(
        "vector_search.html",
        {
            "request": request,
            "photos": photos_with_scores,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "vector_search",
            "search_query": q,
            "pagination": pagination,
            "vector_search_enabled": True,
        },
    ))


@app.get("/tag/{tag}", response_class=HTMLResponse)
async def photos_by_tag(
    tag: str,
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
):
    photos = db.query(Photo).filter(Photo.tags.like(f"%{tag}%")).order_by(Photo.created_at.desc()).all()
    filtered_photos = [p for p in photos if tag in p.get_tags_list()]
    
    total = len(filtered_photos)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_photos = filtered_photos[start_idx:end_idx]
    
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": paged_photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "tag",
            "current_tag": tag,
            "pagination": pagination,
            "vector_search_enabled": _embedding_enabled,
        },
    ))


@app.get("/date/{year_month}", response_class=HTMLResponse)
async def photos_by_date(
    year_month: str,
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
):
    try:
        year, month = map(int, year_month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    photos = db.query(Photo).order_by(Photo.created_at.desc()).all()
    filtered_photos = [
        p for p in photos 
        if p.created_at.year == year and p.created_at.month == month
    ]
    
    total = len(filtered_photos)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_photos = filtered_photos[start_idx:end_idx]
    
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": paged_photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "date",
            "current_date": year_month,
            "pagination": pagination,
            "vector_search_enabled": _embedding_enabled,
        },
    ))


@app.post("/upload")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    tags: str = Form(default=""),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
):
    if not file.content_type.startswith("image/"):
        return HTMLResponse("只能上传图片文件", status_code=400)
    
    filename = get_unique_filename(file.filename)
    file_path = os.path.join("uploads", filename)
    thumbnail_filename = f"thumb_{filename}"
    thumbnail_path = os.path.join("uploads", "thumbnails", thumbnail_filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        generate_thumbnail(file_path, thumbnail_path)
    except Exception as e:
        os.remove(file_path)
        return HTMLResponse(f"处理图片失败: {e}", status_code=500)
    
    photo = Photo(
        filename=filename,
        thumbnail_filename=thumbnail_filename,
        tags=tags.strip(),
        description=description.strip(),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    
    add_to_vector_store(
        photo_id=photo.id,
        description=description.strip(),
        tags=tags.strip(),
    )
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/photo/{photo_id}", response_class=HTMLResponse)
async def photo_detail(photo_id: int, request: Request, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return HTMLResponse(content=render_template(
        "detail.html",
        {"request": request, "photo": photo},
    ))


@app.post("/photo/{photo_id}/delete")
async def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    file_path = os.path.join("uploads", photo.filename)
    thumbnail_path = os.path.join("uploads", "thumbnails", photo.thumbnail_filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    
    remove_from_vector_store(photo_id)
    
    db.delete(photo)
    db.commit()
    
    return RedirectResponse(url="/", status_code=303)
