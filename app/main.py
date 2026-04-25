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

from app.database import get_db, init_db, Photo, User
from app.auth import get_current_user, get_current_user_required, get_token_from_request
from app.logger import get_logger
from app.config import config

logger = get_logger()

app = FastAPI(title="简易相册")

BASE_UPLOAD_DIR = config.UPLOAD_DIR

os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=BASE_UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory="templates")

PAGE_SIZE = config.PAGE_SIZE

_vector_store = None
_embedding_service = None
_embedding_enabled = False


def get_user_upload_dir(user_id: int) -> str:
    user_dir = os.path.join(BASE_UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    thumbnails_dir = os.path.join(user_dir, "thumbnails")
    os.makedirs(thumbnails_dir, exist_ok=True)
    return user_dir


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
            logger.error(f"Embedding service not available: {e}")
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
        logger.info("Vector search enabled with OpenAI API")
    else:
        logger.warning("OpenAI API key not found. Vector search is disabled.")
        logger.warning("Please set OPENAI_API_KEY in .env file to enable vector search.")


def generate_thumbnail(image_path: str, thumbnail_path: str, size: tuple = (300, 300)):
    with Image.open(image_path) as img:
        img.thumbnail(size, Image.LANCZOS)
        img.save(thumbnail_path)


def get_unique_filename(original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4().hex}{ext}"


def get_all_tags(db: Session, user_id: int) -> List[str]:
    photos = db.query(Photo).filter(Photo.user_id == user_id).all()
    tags_set = set()
    for photo in photos:
        for tag in photo.get_tags_list():
            tags_set.add(tag)
    return sorted(list(tags_set))


def get_date_groups(db: Session, user_id: int) -> list:
    photos = db.query(Photo).filter(Photo.user_id == user_id).order_by(Photo.created_at.desc()).all()
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
    
    logger.info(f"\n{'='*60}")
    logger.info(f"[add_to_vector_store] 开始添加到向量存储")
    logger.info(f"{'='*60}")
    logger.info(f"  - photo_id: {photo_id}")
    logger.info(f"  - description: '{description}'")
    logger.info(f"  - tags: '{tags}'")
    logger.info(f"  - _embedding_enabled: {_embedding_enabled}")
    
    if not _embedding_enabled:
        logger.warning(f"[add_to_vector_store] ⚠️ 向量搜索未启用，跳过")
        return False
    
    logger.debug(f"[add_to_vector_store] 获取 embedding_service...")
    embedding_service = get_embedding_service()
    if embedding_service is None:
        logger.error(f"[add_to_vector_store] ❌ embedding_service 为 None")
        return False
    
    logger.debug(f"[add_to_vector_store] ✅ 获取 embedding_service 成功")
    
    text_embedding = embedding_service.embed_description(description, tags)
    
    if text_embedding:
        logger.info(f"[add_to_vector_store] ✅ 成功生成嵌入向量")
        logger.debug(f"  - 维度: {len(text_embedding)}")
        logger.debug(f"  - 前3个值: {text_embedding[:3]}")
        
        logger.debug(f"[add_to_vector_store] 获取 vector_store...")
        vector_store = get_vector_store()
        
        vector_store.add_entry(
            photo_id=photo_id,
            text_embedding=text_embedding,
            description=description,
            tags=tags,
        )
        logger.info(f"[add_to_vector_store] ✅ 已保存到向量存储")
        return True
    else:
        logger.warning(f"[add_to_vector_store] ⚠️ 嵌入向量生成失败 (可能是因为 description 和 tags 都为空)")
    
    return False


def remove_from_vector_store(photo_id: int):
    global _embedding_enabled
    if not _embedding_enabled:
        return
    
    try:
        vector_store = get_vector_store()
        vector_store.remove_entry(photo_id)
    except Exception as e:
        logger.error(f"Error removing from vector store: {e}")


def vector_search(
    query: str,
    top_k: int = 20,
) -> List[Tuple[int, float]]:
    global _embedding_enabled
    
    logger.info(f"\n{'='*60}")
    logger.info(f"[vector_search] ========== 开始向量搜索 ==========")
    logger.info(f"{'='*60}")
    logger.info(f"  - 搜索词: '{query}'")
    logger.info(f"  - top_k: {top_k}")
    logger.info(f"  - _embedding_enabled: {_embedding_enabled}")
    
    if not _embedding_enabled:
        logger.warning(f"[vector_search] ⚠️ 向量搜索未启用，返回空结果")
        return []
    
    logger.debug(f"\n[vector_search] 步骤1: 获取 embedding_service...")
    embedding_service = get_embedding_service()
    if embedding_service is None:
        logger.error(f"[vector_search] ❌ embedding_service 为 None")
        return []
    logger.debug("[vector_search] ✅ embedding_service 获取成功")
    
    logger.debug(f"\n[vector_search] 步骤2: 生成查询嵌入向量...")
    logger.debug(f"  - 输入文本: '{query}'")
    query_embedding = embedding_service.embed_text(query)
    
    if query_embedding is None:
        logger.error(f"[vector_search] ❌ 查询嵌入向量生成失败")
        return []
    
    logger.info(f"[vector_search] ✅ 查询嵌入向量生成成功")
    logger.debug(f"  - 维度: {len(query_embedding)}")
    logger.debug(f"  - 前5个值: {query_embedding[:5]}")
    logger.debug(f"  - 后5个值: {query_embedding[-5:]}")
    
    logger.debug(f"\n[vector_search] 步骤3: 获取 vector_store...")
    vector_store = get_vector_store()
    logger.debug("[vector_search] ✅ vector_store 获取成功")
    
    logger.info(f"\n[vector_search] 步骤4: 检查向量存储内容...")
    logger.info(f"  - 总条目数: {len(vector_store._entries)}")
    logger.info(f"  - 文本嵌入数: {len(vector_store._text_embeddings)}")
    logger.info(f"  - 图像嵌入数: {len(vector_store._image_embeddings)}")
    
    if len(vector_store._entries) == 0:
        logger.warning(f"[vector_search] ⚠️ 向量存储中没有任何条目！")
        logger.warning(f"  可能的原因:")
        logger.warning(f"  1. 上传照片时没有添加描述/标签")
        logger.warning(f"  2. 上传照片时 OpenAI API 调用失败")
        logger.warning(f"  3. 向量存储文件损坏或未正确保存")
    
    logger.info(f"\n[vector_search] 所有条目详情:")
    for pid, entry in vector_store._entries.items():
        has_text = pid in vector_store._text_embeddings
        has_image = pid in vector_store._image_embeddings
        
        if has_text:
            emb = vector_store._text_embeddings[pid]
            emb_info = f"维度={len(emb)}, min={emb.min():.4f}, max={emb.max():.4f}"
        else:
            emb_info = "无"
        
        logger.info(f"  [{pid}] description='{entry.description}', tags='{entry.tags}'")
        logger.info(f"       text_embedding={has_text}, image_embedding={has_image}")
        logger.info(f"       文本嵌入信息: {emb_info}")
    
    logger.info(f"\n[vector_search] 步骤5: 执行搜索...")
    results = vector_store.search_combined(query_embedding, top_k=top_k)
    
    logger.info(f"\n[vector_search] 步骤6: 搜索结果汇总:")
    logger.info(f"  - 结果数量: {len(results)}")
    
    if results:
        logger.info(f"\n  完整结果列表:")
        for i, (pid, score) in enumerate(results):
            entry = vector_store._entries.get(pid)
            desc = entry.description if entry else "N/A"
            tags = entry.tags if entry else "N/A"
            logger.info(f"    {i+1}. photo_id={pid}, 相似度={score:.6f} ({score*100:.2f}%)")
            logger.info(f"       description='{desc}', tags='{tags}'")
    else:
        logger.warning(f"  ⚠️ 没有找到任何匹配的结果")
        logger.warning(f"     可能的原因:")
        logger.warning(f"     1. 没有任何条目有文本/图像嵌入")
        logger.warning(f"     2. 相似度计算结果都为 0")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"[vector_search] ========== 搜索结束 ==========")
    logger.info(f"{'='*60}\n")
    
    return results


