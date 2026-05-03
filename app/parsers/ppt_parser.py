from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import html
import logging
from logging.handlers import RotatingFileHandler


LOG_DIR = Path(__file__).resolve().parent.parent.parent / 'log'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'ppt_parser.log'

logger = logging.getLogger('ppt_parser')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=10*1024*1024,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

logger.info("=" * 60)
logger.info("ppt_parser 模块初始化")
logger.info(f"日志文件: {LOG_FILE}")
logger.info("=" * 60)


@dataclass
class TextStyle:
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[str] = None


@dataclass
class ParagraphInfo:
    text: str
    level: int
    alignment: Optional[str] = None
    style: Optional[TextStyle] = None


@dataclass
class TextFrameInfo:
    paragraphs: List[ParagraphInfo] = field(default_factory=list)
    text: str = ""


@dataclass
class TableCellInfo:
    row_idx: int
    col_idx: int
    text: str
    style: Optional[TextStyle] = None
    merge_info: Optional[Dict[str, Any]] = None


@dataclass
class TableInfo:
    rows: int
    cols: int
    cells: List[List[TableCellInfo]] = field(default_factory=list)
    text_content: str = ""


@dataclass
class ShapeInfo:
    shape_id: int
    shape_type: str
    name: str
    text: str = ""
    text_frame: Optional[TextFrameInfo] = None
    table: Optional[TableInfo] = None
    left: Optional[float] = None
    top: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


@dataclass
class SlideInfo:
    slide_idx: int
    slide_id: int
    layout_name: str = ""
    shapes: List[ShapeInfo] = field(default_factory=list)
    text_content: str = ""
    notes: str = ""


@dataclass
class PresentationInfo:
    slide_count: int
    slide_width: Optional[float] = None
    slide_height: Optional[float] = None
    slides: List[SlideInfo] = field(default_factory=list)
    core_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    success: bool
    error_message: str = ""
    presentation: Optional[PresentationInfo] = None
    text_content: str = ""
    html_content: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


def _get_color_value(prs_color) -> Optional[str]:
    """
    安全地获取颜色值
    """
    if prs_color is None:
        return None
    try:
        if hasattr(prs_color, 'rgb') and prs_color.rgb:
            return str(prs_color.rgb)
        if hasattr(prs_color, 'theme_color'):
            return f"theme:{prs_color.theme_color}"
    except:
        pass
    return None


def _extract_text_style(paragraph) -> TextStyle:
    """
    提取段落的文本样式
    """
    style = TextStyle()
    
    try:
        font = paragraph.font
        if font:
            style.font_name = font.name
            if font.size:
                style.font_size = font.size.pt
            style.bold = font.bold
            style.italic = font.italic
            style.underline = font.underline
            style.color = _get_color_value(font.color)
    except:
        pass
    
    return style


def _extract_paragraph_info(paragraph) -> ParagraphInfo:
    """
    提取段落信息
    """
    text = paragraph.text.strip() if paragraph.text else ""
    level = paragraph.level if hasattr(paragraph, 'level') else 0
    
    alignment = None
    if hasattr(paragraph, 'alignment') and paragraph.alignment:
        align_map = {
            PP_ALIGN.LEFT: 'left',
            PP_ALIGN.CENTER: 'center',
            PP_ALIGN.RIGHT: 'right',
            PP_ALIGN.JUSTIFY: 'justify',
        }
        alignment = align_map.get(paragraph.alignment, str(paragraph.alignment))
    
    style = _extract_text_style(paragraph)
    
    return ParagraphInfo(
        text=text,
        level=level,
        alignment=alignment,
        style=style
    )


def _extract_text_frame_info(text_frame) -> TextFrameInfo:
    """
    提取文本框信息
    """
    paragraphs = []
    all_text = []
    
    if text_frame and hasattr(text_frame, 'paragraphs'):
        for para in text_frame.paragraphs:
            para_info = _extract_paragraph_info(para)
            paragraphs.append(para_info)
            if para_info.text:
                all_text.append(para_info.text)
    
    return TextFrameInfo(
        paragraphs=paragraphs,
        text="\n".join(all_text)
    )


