from openpyxl import load_workbook
from pathlib import Path


def parse_excel(file_path: str) -> tuple[str, str]:
    """
    解析Excel文件（.xlsx），返回原始内容和HTML内容
    """
    file_path = Path(file_path)
    wb = load_workbook(file_path, data_only=True)
    
    content_parts = []
    html_parts = []
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        content_parts.append(f"=== 工作表: {sheet_name} ===")
        html_parts.append(f"<h2>工作表: {sheet_name}</h2>")
        
        html_table = "<table border='1' cellpadding='5' cellspacing='0'>"
        
        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
            row_values = []
            html_row = "<tr>"
            
            for cell_value in row:
                cell_text = str(cell_value) if cell_value is not None else ""
                row_values.append(cell_text)
                
                tag = "th" if row_idx == 0 else "td"
                html_row += f"<{tag}>{cell_text}</{tag}>"
            
            html_row += "</tr>"
            html_table += html_row
            content_parts.append(" | ".join(row_values))
        
        html_table += "</table>"
        html_parts.append(html_table)
    
    content = "\n\n".join(content_parts)
    html_content = "\n".join(html_parts)
    
    return content, html_content
