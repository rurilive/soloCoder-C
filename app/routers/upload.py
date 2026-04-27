from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional

from app.database import get_db
from app.models import Document, Folder
from app.utils import (
    get_file_type, 
    save_upload_file, 
    parse_file, 
    SUPPORTED_TYPES
)

router = APIRouter()


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    上传并解析文件
    """
    file_type = get_file_type(file.filename)
    
    if file_type == "unknown":
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持的格式: {', '.join(SUPPORTED_TYPES.keys())}"
        )
    
    file_path = await save_upload_file(file)
    
    content, html_content = parse_file(str(file_path), file_type)
    
    title = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename
    
    if folder_id is not None:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            folder_id = None
    
    doc = Document(
        title=title,
        filename=file.filename,
        file_type=file_type,
        file_path=str(file_path),
        content=content,
        html_content=html_content,
        folder_id=folder_id,
    )
    
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    return {
        "message": "文件上传成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "folder_id": doc.folder_id,
        }
    }


@router.post("/multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    批量上传文件
    """
    results = []
    errors = []
    
    for file in files:
        try:
            result = await upload_file(file=file, folder_id=folder_id, db=db)
            results.append(result["document"])
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "message": f"成功上传 {len(results)} 个文件",
        "success": results,
        "errors": errors,
    }
