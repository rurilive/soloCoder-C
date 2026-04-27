from pathlib import Path
from docx import Document as DocxDocument
from zipfile import BadZipFile
import olefile
import struct
import re


def is_docx_file(file_path: str) -> bool:
    """
    检测文件是否是 .docx 格式（Open XML/ZIP格式）
    """
    with open(file_path, 'rb') as f:
        header = f.read(4)
        return header == b'PK\x03\x04'


def is_doc_file(file_path: str) -> bool:
    """
    检测文件是否是旧版 .doc 格式（OLE格式）
    """
    return olefile.isOleFile(file_path)


def _is_unicode_word(word_data: bytes) -> bool:
    """
    检测 Word 文档是否使用 Unicode 编码
    """
    try:
        flags = struct.unpack('<H', word_data[0xA:0xC])[0]
        return (flags & 0x0100) != 0
    except:
        return False


def _clean_word_text(text: str) -> str:
    """
    清理从 Word 文档中提取的文本
    """
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    text = re.sub(r'\x0D\x0A|\x0D|\x0A', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text.strip()


def extract_simple_text(data: bytes) -> str:
    """
    简单地从二进制数据中提取可打印字符
    """
    text_parts = []
    current_text = []
    
    for i in range(0, len(data) - 1, 2):
        try:
            char = data[i:i+2].decode('utf-16-le', errors='ignore')
            if char and (char.isprintable() or char in '\n\r\t'):
                current_text.append(char)
            elif current_text:
                text = ''.join(current_text)
                if len(text) > 3:
                    text_parts.append(text)
                current_text = []
        except:
            if current_text:
                text = ''.join(current_text)
                if len(text) > 3:
                    text_parts.append(text)
                current_text = []
    
    if current_text:
        text = ''.join(current_text)
        if len(text) > 3:
            text_parts.append(text)
    
    result = '\n'.join(text_parts)
    return _clean_word_text(result)


def extract_text_from_doc(file_path: str) -> str:
    """
    从旧版 .doc 文件（OLE格式）中提取文本
    这是一个简化的实现，尝试从 WordDocument 流中提取文本
    """
    if not olefile.isOleFile(file_path):
        return ""
    
    try:
        ole = olefile.OleFileIO(file_path)
        
        if not ole.exists('WordDocument'):
            ole.close()
            return ""
        
        word_stream = ole.openstream('WordDocument')
        word_data = word_stream.read()
        word_stream.close()
        
        ole.close()
        
        try:
            fc_min = struct.unpack('<I', word_data[0x18:0x1C])[0]
            fc_max = struct.unpack('<I', word_data[0x1C:0x20])[0]
            
            if 0 < fc_min < fc_max <= len(word_data):
                text_content = word_data[fc_min:fc_max]
                
                encoding = 'utf-16-le' if _is_unicode_word(word_data) else 'latin-1'
                
                try:
                    text = text_content.decode(encoding, errors='ignore')
                    text = _clean_word_text(text)
                    return text
                except:
                    pass
        except:
            pass
        
        try:
            text = word_data.decode('utf-16-le', errors='ignore')
            text = _clean_word_text(text)
            if len(text.strip()) > 10:
                return text
        except:
            pass
        
        try:
            text = word_data.decode('latin-1', errors='ignore')
            text = _clean_word_text(text)
            if len(text.strip()) > 10:
                return text
        except:
            pass
        
        return extract_simple_text(word_data)
        
    except Exception as e:
        print(f"Error extracting text from .doc file: {e}")
        return ""


def parse_docx(file_path: str) -> tuple[str, str]:
    """
    解析 .docx 文件（Open XML格式）
    """
    doc = DocxDocument(file_path)
    
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


def parse_old_doc(file_path: str) -> tuple[str, str]:
    """
    解析旧版 .doc 文件（OLE格式）
    """
    text = extract_text_from_doc(file_path)
    
    if not text or len(text.strip()) < 10:
        with open(file_path, 'rb') as f:
            data = f.read()
            text = extract_simple_text(data)
    
    paragraphs = text.split('\n\n')
    
    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if para:
            if len(para) < 100 and not para.endswith(('.', '。', '!', '！', '?', '？')):
                html_parts.append(f"<h3>{para}</h3>")
            else:
                html_parts.append(f"<p>{para}</p>")
    
    html_content = "\n".join(html_parts)
    
    return text, html_content


def parse_doc(file_path: str) -> tuple[str, str]:
    """
    解析Word文档，自动检测格式并选择合适的解析器
    """
    file_path = Path(file_path)
    
    if is_docx_file(str(file_path)):
        return parse_docx(str(file_path))
    
    elif is_doc_file(str(file_path)):
        text, html = parse_old_doc(str(file_path))
        if text and len(text.strip()) > 10:
            return text, html
        else:
            return f"[旧版Word文档 (.doc) - 部分内容可能无法完全提取]", "<p><em>旧版Word文档 (.doc) - 部分内容可能无法完全提取</em></p>"
    
    else:
        try:
            return parse_docx(str(file_path))
        except BadZipFile:
            try:
                if olefile.isOleFile(str(file_path)):
                    text, html = parse_old_doc(str(file_path))
                    if text and len(text.strip()) > 10:
                        return text, html
            except:
                pass
            
            return f"[不支持的Word文档格式]", "<p><em>不支持的Word文档格式</em></p>"
