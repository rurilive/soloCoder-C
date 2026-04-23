"""文件处理工具"""

import os
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from PIL import Image as PILImage
import aiofiles

from app.config.settings import get_settings

settings = get_settings()


def generate_filename(original_filename: str) -> str:
    """生成唯一文件名"""
    ext = os.path.splitext(original_filename)[1]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


def validate_image_url(url: str) -> bool:
    """验证图片URL"""
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(url.lower())[1]
    return ext in allowed_extensions


async def save_upload_file(
    upload_file: UploadFile,
    save_dir: str,
    allowed_types: Optional[list] = None,
    max_size: int = None,
) -> str:
    """保存上传的文件"""
    if max_size is None:
        max_size = settings.max_file_size

    # 验证文件类型
    if allowed_types and upload_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {upload_file.content_type}",
        )

    # 读取文件内容
    content = await upload_file.read()

    # 验证文件大小
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制: {max_size / 1024 / 1024}MB",
        )

    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)

    # 生成文件名
    filename = generate_filename(upload_file.filename or "unknown")
    file_path = os.path.join(save_dir, filename)

    # 异步保存文件
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return filename


async def save_image(upload_file: UploadFile, save_dir: str = None) -> str:
    """保存图片"""
    if save_dir is None:
        save_dir = settings.upload_image_dir

    filename = await save_upload_file(
        upload_file,
        save_dir,
        allowed_types=settings.allowed_image_types,
    )

    # 生成缩略图
    try:
        image_path = os.path.join(save_dir, filename)
        with PILImage.open(image_path) as img:
            # 生成缩略图
            img.thumbnail((800, 800))
            thumb_filename = f"thumb_{filename}"
            thumb_path = os.path.join(save_dir, thumb_filename)
            img.save(thumb_path, optimize=True, quality=85)
    except Exception:
        pass

    return filename


async def save_video(upload_file: UploadFile, save_dir: str = None) -> str:
    """保存视频"""
    if save_dir is None:
        save_dir = settings.upload_video_dir

    return await save_upload_file(
        upload_file,
        save_dir,
        allowed_types=settings.allowed_video_types,
    )


def get_file_url(filename: str, file_type: str = "image") -> str:
    """获取文件访问URL"""
    if file_type == "image":
        return f"/static/uploads/images/{filename}"
    elif file_type == "video":
        return f"/static/uploads/videos/{filename}"
    elif file_type == "avatar":
        return f"/static/uploads/avatars/{filename}"
    return f"/static/uploads/{filename}"