def _extract_table_info(table) -> TableInfo:
    """
    提取表格信息
    """
    rows = len(table.rows) if hasattr(table, 'rows') else 0
    cols = len(table.columns) if hasattr(table, 'columns') else 0
    
    cells = []
    text_parts = []
    
    for row_idx in range(rows):
        row_cells = []
        row_text = []
        
        for col_idx in range(cols):
            try:
                cell = table.cell(row_idx, col_idx)
                cell_text = cell.text.strip() if cell.text else ""
                
                merge_info = None
                if hasattr(cell, 'merge_anchor') and cell.merge_anchor:
                    merge_info = {
                        'is_anchor': True,
                        'span_rows': 1,
                        'span_cols': 1
                    }
                
                cell_info = TableCellInfo(
                    row_idx=row_idx,
                    col_idx=col_idx,
                    text=cell_text,
                    merge_info=merge_info
                )
                
                row_cells.append(cell_info)
                row_text.append(cell_text)
            except:
                row_cells.append(TableCellInfo(
                    row_idx=row_idx,
                    col_idx=col_idx,
                    text=""
                ))
        
        cells.append(row_cells)
        if row_text:
            text_parts.append(" | ".join(row_text))
    
    return TableInfo(
        rows=rows,
        cols=cols,
        cells=cells,
        text_content="\n".join(text_parts)
    )


def _extract_shape_info(shape, shape_idx: int) -> ShapeInfo:
    """
    提取形状信息
    """
    shape_type = "unknown"
    name = getattr(shape, 'name', f"Shape_{shape_idx}")
    text = ""
    text_frame = None
    table = None
    
    left = None
    top = None
    width = None
    height = None
    
    try:
        if hasattr(shape, 'left'):
            left = shape.left.pt if hasattr(shape.left, 'pt') else float(shape.left)
        if hasattr(shape, 'top'):
            top = shape.top.pt if hasattr(shape.top, 'pt') else float(shape.top)
        if hasattr(shape, 'width'):
            width = shape.width.pt if hasattr(shape.width, 'pt') else float(shape.width)
        if hasattr(shape, 'height'):
            height = shape.height.pt if hasattr(shape.height, 'pt') else float(shape.height)
    except:
        pass
    
    if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
        shape_type = "text_box"
        text_frame = _extract_text_frame_info(shape.text_frame)
        text = text_frame.text
    
    elif hasattr(shape, 'has_table') and shape.has_table:
        shape_type = "table"
        table = _extract_table_info(shape.table)
        text = table.text_content
    
    elif hasattr(shape, 'shape_type'):
        try:
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            type_map = {
                MSO_SHAPE_TYPE.AUTO_SHAPE: "auto_shape",
                MSO_SHAPE_TYPE.CHART: "chart",
                MSO_SHAPE_TYPE.LINE: "line",
                MSO_SHAPE_TYPE.PICTURE: "picture",
                MSO_SHAPE_TYPE.GROUP: "group",
                MSO_SHAPE_TYPE.PLACEHOLDER: "placeholder",
                MSO_SHAPE_TYPE.TEXT_BOX: "text_box",
                MSO_SHAPE_TYPE.TABLE: "table",
                MSO_SHAPE_TYPE.MEDIA: "media",
                MSO_SHAPE_TYPE.LINKED_OLE_OBJECT: "ole_object",
                MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT: "ole_object",
            }
            shape_type = type_map.get(shape.shape_type, str(shape.shape_type))
        except:
            shape_type = str(getattr(shape, 'shape_type', 'unknown'))
    
    return ShapeInfo(
        shape_id=shape_idx,
        shape_type=shape_type,
        name=name,
        text=text,
        text_frame=text_frame,
        table=table,
        left=left,
        top=top,
        width=width,
        height=height
    )


def _extract_slide_info(slide, slide_idx: int) -> SlideInfo:
    """
    提取幻灯片信息
    """
    shapes = []
    text_parts = []
    
    slide_id = getattr(slide, 'slide_id', slide_idx)
    layout_name = ""
    
    try:
        if hasattr(slide, 'slide_layout') and slide.slide_layout:
            layout_name = getattr(slide.slide_layout, 'name', "")
    except:
        pass
    
    for shape_idx, shape in enumerate(slide.shapes):
        shape_info = _extract_shape_info(shape, shape_idx)
        shapes.append(shape_info)
        
        if shape_info.text:
            text_parts.append(shape_info.text)
    
    notes = ""
    try:
        if hasattr(slide, 'notes_slide') and slide.notes_slide:
            notes_shapes = slide.notes_slide.shapes
            for shape in notes_shapes:
                if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
                    notes_text = shape.text_frame.text.strip()
                    if notes_text:
                        notes = notes_text
                        break
    except:
        pass
    
    return SlideInfo(
        slide_idx=slide_idx,
        slide_id=slide_id,
        layout_name=layout_name,
        shapes=shapes,
        text_content="\n".join(text_parts),
        notes=notes
    )


