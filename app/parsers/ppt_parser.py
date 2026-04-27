from pptx import Presentation
from pathlib import Path


def parse_ppt(file_path: str) -> tuple[str, str]:
    """
    解析PowerPoint文件（.pptx），返回原始内容和HTML内容
    """
    file_path = Path(file_path)
    prs = Presentation(file_path)
    
    content_parts = []
    html_parts = []
    
    for slide_idx, slide in enumerate(prs.slides, 1):
        content_parts.append(f"=== 幻灯片 {slide_idx} ===")
        html_parts.append(f"<h2>幻灯片 {slide_idx}</h2>")
        
        slide_content = []
        slide_html = []
        
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                text = shape.text.strip()
                slide_content.append(text)
                
                if shape.has_text_frame:
                    text_frame = shape.text_frame
                    for para in text_frame.paragraphs:
                        level = para.level
                        if level == 0:
                            slide_html.append(f"<p>{para.text.strip()}</p>")
                        else:
                            slide_html.append(f"<p style='margin-left: {level * 20}px;'>{para.text.strip()}</p>")
        
        if slide_content:
            content_parts.append("\n".join(slide_content))
            html_parts.append("<div class='slide-content'>" + "\n".join(slide_html) + "</div>")
        
        if hasattr(slide, "shapes"):
            for shape in slide.shapes:
                if shape.has_table:
                    table = shape.table
                    html_table = "<table border='1' cellpadding='5' cellspacing='0'>"
                    table_content = []
                    
                    for row in table.rows:
                        row_values = []
                        html_row = "<tr>"
                        
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            row_values.append(cell_text)
                            html_row += f"<td>{cell_text}</td>"
                        
                        html_row += "</tr>"
                        html_table += html_row
                        table_content.append(" | ".join(row_values))
                    
                    html_table += "</table>"
                    html_parts.append(html_table)
                    content_parts.append("\n".join(table_content))
    
    content = "\n\n".join(content_parts)
    html_content = "\n".join(html_parts)
    
    return content, html_content
