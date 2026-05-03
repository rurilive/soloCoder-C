from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Any
from pydantic import BaseModel
from pathlib import Path
import uuid
from datetime import datetime

from app.database import get_db
from app.models import Document, Folder
from app.utils import (
    parse_file, 
    get_file_type,
    parse_excel_file,
    update_cell_in_excel,
    update_multiple_cells,
    add_new_sheet,
    delete_sheet,
    get_sheet_data_as_json,
    get_sheet_metadata,
    get_sheet_data_paginated,
    get_ppt_metadata,
    get_slide_data_paginated,
    get_ppt_data_as_json,
    update_text_in_slide,
    update_multiple_texts,
    add_new_slide,
    delete_slide,
    reorder_slides,
    get_background_info,
    set_solid_background,
    set_picture_background,
    set_picture_background_v2,
    add_picture_shape_to_slide,
    remove_background,
)

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


class CellUpdate(BaseModel):
    sheet_name: str
    row: int
    col: int
    value: Optional[Any] = None


class BatchCellUpdate(BaseModel):
    updates: List[CellUpdate]


class SheetOperation(BaseModel):
    sheet_name: str


@router.get("/{doc_id}/excel/metadata")
async def get_excel_metadata(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    快速获取Excel文件的元数据（不加载实际数据）
    适用于大型表格，先获取表格信息再决定如何加载
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    try:
        metadata = get_sheet_metadata(str(file_path))
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取Excel元数据失败: {str(e)}")


@router.get("/{doc_id}/excel/data/paginated")
async def get_excel_data_paginated(
    doc_id: int,
    sheet_name: str,
    start_row: int = 1,
    end_row: int = 100,
    include_styles: bool = False,
    db: Session = Depends(get_db)
):
    """
    分页获取Excel工作表数据
    适用于大型表格，每次只加载指定范围的行
    
    Args:
        doc_id: 文档ID
        sheet_name: 工作表名称
        start_row: 起始行（从1开始）
        end_row: 结束行
        include_styles: 是否包含样式信息（会降低性能）
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    if start_row < 1:
        start_row = 1
    if end_row < start_row:
        end_row = start_row + 99
    
    max_rows_per_request = 500
    if end_row - start_row + 1 > max_rows_per_request:
        end_row = start_row + max_rows_per_request - 1
    
    try:
        data = get_sheet_data_paginated(
            str(file_path),
            sheet_name,
            start_row,
            end_row,
            include_styles
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取Excel数据失败: {str(e)}")


@router.get("/{doc_id}/excel/data")
async def get_excel_data(
    doc_id: int,
    sheet_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取Excel文件的详细数据（JSON格式）
    仅适用于Excel类型的文档
    
    注意：对于超过1000行的大型表格，建议使用 /data/paginated 进行分页加载
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    try:
        data = get_sheet_data_as_json(str(file_path), sheet_name)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取Excel数据失败: {str(e)}")


@router.put("/{doc_id}/excel/cell")
async def update_excel_cell(
    doc_id: int,
    update: CellUpdate,
    db: Session = Depends(get_db)
):
    """
    更新Excel文件中指定单元格的值
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = update_cell_in_excel(
        str(file_path),
        update.sheet_name,
        update.row,
        update.col,
        update.value
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新单元格失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "单元格更新成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.put("/{doc_id}/excel/cells")
async def update_excel_cells_batch(
    doc_id: int,
    batch_update: BatchCellUpdate,
    db: Session = Depends(get_db)
):
    """
    批量更新Excel文件中的多个单元格
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    updates_list = [
        {
            "sheet_name": u.sheet_name,
            "row": u.row,
            "col": u.col,
            "value": u.value
        }
        for u in batch_update.updates
    ]
    
    success = update_multiple_cells(str(file_path), updates_list)
    
    if not success:
        raise HTTPException(status_code=500, detail="批量更新单元格失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"成功更新 {len(batch_update.updates)} 个单元格",
        "updated_count": len(batch_update.updates),
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.post("/{doc_id}/excel/sheet")
async def add_excel_sheet(
    doc_id: int,
    operation: SheetOperation,
    db: Session = Depends(get_db)
):
    """
    在Excel文件中添加新工作表
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = add_new_sheet(str(file_path), operation.sheet_name)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"添加工作表失败，可能工作表名称 '{operation.sheet_name}' 已存在")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"工作表 '{operation.sheet_name}' 添加成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.delete("/{doc_id}/excel/sheet")
async def delete_excel_sheet(
    doc_id: int,
    operation: SheetOperation,
    db: Session = Depends(get_db)
):
    """
    从Excel文件中删除指定工作表
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "excel":
        raise HTTPException(status_code=400, detail="此文档不是Excel格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = delete_sheet(str(file_path), operation.sheet_name)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"删除工作表失败，可能工作表名称 '{operation.sheet_name}' 不存在或是最后一个工作表")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"工作表 '{operation.sheet_name}' 删除成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


class SlideTextUpdate(BaseModel):
    slide_idx: int
    shape_idx: int
    text: str


class BatchSlideTextUpdate(BaseModel):
    updates: List[SlideTextUpdate]


class SlideOperation(BaseModel):
    slide_idx: int


class AddSlideOperation(BaseModel):
    layout_idx: int = 6
    title_text: Optional[str] = None
    content_text: Optional[str] = None


class ReorderSlidesOperation(BaseModel):
    old_idx: int
    new_idx: int


@router.get("/{doc_id}/ppt/metadata")
async def get_ppt_metadata_endpoint(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    快速获取PPT文件的元数据（不加载所有内容）
    适用于大型PPT，先获取幻灯片信息再决定如何加载
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    try:
        metadata = get_ppt_metadata(str(file_path))
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取PPT元数据失败: {str(e)}")


@router.get("/{doc_id}/ppt/data/paginated")
async def get_ppt_data_paginated(
    doc_id: int,
    start_slide: int = 1,
    end_slide: int = 10,
    include_notes: bool = True,
    db: Session = Depends(get_db)
):
    """
    分页获取PPT幻灯片数据
    适用于大型PPT，每次只加载指定范围的幻灯片
    
    Args:
        doc_id: 文档ID
        start_slide: 起始幻灯片（从1开始）
        end_slide: 结束幻灯片
        include_notes: 是否包含备注
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    if start_slide < 1:
        start_slide = 1
    if end_slide < start_slide:
        end_slide = start_slide + 9
    
    max_slides_per_request = 50
    if end_slide - start_slide + 1 > max_slides_per_request:
        end_slide = start_slide + max_slides_per_request - 1
    
    try:
        data = get_slide_data_paginated(
            str(file_path),
            start_slide,
            end_slide,
            include_notes
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取PPT数据失败: {str(e)}")


@router.get("/{doc_id}/ppt/data")
async def get_ppt_data(
    doc_id: int,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取PPT文件的详细数据（JSON格式）
    仅适用于PPT类型的文档
    
    注意：对于超过50张幻灯片的大型PPT，建议使用 /data/paginated 进行分页加载
    
    Args:
        doc_id: 文档ID
        start_slide: 可选，起始幻灯片（从1开始）
        end_slide: 可选，结束幻灯片
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    try:
        slide_range = None
        if start_slide is not None and end_slide is not None:
            slide_range = (start_slide, end_slide)
        
        data = get_ppt_data_as_json(str(file_path), slide_range)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取PPT数据失败: {str(e)}")


@router.put("/{doc_id}/ppt/text")
async def update_ppt_text(
    doc_id: int,
    update: SlideTextUpdate,
    db: Session = Depends(get_db)
):
    """
    更新PPT中指定幻灯片中指定形状的文本
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = update_text_in_slide(
        str(file_path),
        update.slide_idx,
        update.shape_idx,
        update.text
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新文本失败，请检查幻灯片索引和形状索引是否正确")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "文本更新成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.put("/{doc_id}/ppt/texts")
async def update_ppt_texts_batch(
    doc_id: int,
    batch_update: BatchSlideTextUpdate,
    db: Session = Depends(get_db)
):
    """
    批量更新PPT中的多个文本
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    updates_list = [
        {
            "slide_idx": u.slide_idx,
            "shape_idx": u.shape_idx,
            "text": u.text
        }
        for u in batch_update.updates
    ]
    
    success, updated_count = update_multiple_texts(str(file_path), updates_list)
    
    if not success:
        raise HTTPException(status_code=500, detail="批量更新文本失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"成功更新 {updated_count} 个文本",
        "updated_count": updated_count,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.post("/{doc_id}/ppt/slide")
async def add_ppt_slide(
    doc_id: int,
    operation: AddSlideOperation,
    db: Session = Depends(get_db)
):
    """
    在PPT中添加新幻灯片
    
    Args:
        layout_idx: 布局索引（默认6是空白布局，0是标题布局）
        title_text: 标题文本（可选）
        content_text: 内容文本（可选）
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = add_new_slide(
        str(file_path),
        operation.layout_idx,
        operation.title_text,
        operation.content_text
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="添加幻灯片失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "幻灯片添加成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.delete("/{doc_id}/ppt/slide")
async def delete_ppt_slide(
    doc_id: int,
    operation: SlideOperation,
    db: Session = Depends(get_db)
):
    """
    从PPT中删除指定幻灯片
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = delete_slide(str(file_path), operation.slide_idx)
    
    if not success:
        raise HTTPException(status_code=400, detail="删除幻灯片失败，可能幻灯片索引不存在或是最后一张幻灯片")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"幻灯片 {operation.slide_idx} 删除成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.put("/{doc_id}/ppt/reorder")
async def reorder_ppt_slides(
    doc_id: int,
    operation: ReorderSlidesOperation,
    db: Session = Depends(get_db)
):
    """
    重新排列PPT中的幻灯片顺序
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = reorder_slides(
        str(file_path),
        operation.old_idx,
        operation.new_idx
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="重新排列幻灯片失败，请检查索引是否正确")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": f"幻灯片从位置 {operation.old_idx} 移动到位置 {operation.new_idx} 成功",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


class SolidBackgroundOperation(BaseModel):
    slide_idx: int
    color: str


class PictureBackgroundOperation(BaseModel):
    slide_idx: int
    image_path: Optional[str] = None


class AddPictureShapeOperation(BaseModel):
    slide_idx: int
    image_path: str
    left: float = 0
    top: float = 0
    width: Optional[float] = None
    height: Optional[float] = None


BACKGROUND_DIR = Path("uploads/backgrounds")
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)


def generate_unique_image_filename(original_filename: str) -> str:
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "jpg"
    if ext not in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
        ext = "jpg"
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{unique_id}.{ext}"


@router.get("/{doc_id}/ppt/background")
async def get_ppt_background(
    doc_id: int,
    slide_idx: int = 1,
    db: Session = Depends(get_db)
):
    """
    获取指定幻灯片的背景信息
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    try:
        background = get_background_info(str(file_path), slide_idx)
        return {
            "success": True,
            "slide_idx": slide_idx,
            "background_type": background.background_type,
            "color": background.color,
            "image_path": background.image_path,
            "image_filename": background.image_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取背景信息失败: {str(e)}")


@router.put("/{doc_id}/ppt/background/solid")
async def set_ppt_solid_background(
    doc_id: int,
    operation: SolidBackgroundOperation,
    db: Session = Depends(get_db)
):
    """
    设置幻灯片纯色背景
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = set_solid_background(str(file_path), operation.slide_idx, operation.color)
    
    if not success:
        raise HTTPException(status_code=500, detail="设置纯色背景失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "纯色背景设置成功",
        "slide_idx": operation.slide_idx,
        "color": operation.color,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.post("/{doc_id}/ppt/background/picture")
async def set_ppt_picture_background(
    doc_id: int,
    slide_idx: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    设置幻灯片图片背景（上传图片）
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择图片文件")
    
    filename = generate_unique_image_filename(file.filename)
    image_file_path = BACKGROUND_DIR / filename
    
    content = await file.read()
    with open(image_file_path, "wb") as f:
        f.write(content)
    
    success = set_picture_background_v2(str(file_path), slide_idx, str(image_file_path))
    
    if not success:
        if image_file_path.exists():
            image_file_path.unlink()
        raise HTTPException(status_code=500, detail="设置图片背景失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "图片背景设置成功",
        "slide_idx": slide_idx,
        "image_filename": filename,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.post("/{doc_id}/ppt/picture")
async def add_ppt_picture_shape(
    doc_id: int,
    slide_idx: int = Form(...),
    left: float = Form(0),
    top: float = Form(0),
    width: Optional[float] = Form(None),
    height: Optional[float] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    在幻灯片中添加图片形状
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择图片文件")
    
    filename = generate_unique_image_filename(file.filename)
    image_file_path = BACKGROUND_DIR / filename
    
    content = await file.read()
    with open(image_file_path, "wb") as f:
        f.write(content)
    
    success = add_picture_shape_to_slide(
        str(file_path),
        slide_idx,
        str(image_file_path),
        left,
        top,
        width,
        height
    )
    
    if not success:
        if image_file_path.exists():
            image_file_path.unlink()
        raise HTTPException(status_code=500, detail="添加图片形状失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "图片形状添加成功",
        "slide_idx": slide_idx,
        "image_filename": filename,
        "position": {
            "left": left,
            "top": top,
            "width": width,
            "height": height
        },
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }


@router.delete("/{doc_id}/ppt/background")
async def remove_ppt_background(
    doc_id: int,
    operation: SlideOperation,
    db: Session = Depends(get_db)
):
    """
    移除幻灯片背景
    """
    doc = db.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if doc.file_type != "ppt":
        raise HTTPException(status_code=400, detail="此文档不是PPT格式")
    
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    success = remove_background(str(file_path), operation.slide_idx)
    
    if not success:
        raise HTTPException(status_code=500, detail="移除背景失败")
    
    content, html_content = parse_file(str(file_path), doc.file_type)
    if content or html_content:
        doc.content = content
        doc.html_content = html_content
        db.commit()
        db.refresh(doc)
    
    return {
        "message": "背景移除成功",
        "slide_idx": operation.slide_idx,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "html_content": doc.html_content,
        }
    }