def _extract_core_properties(prs) -> Dict[str, Any]:
    """
    提取演示文稿核心属性
    """
    properties = {}
    
    try:
        if hasattr(prs, 'core_properties'):
            cp = prs.core_properties
            property_map = {
                'author': 'author',
                'category': 'category',
                'comments': 'comments',
                'content_status': 'content_status',
                'created': 'created',
                'identifier': 'identifier',
                'keywords': 'keywords',
                'language': 'language',
                'last_modified_by': 'last_modified_by',
                'last_printed': 'last_printed',
                'modified': 'modified',
                'revision': 'revision',
                'subject': 'subject',
                'title': 'title',
                'version': 'version',
            }
            
            for key, attr in property_map.items():
                try:
                    value = getattr(cp, attr, None)
                    if value is not None:
                        if hasattr(value, 'isoformat'):
                            properties[key] = value.isoformat()
                        else:
                            properties[key] = str(value)
                except:
                    pass
    except:
        pass
    
    return properties


def parse_ppt_file(file_path: str) -> ParseResult:
    """
    解析PowerPoint文件，返回详细的解析结果
    """
    file_path = Path(file_path)
    
    logger.info(f"[parse_ppt_file] 开始解析: {file_path}")
    
    try:
        prs = Presentation(file_path)
    except Exception as e:
        logger.error(f"[parse_ppt_file] 无法加载PPT文件: {e}")
        return ParseResult(
            success=False,
            error_message=f"无法加载PPT文件: {str(e)}"
        )
    
    slides = []
    all_text_parts = []
    all_html_parts = []
    
    slide_width = None
    slide_height = None
    
    try:
        if hasattr(prs, 'slide_width'):
            slide_width = prs.slide_width.pt if hasattr(prs.slide_width, 'pt') else float(prs.slide_width)
        if hasattr(prs, 'slide_height'):
            slide_height = prs.slide_height.pt if hasattr(prs.slide_height, 'pt') else float(prs.slide_height)
    except:
        pass
    
    core_properties = _extract_core_properties(prs)
    
    for slide_idx, slide in enumerate(prs.slides, 1):
        slide_info = _extract_slide_info(slide, slide_idx)
        slides.append(slide_info)
        
        all_text_parts.append(f"=== 幻灯片 {slide_idx} ===")
        if slide_info.text_content:
            all_text_parts.append(slide_info.text_content)
        
        slide_html = _slide_to_html(slide_info)
        all_html_parts.append(slide_html)
    
    presentation = PresentationInfo(
        slide_count=len(slides),
        slide_width=slide_width,
        slide_height=slide_height,
        slides=slides,
        core_properties=core_properties
    )
    
    text_content = "\n\n".join(all_text_parts)
    html_content = "\n".join(all_html_parts)
    
    logger.info(f"[parse_ppt_file] 解析完成，幻灯片数: {len(slides)}, 文本长度: {len(text_content)}")
    
    return ParseResult(
        success=True,
        presentation=presentation,
        text_content=text_content,
        html_content=html_content,
        raw_data={
            'slide_count': len(slides),
            'slide_width': slide_width,
            'slide_height': slide_height,
        }
    )


def _slide_to_html(slide_info: SlideInfo) -> str:
    """
    将幻灯片信息转换为HTML
    """
    html_parts = []
    
    html_parts.append(f"<div class='slide'>")
    html_parts.append(f"<h2 class='slide-title'>幻灯片 {slide_info.slide_idx}</h2>")
    
    if slide_info.layout_name:
        html_parts.append(f"<div class='slide-layout'>布局: {html.escape(slide_info.layout_name)}</div>")
    
    for shape in slide_info.shapes:
        if shape.shape_type == "table" and shape.table:
            html_parts.append(_table_to_html(shape.table))
        elif shape.text:
            html_parts.append(_text_shape_to_html(shape))
    
    if slide_info.notes:
        html_parts.append(f"<div class='slide-notes'>")
        html_parts.append(f"<h4>备注</h4>")
        html_parts.append(f"<p>{html.escape(slide_info.notes)}</p>")
        html_parts.append("</div>")
    
    html_parts.append("</div>")
    
    return "\n".join(html_parts)


