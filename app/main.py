import os
import uuid
from datetime import datetime
from typing import List, Optional
from collections import defaultdict

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    photos = db.query(Photo).order_by(Photo.created_at.desc()).all()
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "all",
        },
    ))


@app.get("/tag/{tag}", response_class=HTMLResponse)
async def photos_by_tag(tag: str, request: Request, db: Session = Depends(get_db)):
    photos = db.query(Photo).filter(Photo.tags.like(f"%{tag}%")).order_by(Photo.created_at.desc()).all()
    filtered_photos = [p for p in photos if tag in p.get_tags_list()]
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": filtered_photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "tag",
            "current_tag": tag,
        },
    ))


@app.get("/date/{year_month}", response_class=HTMLResponse)
async def photos_by_date(year_month: str, request: Request, db: Session = Depends(get_db)):
    try:
        year, month = map(int, year_month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    photos = db.query(Photo).order_by(Photo.created_at.desc()).all()
    filtered_photos = [
        p for p in photos 
        if p.created_at.year == year and p.created_at.month == month
    ]
    tags = get_all_tags(db)
    date_groups = get_date_groups(db)
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "photos": filtered_photos,
            "tags": tags,
            "date_groups": date_groups,
            "current_view": "date",
            "current_date": year_month,
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
