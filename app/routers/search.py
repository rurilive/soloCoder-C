from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import Optional

from app.database import get_db
from app.models import Document, Folder

router = APIRouter()


@router.get("/")
async def search(
    q: str = Query(..., min_length=1),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    搜索文档和文件夹
    """
    results = {
        "documents": [],
        "folders": [],
    }
    
    if not q or len(q.strip()) == 0:
        return results
    
    search_term = f"%{q.strip()}%"
    
    if type is None or type == "document":
        docs_query = select(Document).where(
            or_(
                Document.title.ilike(search_term),
                Document.filename.ilike(search_term),
                Document.content.ilike(search_term),
            )
        )
        documents = db.execute(docs_query.order_by(Document.updated_at.desc())).scalars().all()
        
        results["documents"] = [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "folder_id": doc.folder_id,
                "snippet": get_snippet(doc.content, q) if doc.content else "",
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ]
    
    if type is None or type == "folder":
        folders_query = select(Folder).where(Folder.name.ilike(search_term))
        folders = db.execute(folders_query.order_by(Folder.updated_at.desc())).scalars().all()
        
        results["folders"] = [
            {
                "id": folder.id,
                "name": folder.name,
                "parent_id": folder.parent_id,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
            }
            for folder in folders
        ]
    
    return {
        "query": q,
        "total": len(results["documents"]) + len(results["folders"]),
        "results": results,
    }


def get_snippet(content: str, query: str, context_length: int = 100) -> str:
    """
    从内容中提取包含搜索词的摘要片段
    """
    if not content or not query:
        return ""
    
    query_lower = query.lower()
    content_lower = content.lower()
    
    index = content_lower.find(query_lower)
    if index == -1:
        words = content.split()[:20]
        return " ".join(words) + "..." if len(words) > 20 else " ".join(words)
    
    start = max(0, index - context_length)
    end = min(len(content), index + len(query) + context_length)
    
    snippet = content[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    
    return snippet
