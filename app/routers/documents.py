from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from app.database import get_db
from app.models import Document, Folder
from app.utils import parse_file, get_file_type

router = APIRouter()


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None


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


@router.put("/{doc_id}")
async def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """
    更新文档信息和内容
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if update_data.title is not None:
        doc.title = update_data.title
    
    if update_data.content is not None:
        doc.content = update_data.content
    
    if update_data.html_content is not None:
        doc.html_content = update_data.html_content
    
    db.commit()
    db.refresh(doc)
    
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


@router.post("/{doc_id}/reparse")
async def reparse_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    重新解析文档内容
    用于当解析器更新后，重新解析已上传的文档
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    print(f"[REPARSE DEBUG] 开始重新解析文档 ID: {doc_id}")
    print(f"[REPARSE DEBUG] 文档标题: {doc.title}")
    print(f"[REPARSE DEBUG] 文件名: {doc.filename}")
    print(f"[REPARSE DEBUG] 文件类型: {doc.file_type}")
    print(f"[REPARSE DEBUG] 文件路径: {doc.file_path}")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        print(f"[REPARSE DEBUG] 文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="原始文件不存在，无法重新解析")
    
    print(f"[REPARSE DEBUG] 文件存在，开始解析...")
    
    try:
        file_type = doc.file_type
        print(f"[REPARSE DEBUG] 调用 parse_file, file_type={file_type}")
        
        content, html_content = parse_file(str(file_path), file_type)
        
        print(f"[REPARSE DEBUG] 解析完成")
        print(f"[REPARSE DEBUG] content长度: {len(content) if content else 0}")
        print(f"[REPARSE DEBUG] html_content长度: {len(html_content) if html_content else 0}")
        
        if content:
            print(f"[REPARSE DEBUG] content前200字符: {content[:200] if len(content) > 200 else content}")
        
        if html_content:
            print(f"[REPARSE DEBUG] html_content前200字符: {html_content[:200] if len(html_content) > 200 else html_content}")
        
        if content or html_content:
            doc.content = content
            doc.html_content = html_content
            db.commit()
            db.refresh(doc)
            
            print(f"[REPARSE DEBUG] 数据库更新成功")
            
            return {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "content": doc.content,
                "html_content": doc.html_content,
                "message": "文档重新解析成功"
            }
        else:
            print(f"[REPARSE DEBUG] 解析结果为空")
            raise HTTPException(status_code=500, detail="重新解析失败，无法提取内容")
            
    except Exception as e:
        print(f"[REPARSE DEBUG] 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重新解析失败: {str(e)}")
