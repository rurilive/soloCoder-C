from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List

from app.database import get_db
from app.models import Folder, Document

router = APIRouter()


def get_folder_tree(db: Session, parent_id: int = None):
    """
    递归获取文件夹树结构
    """
    query = select(Folder)
    if parent_id is None:
        query = query.where(Folder.parent_id.is_(None))
    else:
        query = query.where(Folder.parent_id == parent_id)
    
    folders = db.execute(query.order_by(Folder.name)).scalars().all()
    
    result = []
    for folder in folders:
        children = get_folder_tree(db, folder.id)
        docs_query = select(Document).where(Document.folder_id == folder.id)
        documents = db.execute(docs_query).scalars().all()
        
        result.append({
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
            "children": children,
            "document_count": len(documents),
        })
    
    return result


@router.get("/")
async def get_folders(
    parent_id: int = None,
    tree: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取文件夹列表，支持树形结构
    """
    if tree:
        return {"folders": get_folder_tree(db)}
    
    query = select(Folder)
    if parent_id is not None:
        query = query.where(Folder.parent_id == parent_id)
    else:
        query = query.where(Folder.parent_id.is_(None))
    
    folders = db.execute(query.order_by(Folder.name)).scalars().all()
    
    return {
        "folders": [
            {
                "id": folder.id,
                "name": folder.name,
                "parent_id": folder.parent_id,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
            }
            for folder in folders
        ]
    }


@router.get("/tree")
async def get_folder_tree_api(
    db: Session = Depends(get_db)
):
    """
    获取完整的文件夹树结构，包含文档统计
    """
    return {"folders": get_folder_tree(db)}


@router.get("/{folder_id}")
async def get_folder(
    folder_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个文件夹详情
    """
    folder = db.execute(select(Folder).where(Folder.id == folder_id)).scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    children = get_folder_tree(db, folder.id)
    docs_query = select(Document).where(Document.folder_id == folder.id)
    documents = db.execute(docs_query.order_by(Document.created_at.desc())).scalars().all()
    
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        "children": children,
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
    }


@router.post("/")
async def create_folder(
    name: str = Form(...),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    创建新文件夹
    """
    if parent_id is not None:
        parent = db.execute(select(Folder).where(Folder.id == parent_id)).scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="父文件夹不存在")
    
    folder = Folder(name=name, parent_id=parent_id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
    return {
        "message": "文件夹创建成功",
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
        }
    }


@router.put("/{folder_id}")
async def update_folder(
    folder_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    更新文件夹名称
    """
    folder = db.execute(select(Folder).where(Folder.id == folder_id)).scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    folder.name = name
    db.commit()
    
    return {"message": "文件夹更新成功"}


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db)
):
    """
    删除文件夹（级联删除子文件夹和文档）
    """
    folder = db.execute(select(Folder).where(Folder.id == folder_id)).scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    db.delete(folder)
    db.commit()
    
    return {"message": "文件夹删除成功"}