def _table_to_html(table_info: TableInfo) -> str:
    """
    将表格信息转换为HTML
    """
    html_parts = []
    
    html_parts.append("<table class='ppt-table' style='border-collapse: collapse; margin: 10px 0;'>")
    
    for row_idx, row in enumerate(table_info.cells):
        html_parts.append("<tr>")
        
        for col_idx, cell in enumerate(row):
            tag = "th" if row_idx == 0 else "td"
            cell_text = html.escape(cell.text) if cell.text else ""
            
            style_parts = [
                "border: 1px solid #ccc;",
                "padding: 8px;",
            ]
            
            style_attr = f" style='{''.join(style_parts)}'" if style_parts else ""
            
            html_parts.append(f"<{tag}{style_attr}>{cell_text}</{tag}>")
        
        html_parts.append("</tr>")
    
    html_parts.append("</table>")
    
    return "\n".join(html_parts)


def _text_shape_to_html(shape_info: ShapeInfo) -> str:
    """
    将文本形状转换为HTML
    """
    html_parts = []
    
    if shape_info.text_frame and shape_info.text_frame.paragraphs:
        for para in shape_info.text_frame.paragraphs:
            para_text = html.escape(para.text)
            
            style_parts = []
            
            if para.level > 0:
                style_parts.append(f"margin-left: {para.level * 20}px;")
            
            if para.alignment:
                align_map = {
                    'left': 'left',
                    'center': 'center',
                    'right': 'right',
                    'justify': 'justify',
                }
                align = align_map.get(para.alignment)
                if align:
                    style_parts.append(f"text-align: {align};")
            
            if para.style:
                if para.style.bold:
                    style_parts.append("font-weight: bold;")
                if para.style.italic:
                    style_parts.append("font-style: italic;")
                if para.style.font_size:
                    style_parts.append(f"font-size: {para.style.font_size}pt;")
            
            style_attr = f" style='{''.join(style_parts)}'" if style_parts else ""
            
            html_parts.append(f"<p{style_attr}>{para_text}</p>")
    else:
        html_parts.append(f"<p>{html.escape(shape_info.text)}</p>")
    
    return "\n".join(html_parts)


def parse_ppt(file_path: str) -> tuple[str, str]:
    """
    兼容旧接口的解析函数，返回原始内容和HTML内容
    """
    logger.info(f"[parse_ppt] 解析文件: {file_path}")
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        logger.error(f"[parse_ppt] 文件不存在: {file_path}")
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    result = parse_ppt_file(file_path)
    
    if result.success:
        return result.text_content, result.html_content
    else:
        logger.error(f"[parse_ppt] 解析失败: {result.error_message}")
        raise Exception(f"解析失败: {result.error_message}")


def get_ppt_metadata(file_path: str) -> Dict[str, Any]:
    """
    快速获取PPT文件的元数据（不加载所有内容）
    """
    logger.info(f"[get_ppt_metadata] 获取元数据: {file_path}")
    
    try:
        prs = Presentation(file_path)
        
        slide_width = None
        slide_height = None
        
        try:
            if hasattr(prs, 'slide_width'):
                slide_width = prs.slide_width.pt if hasattr(prs.slide_width, 'pt') else float(prs.slide_width)
            if hasattr(prs, 'slide_height'):
                slide_height = prs.slide_height.pt if hasattr(prs.slide_height, 'pt') else float(prs.slide_height)
        except:
            pass
        
        slides_info = []
        for slide_idx, slide in enumerate(prs.slides, 1):
            slide_info = {
                'slide_idx': slide_idx,
                'shape_count': len(slide.shapes),
                'layout_name': getattr(getattr(slide, 'slide_layout', None), 'name', ""),
            }
            slides_info.append(slide_info)
        
        core_properties = _extract_core_properties(prs)
        

        
        return {
            'success': True,
            'slide_count': len(slides_info),
            'slide_width': slide_width,
            'slide_height': slide_height,
            'slides': slides_info,
            'core_properties': core_properties,
        }
        
    except Exception as e:
        logger.error(f"[get_ppt_metadata] 获取元数据失败: {e}")
        return {'success': False, 'error': str(e)}


