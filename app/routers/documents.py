from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Document, Folder

router = APIRouter()


@router.get("/")
async def get_documents(
    folder_id: int = None,
    db: Session = Depends(get_db)
):
    """
    获取文档列表，支持按文件夹筛选
    """
    query = select(Document)
    if folder_id is not None:
        query = query.where(Document.folder_id == folder_id)
    else:
        query = query.where(Document.folder_id.is_(None))
    
    documents = db.execute(query.order_by(Document.created_at.desc())).scalars().all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "folder_id": doc.folder_id,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ]
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个文档详情
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return {
        "id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_path": doc.file_path,
        "content": doc.content,
        "html_content": doc.html_content,
        "folder_id": doc.folder_id,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    删除文档
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    db.delete(doc)
    db.commit()
    
    return {"message": "文档删除成功"}


@router.put("/{doc_id}/move/{folder_id}")
async def move_document(
    doc_id: int,
    folder_id: int,
    db: Session = Depends(get_db)
):
    """
    移动文档到指定文件夹
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if folder_id == 0:
        doc.folder_id = None
    else:
        folder = db.execute(select(Folder).where(Folder.id == folder_id)).scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        doc.folder_id = folder_id
    
    db.commit()
    
    return {"message": "文档移动成功"}
