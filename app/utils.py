import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile

from app.parsers import (
    parse_markdown, 
    parse_doc, 
    parse_excel, 
    parse_ppt,
    parse_excel_file,
    update_cell_in_excel,
    update_multiple_cells,
    add_new_sheet,
    delete_sheet,
    get_sheet_data_as_json,
    get_sheet_metadata,
    get_sheet_data_paginated,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

SUPPORTED_TYPES = {
    "md": "markdown",
    "markdown": "markdown",
    "docx": "doc",
    "doc": "doc",
    "xlsx": "excel",
    "xls": "excel",
    "pptx": "ppt",
    "ppt": "ppt",
}

PARSERS = {
    "markdown": parse_markdown,
    "doc": parse_doc,
    "excel": parse_excel,
    "ppt": parse_ppt,
}


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写）
    """
    return filename.split(".")[-1].lower() if "." in filename else ""


def get_file_type(filename: str) -> str:
    """
    根据文件名获取文件类型
    """
    ext = get_file_extension(filename)
    return SUPPORTED_TYPES.get(ext, "unknown")


def generate_unique_filename(filename: str) -> str:
    """
    生成唯一的文件名
    """
    ext = get_file_extension(filename)
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{unique_id}.{ext}" if ext else f"{timestamp}_{unique_id}"


async def save_upload_file(file: UploadFile) -> Path:
    """
    保存上传的文件到uploads目录
    """
    filename = generate_unique_filename(file.filename)
    file_path = UPLOAD_DIR / filename
    
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    return file_path


def parse_file(file_path: str, file_type: str) -> tuple[str, str]:
    """
    根据文件类型解析文件内容
    """
    if file_type not in PARSERS:
        return "", ""
    
    try:
        return PARSERS[file_type](file_path)
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return "", ""
