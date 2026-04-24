import os
import uuid
import math
from datetime import datetime
from typing import List, Optional
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


@app.on_event("startup")
def startup_event():
    init_db()


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


def build_pagination_url(page: int, current_view: str, **kwargs) -> str:
    if current_view == "search" and kwargs.get("search_query"):
        return f"/?q={kwargs.get('search_query')}&page={page}"
    elif current_view == "tag" and kwargs.get("current_tag"):
        return f"/tag/{kwargs.get('current_tag')}?page={page}"
    elif current_view == "date" and kwargs.get("current_date"):
        return f"/date/{kwargs.get('current_date')}?page={page}"
    else:
        return f"/?page={page}"


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
    
    db.delete(photo)
    db.commit()
    
    return RedirectResponse(url="/", status_code=303)