def filter_results_by_user(results: List[Tuple[int, float]], db: Session, user_id: int) -> List[Tuple[int, float]]:
    logger.info(f"\n{'='*60}")
    logger.info(f"[filter_results_by_user] 按用户过滤结果")
    logger.info(f"{'='*60}")
    logger.info(f"  - 用户ID: {user_id}")
    logger.info(f"  - 输入结果数: {len(results)}")
    
    if len(results) == 0:
        logger.debug("[filter_results_by_user] 输入结果为空，直接返回")
        return []
    
    photo_ids = [r[0] for r in results]
    logger.debug(f"  - 搜索到的 photo_ids: {photo_ids}")
    
    logger.debug(f"\n[filter_results_by_user] 查询数据库中属于该用户的照片...")
    user_photos = db.query(Photo).filter(
        Photo.id.in_(photo_ids),
        Photo.user_id == user_id
    ).all()
    
    logger.info(f"[filter_results_by_user] 查询到 {len(user_photos)} 张照片属于该用户")
    
    if len(user_photos) > 0:
        logger.debug(f"\n  详情:")
        for p in user_photos:
            logger.debug(f"    - photo_id={p.id}, user_id={p.user_id}, description='{p.description}'")
    else:
        logger.warning(f"\n  ⚠️ 没有任何照片属于该用户")
        logger.warning(f"     可能的原因:")
        logger.warning(f"     1. 这些照片属于其他用户")
        logger.warning(f"     2. 照片的 user_id 字段为空")
    
    user_photo_ids = {p.id for p in user_photos}
    filtered = [(photo_id, score) for photo_id, score in results if photo_id in user_photo_ids]
    
    logger.info(f"\n[filter_results_by_user] 过滤结果:")
    logger.info(f"  - 过滤前: {len(results)} 个结果")
    logger.info(f"  - 过滤后: {len(filtered)} 个结果")
    
    if len(filtered) > 0:
        logger.debug(f"\n  过滤后的结果:")
        for i, (pid, score) in enumerate(filtered):
            logger.debug(f"    {i+1}. photo_id={pid}, 相似度={score:.6f}")
    
    logger.info(f"{'='*60}\n")
    
    return filtered


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    
    return HTMLResponse(content=render_template(
        "login.html",
        {
            "request": request,
            "error": None,
        },
    ))


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    token: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.token == token.strip()).first()
    
    if not user:
        return HTMLResponse(content=render_template(
            "login.html",
            {
                "request": request,
                "error": "无效的 token，请重试",
            },
        ), status_code=401)
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="token", value=user.token, httponly=True, max_age=86400 * 30)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="token")
    return response


