from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path


def parse_doc(file_path: str) -> tuple[str, str]:
    """
    解析Word文档（.docx），返回原始内容和HTML内容
    """
    file_path = Path(file_path)
    doc = Document(file_path)
    
    content_parts = []
    html_parts = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            content_parts.append(text)
            
            style = para.style.name.lower()
            if 'heading 1' in style:
                html_parts.append(f"<h1>{text}</h1>")
            elif 'heading 2' in style:
                html_parts.append(f"<h2>{text}</h2>")
            elif 'heading 3' in style:
                html_parts.append(f"<h3>{text}</h3>")
            elif 'heading 4' in style:
                html_parts.append(f"<h4>{text}</h4>")
            elif 'heading 5' in style:
                html_parts.append(f"<h5>{text}</h5>")
            elif 'heading 6' in style:
                html_parts.append(f"<h6>{text}</h6>")
            elif 'list' in style or 'bullet' in style:
                html_parts.append(f"<li>{text}</li>")
            else:
                html_parts.append(f"<p>{text}</p>")
    
    for table in doc.tables:
        html_table = "<table border='1' cellpadding='5' cellspacing='0'>"
        for row in table.rows:
            html_table += "<tr>"
            for cell in row.cells:
                cell_text = cell.text.strip()
                html_table += f"<td>{cell_text}</td>"
            html_table += "</tr>"
            content_parts.append(" | ".join([cell.text.strip() for cell in row.cells]))
        html_table += "</table>"
        html_parts.append(html_table)
    
    content = "\n\n".join(content_parts)
    html_content = "\n".join(html_parts)
    
    return content, html_content