def get_slide_data_paginated(
    file_path: str,
    start_slide: int = 1,
    end_slide: int = 10,
    include_notes: bool = True
) -> Dict[str, Any]:
    """
    分页获取PPT幻灯片数据
    
    Args:
        file_path: PPT文件路径
        start_slide: 起始幻灯片（从1开始）
        end_slide: 结束幻灯片
        include_notes: 是否包含备注
    
    Returns:
        包含分页数据的字典
    """
    logger.info(f"[get_slide_data_paginated] 获取幻灯片数据: {file_path}, 范围: {start_slide}-{end_slide}")
    
    try:
        prs = Presentation(file_path)
        
        total_slides = len(prs.slides)
        
        start_slide = max(1, start_slide)
        end_slide = min(end_slide, total_slides)
        
        if start_slide > end_slide:
    
            return {
                'success': True,
                'file_path': file_path,
                'total_slides': total_slides,
                'start_slide': start_slide,
                'end_slide': end_slide,
                'slides': [],
                'slide_count': 0,
            }
        
        slides_data = []
        
        for slide_idx in range(start_slide, end_slide + 1):
            slide = prs.slides[slide_idx - 1]
            slide_info = _extract_slide_info(slide, slide_idx)
            
            slide_dict = {
                'slide_idx': slide_info.slide_idx,
                'slide_id': slide_info.slide_id,
                'layout_name': slide_info.layout_name,
                'text_content': slide_info.text_content,
                'shape_count': len(slide_info.shapes),
                'shapes': [],
            }
            
            for shape in slide_info.shapes:
                shape_dict = {
                    'shape_id': shape.shape_id,
                    'shape_type': shape.shape_type,
                    'name': shape.name,
                    'text': shape.text,
                    'left': shape.left,
                    'top': shape.top,
                    'width': shape.width,
                    'height': shape.height,
                }
                
                if shape.text_frame and shape.text_frame.paragraphs:
                    shape_dict['paragraphs'] = [
                        {
                            'text': p.text,
                            'level': p.level,
                            'alignment': p.alignment,
                        }
                        for p in shape.text_frame.paragraphs
                    ]
                
                if shape.table:
                    shape_dict['table'] = {
                        'rows': shape.table.rows,
                        'cols': shape.table.cols,
                        'text_content': shape.table.text_content,
                    }
                
                slide_dict['shapes'].append(shape_dict)
            
            if include_notes and slide_info.notes:
                slide_dict['notes'] = slide_info.notes
            
            slides_data.append(slide_dict)
        

        
        return {
            'success': True,
            'file_path': file_path,
            'total_slides': total_slides,
            'start_slide': start_slide,
            'end_slide': end_slide,
            'slides': slides_data,
            'slide_count': len(slides_data),
        }
        
    except Exception as e:
        logger.error(f"[get_slide_data_paginated] 获取幻灯片数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def get_ppt_data_as_json(file_path: str, slide_range: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
    """
    获取PPT文件数据为JSON格式
    
    注意：对于大型PPT，建议使用 get_slide_data_paginated 进行分页加载
    
    Args:
        file_path: PPT文件路径
        slide_range: 幻灯片范围 (start, end)，默认为全部
    
    Returns:
        包含数据的字典
    """
    logger.info(f"[get_ppt_data_as_json] 获取PPT数据: {file_path}")
    
    metadata = get_ppt_metadata(file_path)
    
    if not metadata['success']:
        return {'success': False, 'error': metadata['error']}
    
    total_slides = metadata['slide_count']
    
    MAX_SLIDES_FULL_LOAD = 50
    
    if slide_range:
        start_slide, end_slide = slide_range
    else:
        start_slide = 1
        end_slide = total_slides
    
    if total_slides <= MAX_SLIDES_FULL_LOAD:
        paginated_data = get_slide_data_paginated(
            file_path,
            start_slide=start_slide,
            end_slide=end_slide,
            include_notes=True
        )
        
        if paginated_data['success']:
            return {
                'success': True,
                'slide_count': total_slides,
                'slide_width': metadata.get('slide_width'),
                'slide_height': metadata.get('slide_height'),
                'slides': paginated_data['slides'],
                'is_paginated': False,
                'core_properties': metadata.get('core_properties', {}),
            }
        else:
            return {
                'success': False,
                'error': paginated_data.get('error'),
            }
    else:
        return {
            'success': True,
            'slide_count': total_slides,
            'slide_width': metadata.get('slide_width'),
            'slide_height': metadata.get('slide_height'),
            'slides': [],
            'is_paginated': True,
            'message': f'PPT较大（{total_slides}张幻灯片），请使用分页API加载数据',
            'core_properties': metadata.get('core_properties', {}),
        }


def update_text_in_slide(
    file_path: str,
    slide_idx: int,
    shape_idx: int,
    new_text: str
) -> bool:
    """
    更新PPT中指定幻灯片中指定形状的文本
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
        shape_idx: 形状索引（从0开始）
        new_text: 新文本
    
    Returns:
        是否成功
    """
    logger.info(f"[update_text_in_slide] 更新文本: {file_path}, 幻灯片: {slide_idx}, 形状: {shape_idx}")
    
    try:
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[update_text_in_slide] 幻灯片索引超出范围: {slide_idx}")
    
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        if shape_idx < 0 or shape_idx >= len(slide.shapes):
            logger.error(f"[update_text_in_slide] 形状索引超出范围: {shape_idx}")
    
            return False
        
        shape = slide.shapes[shape_idx]
        
        if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
            text_frame = shape.text_frame
            text_frame.clear()
            p = text_frame.paragraphs[0]
            p.text = new_text
        else:
            logger.error(f"[update_text_in_slide] 形状不包含文本框")
    
            return False
        
        prs.save(file_path)

        
        logger.info(f"[update_text_in_slide] 更新成功")
        return True
        
    except Exception as e:
        logger.error(f"[update_text_in_slide] 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_multiple_texts(
    file_path: str,
    updates: List[Dict[str, Any]]
) -> Tuple[bool, int]:
    """
    批量更新PPT中的多个文本
    
    Args:
        file_path: PPT文件路径
        updates: 更新列表，每个元素包含:
            - slide_idx: 幻灯片索引
            - shape_idx: 形状索引
            - text: 新文本
    
    Returns:
        (是否成功, 更新数量)
    """
    logger.info(f"[update_multiple_texts] 批量更新文本: {file_path}, 更新数量: {len(updates)}")
    
    try:
        prs = Presentation(file_path)
        
        updated_count = 0
        
        for update in updates:
            slide_idx = update.get('slide_idx')
            shape_idx = update.get('shape_idx')
            new_text = update.get('text', '')
            
            if slide_idx is None or shape_idx is None:
                continue
            
            if slide_idx < 1 or slide_idx > len(prs.slides):
                continue
            
            slide = prs.slides[slide_idx - 1]
            
            if shape_idx < 0 or shape_idx >= len(slide.shapes):
                continue
            
            shape = slide.shapes[shape_idx]
            
            if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
                text_frame = shape.text_frame
                text_frame.clear()
                p = text_frame.paragraphs[0]
                p.text = new_text
                updated_count += 1
        
        prs.save(file_path)

        
        logger.info(f"[update_multiple_texts] 批量更新完成，成功更新: {updated_count} 个")
        return True, updated_count
        
    except Exception as e:
        logger.error(f"[update_multiple_texts] 批量更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def add_new_slide(
    file_path: str,
    layout_idx: int = 6,
    title_text: Optional[str] = None,
    content_text: Optional[str] = None
) -> bool:
    """
    在PPT中添加新幻灯片
    
    Args:
        file_path: PPT文件路径
        layout_idx: 布局索引（默认6是空白布局，0是标题布局）
        title_text: 标题文本（可选）
        content_text: 内容文本（可选）
    
    Returns:
        是否成功
    """
    logger.info(f"[add_new_slide] 添加新幻灯片: {file_path}, 布局: {layout_idx}")
    
    try:
        prs = Presentation(file_path)
        
        if layout_idx < 0 or layout_idx >= len(prs.slide_layouts):
            layout_idx = 6
        
        slide_layout = prs.slide_layouts[layout_idx]
        slide = prs.slides.add_slide(slide_layout)
        
        if title_text and hasattr(slide.shapes, 'title') and slide.shapes.title:
            slide.shapes.title.text = title_text
        
        if content_text:
            for shape in slide.shapes:
                if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
                    if shape != slide.shapes.title:
                        shape.text_frame.text = content_text
                        break
        
        prs.save(file_path)

        
        logger.info(f"[add_new_slide] 幻灯片添加成功")
        return True
        
    except Exception as e:
        logger.error(f"[add_new_slide] 添加幻灯片失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_slide(file_path: str, slide_idx: int) -> bool:
    """
    删除PPT中指定的幻灯片
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
    
    Returns:
        是否成功
    """
    logger.info(f"[delete_slide] 删除幻灯片: {file_path}, 索引: {slide_idx}")
    
    try:
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[delete_slide] 幻灯片索引超出范围: {slide_idx}")
    
            return False
        
        if len(prs.slides) <= 1:
            logger.error(f"[delete_slide] 不能删除最后一张幻灯片")
    
            return False
        
        rId = prs.slides._sldIdLst[slide_idx - 1].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[slide_idx - 1]
        
        prs.save(file_path)

        
        logger.info(f"[delete_slide] 幻灯片删除成功")
        return True
        
    except Exception as e:
        logger.error(f"[delete_slide] 删除幻灯片失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def reorder_slides(
    file_path: str,
    old_idx: int,
    new_idx: int
) -> bool:
    """
    重新排列PPT中的幻灯片顺序
    
    Args:
        file_path: PPT文件路径
        old_idx: 原始位置（从1开始）
        new_idx: 新位置（从1开始）
    
    Returns:
        是否成功
    """
    logger.info(f"[reorder_slides] 移动幻灯片: {file_path}, 从 {old_idx} 到 {new_idx}")
    
    try:
        prs = Presentation(file_path)
        
        total_slides = len(prs.slides)
        
        if old_idx < 1 or old_idx > total_slides:
            logger.error(f"[reorder_slides] 原始位置超出范围: {old_idx}")
    
            return False
        
        if new_idx < 1 or new_idx > total_slides:
            logger.error(f"[reorder_slides] 新位置超出范围: {new_idx}")
    
            return False
        
        if old_idx == new_idx:
    
            return True
        
        old_idx_0 = old_idx - 1
        new_idx_0 = new_idx - 1
        
        sldIdLst = prs.slides._sldIdLst
        sldId = sldIdLst[old_idx_0]
        
        sldIdLst.remove(sldId)
        sldIdLst.insert(new_idx_0, sldId)
        
        prs.save(file_path)

        
        logger.info(f"[reorder_slides] 幻灯片移动成功")
        return True
        
    except Exception as e:
        logger.error(f"[reorder_slides] 移动幻灯片失败: {e}")
        import traceback
        traceback.print_exc()
        return False


BACKGROUND_DIR = Path(__file__).resolve().parent.parent.parent / 'uploads' / 'backgrounds'
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BackgroundInfo:
    background_type: str = "none"
    color: Optional[str] = None
    image_path: Optional[str] = None
    image_filename: Optional[str] = None


def get_background_info(file_path: str, slide_idx: int) -> BackgroundInfo:
    """
    获取幻灯片的背景信息
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
    
    Returns:
        BackgroundInfo 对象
    """
    logger.info(f"[get_background_info] 获取背景信息: {file_path}, 幻灯片: {slide_idx}")
    
    try:
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[get_background_info] 幻灯片索引超出范围: {slide_idx}")
            return BackgroundInfo(background_type="none")
        
        slide = prs.slides[slide_idx - 1]
        
        background = BackgroundInfo(background_type="none")
        
        try:
            if hasattr(slide, 'background') and hasattr(slide.background, 'fill'):
                fill = slide.background.fill
                
                if fill.type is not None:
                    fill_type_name = str(fill.type)
                    
                    if 'SOLID' in fill_type_name:
                        background.background_type = "solid"
                        if hasattr(fill, 'fore_color') and hasattr(fill.fore_color, 'rgb'):
                            if fill.fore_color.rgb:
                                background.color = str(fill.fore_color.rgb)
                    
                    elif 'PICTURE' in fill_type_name:
                        background.background_type = "picture"
                        
        except Exception as e:
            logger.warning(f"[get_background_info] 读取背景信息时出错: {e}")
        
        return background
        
    except Exception as e:
        logger.error(f"[get_background_info] 获取背景信息失败: {e}")
        import traceback
        traceback.print_exc()
        return BackgroundInfo(background_type="none")


def set_solid_background(file_path: str, slide_idx: int, color: str) -> bool:
    """
    设置幻灯片纯色背景
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
        color: 颜色值，如 "FF0000" 或 "#FF0000"
    
    Returns:
        是否成功
    """
    logger.info(f"[set_solid_background] 设置纯色背景: {file_path}, 幻灯片: {slide_idx}, 颜色: {color}")
    
    try:
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[set_solid_background] 幻灯片索引超出范围: {slide_idx}")
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        color = color.lstrip('#')
        
        slide.background.fill.solid()
        
        from pptx.dml.color import RGBColor
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            slide.background.fill.fore_color.rgb = RGBColor(r, g, b)
        except Exception as e:
            logger.error(f"[set_solid_background] 解析颜色失败: {e}")
            return False
        
        prs.save(file_path)
        
        logger.info(f"[set_solid_background] 纯色背景设置成功")
        return True
        
    except Exception as e:
        logger.error(f"[set_solid_background] 设置纯色背景失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def set_picture_background(file_path: str, slide_idx: int, image_file_path: str) -> bool:
    """
    设置幻灯片图片背景
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
        image_file_path: 图片文件路径
    
    Returns:
        是否成功
    """
    logger.info(f"[set_picture_background] 设置图片背景: {file_path}, 幻灯片: {slide_idx}, 图片: {image_file_path}")
    
    try:
        image_path = Path(image_file_path)
        if not image_path.exists():
            logger.error(f"[set_picture_background] 图片文件不存在: {image_file_path}")
            return False
        
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[set_picture_background] 幻灯片索引超出范围: {slide_idx}")
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        slide.background.fill.picture()
        
        try:
            slide.shapes.add_picture(
                str(image_path),
                0, 0,
                prs.slide_width,
                prs.slide_height
            )
        except Exception as e:
            logger.warning(f"[set_picture_background] 使用备用方法添加背景: {e}")
        
        prs.save(file_path)
        
        logger.info(f"[set_picture_background] 图片背景设置成功")
        return True
        
    except Exception as e:
        logger.error(f"[set_picture_background] 设置图片背景失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def set_picture_background_v2(file_path: str, slide_idx: int, image_file_path: str) -> bool:
    """
    设置幻灯片图片背景（版本2：将图片作为底层形状添加）
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
        image_file_path: 图片文件路径
    
    Returns:
        是否成功
    """
    logger.info(f"[set_picture_background_v2] 设置图片背景v2: {file_path}, 幻灯片: {slide_idx}, 图片: {image_file_path}")
    
    try:
        image_path = Path(image_file_path)
        if not image_path.exists():
            logger.error(f"[set_picture_background_v2] 图片文件不存在: {image_file_path}")
            return False
        
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[set_picture_background_v2] 幻灯片索引超出范围: {slide_idx}")
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        existing_shapes = list(slide.shapes)
        
        pic = slide.shapes.add_picture(
            str(image_path),
            0, 0,
            prs.slide_width,
            prs.slide_height
        )
        
        if existing_shapes:
            for _ in range(len(existing_shapes)):
                slide.shapes._spTree.remove(slide.shapes._spTree[-1])
                slide.shapes._spTree.insert(2, pic._element)
                break
        
        prs.save(file_path)
        
        logger.info(f"[set_picture_background_v2] 图片背景设置成功")
        return True
        
    except Exception as e:
        logger.error(f"[set_picture_background_v2] 设置图片背景失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_picture_shape_to_slide(
    file_path: str,
    slide_idx: int,
    image_file_path: str,
    left: float = 0,
    top: float = 0,
    width: Optional[float] = None,
    height: Optional[float] = None
) -> bool:
    """
    在幻灯片中添加图片形状
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
        image_file_path: 图片文件路径
        left: 左边距（磅）
        top: 上边距（磅）
        width: 宽度（磅，可选）
        height: 高度（磅，可选）
    
    Returns:
        是否成功
    """
    logger.info(f"[add_picture_shape_to_slide] 添加图片形状: {file_path}, 幻灯片: {slide_idx}")
    
    try:
        image_path = Path(image_file_path)
        if not image_path.exists():
            logger.error(f"[add_picture_shape_to_slide] 图片文件不存在: {image_file_path}")
            return False
        
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[add_picture_shape_to_slide] 幻灯片索引超出范围: {slide_idx}")
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        left_emu = Emu(left * 914400 / 72)
        top_emu = Emu(top * 914400 / 72)
        
        width_emu = None
        height_emu = None
        
        if width:
            width_emu = Emu(width * 914400 / 72)
        if height:
            height_emu = Emu(height * 914400 / 72)
        
        if width_emu and height_emu:
            slide.shapes.add_picture(
                str(image_path),
                left_emu, top_emu,
                width_emu, height_emu
            )
        else:
            slide.shapes.add_picture(
                str(image_path),
                left_emu, top_emu
            )
        
        prs.save(file_path)
        
        logger.info(f"[add_picture_shape_to_slide] 图片形状添加成功")
        return True
        
    except Exception as e:
        logger.error(f"[add_picture_shape_to_slide] 添加图片形状失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def remove_background(file_path: str, slide_idx: int) -> bool:
    """
    移除幻灯片背景
    
    Args:
        file_path: PPT文件路径
        slide_idx: 幻灯片索引（从1开始）
    
    Returns:
        是否成功
    """
    logger.info(f"[remove_background] 移除背景: {file_path}, 幻灯片: {slide_idx}")
    
    try:
        prs = Presentation(file_path)
        
        if slide_idx < 1 or slide_idx > len(prs.slides):
            logger.error(f"[remove_background] 幻灯片索引超出范围: {slide_idx}")
            return False
        
        slide = prs.slides[slide_idx - 1]
        
        try:
            if hasattr(slide, 'background') and hasattr(slide.background, 'fill'):
                from pptx.enum.dml import MSO_FILL_TYPE
                slide.background.fill.background()
        except Exception as e:
            logger.warning(f"[remove_background] 移除填充背景时出错: {e}")
        
        prs.save(file_path)
        
        logger.info(f"[remove_background] 背景移除成功")
        return True
        
    except Exception as e:
        logger.error(f"[remove_background] 移除背景失败: {e}")
        import traceback
        traceback.print_exc()
        return False