@app.get("/create-user", response_class=HTMLResponse)
async def create_user_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    
    return HTMLResponse(content=render_template(
        "create_user.html",
        {
            "request": request,
            "error": None,
        },
    ))


@app.post("/create-user", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.username == username.strip()).first()
    if existing_user:
        return HTMLResponse(content=render_template(
            "create_user.html",
            {
                "request": request,
                "error": "用户名已存在，请选择其他用户名",
            },
        ), status_code=400)
    
    new_token = uuid.uuid4().hex
    user = User(token=new_token, username=username.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return HTMLResponse(content=render_template(
        "create_user_success.html",
        {
            "request": request,
            "username": user.username,
            "token": user.token,
        },
    ))


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    query = db.query(Photo).filter(Photo.user_id == current_user.id)
    
    if q:
        query = query.filter(Photo.description.like(f"%{q}%"))
    
    total = query.count()
    
    photos = (
        query.order_by(Photo.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    
    tags = get_all_tags(db, current_user.id)
    date_groups = get_date_groups(db, current_user.id)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
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
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    global _embedding_enabled
    
    tags = get_all_tags(db, current_user.id)
    date_groups = get_date_groups(db, current_user.id)
    
    if not _embedding_enabled:
        return HTMLResponse(content=render_template(
            "vector_search.html",
            {
                "request": request,
                "current_user": current_user,
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
                "current_user": current_user,
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
    search_results = filter_results_by_user(search_results, db, current_user.id)
    
    total = len(search_results)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_results = search_results[start_idx:end_idx]
    
    photo_ids_with_score = {photo_id: score for photo_id, score in paged_results}
    photos = db.query(Photo).filter(
        Photo.id.in_(list(photo_ids_with_score.keys())),
        Photo.user_id == current_user.id
    ).all()
    
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
            "current_user": current_user,
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
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    photos = db.query(Photo).filter(
        Photo.user_id == current_user.id,
        Photo.tags.like(f"%{tag}%")
    ).order_by(Photo.created_at.desc()).all()
    
    filtered_photos = [p for p in photos if tag in p.get_tags_list()]
    
    total = len(filtered_photos)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_photos = filtered_photos[start_idx:end_idx]
    
    tags = get_all_tags(db, current_user.id)
    date_groups = get_date_groups(db, current_user.id)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
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
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        year, month = map(int, year_month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    photos = db.query(Photo).filter(
        Photo.user_id == current_user.id
    ).order_by(Photo.created_at.desc()).all()
    
    filtered_photos = [
        p for p in photos 
        if p.created_at.year == year and p.created_at.month == month
    ]
    
    total = len(filtered_photos)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paged_photos = filtered_photos[start_idx:end_idx]
    
    tags = get_all_tags(db, current_user.id)
    date_groups = get_date_groups(db, current_user.id)
    pagination = get_pagination_info(total, page, PAGE_SIZE)
    
    global _embedding_enabled
    return HTMLResponse(content=render_template(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
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
    current_user: User = Depends(get_current_user_required),
):
    if not file.content_type.startswith("image/"):
        return HTMLResponse("只能上传图片文件", status_code=400)
    
    user_dir = get_user_upload_dir(current_user.id)
    thumbnails_dir = os.path.join(user_dir, "thumbnails")
    
    filename = get_unique_filename(file.filename)
    file_path = os.path.join(user_dir, filename)
    thumbnail_filename = f"thumb_{filename}"
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    
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
        user_id=current_user.id,
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
async def photo_detail(
    photo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return HTMLResponse(content=render_template(
        "detail.html",
        {"request": request, "current_user": current_user, "photo": photo},
    ))


@app.post("/photo/{photo_id}/delete")
async def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    user_dir = get_user_upload_dir(current_user.id)
    file_path = os.path.join(user_dir, photo.filename)
    thumbnail_path = os.path.join(user_dir, "thumbnails", photo.thumbnail_filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    
    remove_from_vector_store(photo_id)
    
    db.delete(photo)
    db.commit()
    
    return RedirectResponse(url="/", status_code=303)
