from pathlib import Path
from docx import Document as DocxDocument
from zipfile import BadZipFile
import olefile
import struct
import re
import chardet

try:
    from pyantiword.antiword_wrapper import extract_text_with_antiword as antiword_extract_text
    HAS_ANTIWORD = True
except ImportError:
    HAS_ANTIWORD = False


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


def _detect_encoding(data: bytes) -> str:
    """
    使用 chardet 检测字节数据的编码
    """
    if not data or len(data) == 0:
        return 'utf-8'
    
    try:
        result = chardet.detect(data)
        if result and result['encoding']:
            confidence = result.get('confidence', 0)
            if confidence > 0.5:
                return result['encoding']
    except:
        pass
    
    return 'utf-8'


def _clean_word_text(text: str) -> str:
    """
    清理从 Word 文档中提取的文本
    """
    if not text:
        return ""
    
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    text = re.sub(r'\x0D\x0A|\x0D|\x0A', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text.strip()


def _is_highly_likely_valid_text(text: str) -> bool:
    """
    更严格地检测文本是否可能是有效的可读文本
    """
    if not text or len(text.strip()) < 20:
        return False
    
    total_chars = len(text)
    if total_chars == 0:
        return False
    
    printable_chars = sum(1 for c in text if c.isprintable() or c in '\n\r\t ')
    printable_ratio = printable_chars / total_chars
    
    if printable_ratio < 0.7:
        return False
    
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_letters = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    digits = sum(1 for c in text if c.isdigit())
    
    meaningful_chars = chinese_chars + english_letters + digits
    meaningful_ratio = meaningful_chars / total_chars
    
    if meaningful_ratio < 0.3:
        return False
    
    weird_chars = sum(1 for c in text if (
        '\u0080' <= c <= '\u00FF' or
        '\u0100' <= c <= '\u017F' or
        '\u0180' <= c <= '\u024F' or
        '\u0250' <= c <= '\u02AF' or
        '\u1E00' <= c <= '\u1EFF' or
        '\u2C60' <= c <= '\u2C7F' or
        '\uA720' <= c <= '\uA7FF' or
        '\uAB30' <= c <= '\uAB6F' or
        '\uFB00' <= c <= '\uFB4F' or
        '\uFF00' <= c <= '\uFFEF' or
        c in '⸀㬆ᨆఀ䭓쌀ꐀ؆㔊᐀Ȁ␀㨀☆ᔀ䤊꬀ᔊ Ȁఁ䘀'
    ))
    
    if weird_chars > total_chars * 0.1:
        return False
    
    control_chars = sum(1 for c in text if (
        '\u2000' <= c <= '\u206F' or
        '\uFFF0' <= c <= '\uFFFF' or
        '\uE000' <= c <= '\uF8FF'
    ))
    
    if control_chars > total_chars * 0.05:
        return False
    
    if chinese_chars > 10:
        return True
    
    if english_letters > 50:
        common_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'own', 'say', 'she', 'too', 'use', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'been', 'call', 'make', 'come', 'time', 'just', 'know', 'take', 'into', 'year', 'some', 'want', 'look', 'work', 'give', 'over', 'think', 'most', 'find', 'day', 'also', 'after', 'way', 'many', 'must', 'look', 'before', 'great', 'back', 'through', 'long', 'where', 'much', 'should', 'well', 'people', 'down', 'own', 'upon', 'good', 'part', 'place', 'write', 'word', 'about', 'read', 'man', 'find', 'change', 'went', 'light', 'kind', 'off', 'need', 'house', 'picture', 'try', 'again', 'animal', 'point', 'mother', 'world', 'near', 'build', 'self', 'earth', 'father', 'head', 'stand', 'page', 'country', 'found', 'answer', 'school', 'grow', 'study', 'learn', 'plant', 'cover', 'food', 'sun', 'thought', 'let', 'keep', 'eye', 'never', 'last', 'door', 'between', 'city', 'tree', 'cross', 'since', 'hard', 'start', 'might', 'story', 'saw', 'far', 'sea', 'draw', 'left', 'late', 'run', "don't", 'while', 'press', 'close', 'night', 'real', 'life', 'few', 'north', 'book', 'carry', 'took', 'science', 'eat', 'room', 'friend', 'began', 'idea', 'fish', 'mountain', 'stop', 'once', 'base', 'hear', 'horse', 'cut', 'sure', 'watch', 'color', 'face', 'wood', 'main', 'open', 'seem', 'together', 'next', 'white', 'children', 'begin', 'got', 'walk', 'example', 'ease', 'paper', 'group', 'always', 'music', 'those', 'both', 'mark', 'often', 'letter', 'until', 'mile', 'river', 'car', 'feet', 'care', 'second', 'book', 'remember', 'early', 'game', 'line', 'quite', 'move', 'thing', 'light', 'kilogram', 'common', 'come', 'difference', 'use', 'language', 'govern', 'please', 'simple', 'third', 'order', 'fire', 'south', 'problem', 'full', 'hear', 'ask', 'force', 'air', 'today', 'important', 'play', 'still', 'learn', 'water', 'little', 'small', 'round', 'man', 'year', 'woman', 'should', 'call', 'ask', 'show', 'try', 'put', 'take', 'get', 'make', 'feel', 'leave', 'let', 'begin', 'seem', 'help', 'talk', 'turn', 'start', 'keep', 'hold', 'write', 'become', 'like', 'love', 'use', 'find', 'give', 'tell', 'work', 'follow', 'act', 'speak', 'read', 'pass', 'die', 'send', 'receive', 'believe', 'accept', 'allow', 'break', 'bring', 'build', 'buy', 'catch', 'choose', 'come', 'cost', 'cut', 'do', 'draw', 'drink', 'drive', 'eat', 'fall', 'feel', 'fight', 'find', 'fly', 'forget', 'get', 'give', 'go', 'grow', 'have', 'hear', 'hit', 'hold', 'hurt', 'keep', 'know', 'lay', 'lead', 'learn', 'leave', 'lend', 'let', 'lie', 'light', 'lose', 'make', 'mean', 'meet', 'pay', 'put', 'read', 'ride', 'ring', 'run', 'say', 'see', 'sell', 'send', 'set', 'shake', 'shine', 'show', 'shut', 'sing', 'sit', 'sleep', 'speak', 'spend', 'stand', 'steal', 'stick', 'strike', 'swear', 'sweep', 'swim', 'take', 'teach', 'tear', 'tell', 'think', 'throw', 'understand', 'wake', 'wear', 'win', 'write']
        text_lower = text.lower()
        for word in common_words:
            if f' {word} ' in text_lower or text_lower.startswith(f'{word} ') or text_lower.endswith(f' {word}'):
                return True
    
    if text.count(' ') > len(text) * 0.03 and text.count('\n') > 0:
        return True
    
    return False


def _is_likely_valid_text(text: str) -> bool:
    """
    检测文本是否可能是有效的可读文本（较宽松版本）
    """
    if not text or len(text.strip()) < 10:
        return False
    
    total_chars = len(text)
    if total_chars == 0:
        return False
    
    printable_chars = sum(1 for c in text if c.isprintable() or c in '\n\r\t ')
    printable_ratio = printable_chars / total_chars
    
    if printable_ratio < 0.6:
        return False
    
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    ascii_ratio = ascii_chars / total_chars
    
    if ascii_ratio > 0.3:
        common_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'own', 'say', 'she', 'too', 'use']
        text_lower = text.lower()
        for word in common_words:
            if f' {word} ' in text_lower or text_lower.startswith(f'{word} ') or text_lower.endswith(f' {word}'):
                return True
    
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if chinese_chars > 5:
        return True
    
    if text.count(' ') > len(text) * 0.05 and text.count('\n') > 0:
        return True
    
    return False


def _smart_split_paragraphs(text: str) -> list:
    """
    智能分割段落，考虑多种换行符组合
    """
    if not text:
        return []
    
    paragraphs = []
    current_para = []
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.rstrip()
        
        if not line:
            if current_para:
                paragraphs.append('\n'.join(current_para))
                current_para = []
        else:
            current_para.append(line)
    
    if current_para:
        paragraphs.append('\n'.join(current_para))
    
    return paragraphs


def _is_likely_english_heading(para: str) -> tuple:
    """
    判断是否是英文标题
    返回: (是否是标题, 标题级别h1-h6)
    """
    if not para or len(para.strip()) == 0:
        return False, None
    
    para = para.strip()
    para_len = len(para)
    
    if para_len > 80:
        return False, None
    
    chinese_count = sum(1 for c in para if '\u4e00' <= c <= '\u9fff')
    english_letters = sum(1 for c in para if c.isalpha() and ord(c) < 128)
    
    total_chars = chinese_count + english_letters
    if total_chars == 0:
        return False, None
    
    english_ratio = english_letters / total_chars
    
    if english_ratio > 0.7:
        if para.isupper() and para_len >= 2:
            if para_len <= 10:
                return True, 'h1'
            elif para_len <= 20:
                return True, 'h2'
            else:
                return True, 'h3'
        
        words = para.split()
        if len(words) >= 1 and len(words) <= 10:
            title_case = all(word and word[0].isupper() for word in words if word)
            if title_case and not para.endswith(('.', '!', '?', ',', ';', ':')):
                if para_len <= 15:
                    return True, 'h2'
                elif para_len <= 30:
                    return True, 'h3'
                elif para_len <= 50:
                    return True, 'h4'
                else:
                    return True, 'h5'
        
        if english_ratio > 0.9 and para_len <= 30:
            if not para.endswith(('.', '!', '?', ',', ';', ':')):
                if para_len <= 15:
                    return True, 'h3'
                else:
                    return True, 'h4'
    
    return False, None


def _is_likely_heading(para: str, prev_para: str = None, next_para: str = None) -> tuple:
    """
    智能判断段落是否是标题
    返回: (是否是标题, 标题级别h1-h6)
    """
    if not para or len(para.strip()) == 0:
        return False, None
    
    para = para.strip()
    para_len = len(para)
    
    heading_patterns = [
        (r'^第[一二三四五六七八九十百千\d]+[章节篇条]\s*[：:]*\s*', 1),
        (r'^[一二三四五六七八九十]+[、.．]\s*', 2),
        (r'^(\d+)[\.．、]\s*', 2),
        (r'^(\d+\.\d+)[\.．\s]*', 3),
        (r'^(\d+\.\d+\.\d+)[\.．\s]*', 4),
        (r'^[（(]\d+[)）]\s*', 3),
        (r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*', 3),
    ]
    
    for pattern, level in heading_patterns:
        if re.match(pattern, para):
            return True, f'h{level}'
    
    is_eng_heading, eng_level = _is_likely_english_heading(para)
    if is_eng_heading:
        return True, eng_level
    
    if para_len <= 80:
        ends_with_punctuation = para.endswith(('。', '！', '？', '，', '；', '：', '.', '!', '?', ',', ';', ':'))
        
        if not ends_with_punctuation:
            chinese_count = sum(1 for c in para if '\u4e00' <= c <= '\u9fff')
            if chinese_count > 0:
                has_common_words = any(word in para for word in ['的', '是', '在', '了', '和', '与', '或', '中', '上', '下', '这', '那', '有', '为', '以', '及', '等', '也', '都', '就', '被', '把', '让', '给', '到', '从', '向', '对', '跟', '和', '同', '与', '比', '被', '把', '让', '给', '到', '从', '向', '对', '跟'])
                
                if not has_common_words:
                    has_next_content = next_para and len(next_para.strip()) > 50
                    has_prev_content = prev_para and len(prev_para.strip()) > 0
                    
                    if has_next_content or (not has_prev_content and not next_para):
                        if para_len <= 15:
                            return True, 'h2'
                        elif para_len <= 30:
                            return True, 'h3'
                        elif para_len <= 50:
                            return True, 'h4'
                        else:
                            return True, 'h5'
            
            if prev_para and len(prev_para.strip()) > 0:
                if next_para and len(next_para.strip()) > 100:
                    return True, 'h3'
    
    return False, None


def _is_list_item(para: str) -> tuple:
    """
    判断段落是否是列表项
    返回: (是否是列表项, 列表类型: 'ul' 或 'ol', 列表项内容)
    """
    if not para or len(para.strip()) == 0:
        return False, None, None
    
    para = para.strip()
    
    ul_patterns = [
        r'^[•●○■□◆◇★☆►▶▸▹▻▪▫▬▭▮▯]\s*',
        r'^[-–—]\s+',
        r'^[*＊]\s+',
        r'^[√√✓✔✕✖✗✘]\s*',
        r'^\s*[•●○■□◆◇★☆►▶▸▹▻▪▫▬▭▮▯]\s*',
    ]
    
    for pattern in ul_patterns:
        match = re.match(pattern, para)
        if match:
            content = para[match.end():].strip()
            return True, 'ul', content
    
    ol_patterns = [
        (r'^(\d+)[\.．、)\s]+', 'ol'),
        (r'^[（(](\d+)[)）]\s*', 'ol'),
        (r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*', 'ol'),
        (r'^[一二三四五六七八九十]+[、.．)\s]+', 'ol'),
        (r'^[（(][一二三四五六七八九十]+[)）]\s*', 'ol'),
    ]
    
    for pattern, list_type in ol_patterns:
        match = re.match(pattern, para)
        if match:
            content = para[match.end():].strip()
            return True, list_type, content
    
    return False, None, None


def _convert_text_to_html(text: str) -> str:
    """
    智能转换文本到HTML，识别标题、列表、段落等格式
    """
    if not text or len(text.strip()) == 0:
        return ""
    
    paragraphs = _smart_split_paragraphs(text)
    
    if not paragraphs:
        return ""
    
    html_parts = []
    in_list = False
    list_type = None
    
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        
        prev_para = paragraphs[i-1].strip() if i > 0 else None
        next_para = paragraphs[i+1].strip() if i < len(paragraphs)-1 else None
        
        is_list, current_list_type, list_content = _is_list_item(para)
        
        if is_list:
            if not in_list or list_type != current_list_type:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                list_type = current_list_type
                html_parts.append(f'<{list_type}>')
                in_list = True
            
            html_parts.append(f'<li>{list_content}</li>')
            continue
        
        if in_list:
            html_parts.append(f'</{list_type}>')
            in_list = False
            list_type = None
        
        is_heading, heading_level = _is_likely_heading(para, prev_para, next_para)
        
        if is_heading and heading_level:
            html_parts.append(f'<{heading_level}>{para}</{heading_level}>')
            continue
        
        para_lines = para.split('\n')
        if len(para_lines) > 1:
            para = '<br>'.join(para_lines)
        
        html_parts.append(f'<p>{para}</p>')
    
    if in_list:
        html_parts.append(f'</{list_type}>')
    
    return '\n'.join(html_parts)


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


def _try_decode_with_encoding(data: bytes, encoding: str) -> str:
    """
    尝试使用指定编码解码字节数据
    """
    try:
        text = data.decode(encoding, errors='strict')
        return text
    except:
        try:
            text = data.decode(encoding, errors='ignore')
            return text
        except:
            return ""


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
        
        extracted_texts = []
        
        try:
            fc_min = struct.unpack('<I', word_data[0x18:0x1C])[0]
            fc_max = struct.unpack('<I', word_data[0x1C:0x20])[0]
            
            if 0 < fc_min < fc_max <= len(word_data):
                text_content = word_data[fc_min:fc_max]
                
                detected_encoding = _detect_encoding(text_content)
                
                encodings_to_try = [
                    detected_encoding,
                    'utf-16-le',
                    'utf-16-be',
                    'gbk',
                    'gb2312',
                    'gb18030',
                    'big5',
                    'shift_jis',
                    'euc-jp',
                    'euc-kr',
                    'utf-8',
                    'latin-1',
                    'cp1252',
                ]
                
                tried_encodings = set()
                for encoding in encodings_to_try:
                    if encoding and encoding.lower() not in tried_encodings:
                        tried_encodings.add(encoding.lower())
                        try:
                            text = _try_decode_with_encoding(text_content, encoding)
                            cleaned_text = _clean_word_text(text)
                            if cleaned_text and len(cleaned_text.strip()) > 20:
                                if _is_highly_likely_valid_text(cleaned_text):
                                    return cleaned_text
                                elif _is_likely_valid_text(cleaned_text):
                                    extracted_texts.append(cleaned_text)
                        except:
                            continue
        except:
            pass
        
        for encoding in ['utf-16-le', 'utf-16-be', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-8', 'latin-1', 'cp1252']:
            try:
                text = _try_decode_with_encoding(word_data, encoding)
                cleaned_text = _clean_word_text(text)
                if cleaned_text and len(cleaned_text.strip()) > 20:
                    if _is_highly_likely_valid_text(cleaned_text):
                        return cleaned_text
                    elif _is_likely_valid_text(cleaned_text):
                        extracted_texts.append(cleaned_text)
            except:
                continue
        
        simple_text = extract_simple_text(word_data)
        if simple_text and len(simple_text.strip()) > 20:
            if _is_highly_likely_valid_text(simple_text):
                return simple_text
            elif _is_likely_valid_text(simple_text):
                extracted_texts.append(simple_text)
        
        if extracted_texts:
            extracted_texts.sort(key=lambda x: (
                _is_highly_likely_valid_text(x),
                sum(1 for c in x if '\u4e00' <= c <= '\u9fff' or c.isalpha()),
                len(x)
            ), reverse=True)
            
            for text in extracted_texts:
                if _is_highly_likely_valid_text(text):
                    return text
            
            return extracted_texts[0]
        
        return ""
        
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
    优先使用 pyantiword，如果失败则使用自定义解析逻辑
    """
    text = ""
    
    if HAS_ANTIWORD:
        try:
            text = antiword_extract_text(file_path)
            if text:
                text = text.strip()
                if len(text) > 10:
                    text = _clean_word_text(text)
                    if _is_highly_likely_valid_text(text):
                        html_content = _convert_text_to_html(text)
                        return text, html_content
                    elif _is_likely_valid_text(text):
                        pass
        except Exception as e:
            print(f"Error using pyantiword: {e}, falling back to custom parser")
    
    text = extract_text_from_doc(file_path)
    
    if not text or len(text.strip()) < 10:
        with open(file_path, 'rb') as f:
            data = f.read()
            text = extract_simple_text(data)
    
    if not text or not _is_likely_valid_text(text):
        return "[旧版Word文档 (.doc) - 无法提取有效内容]", "<p><em>旧版Word文档 (.doc) - 无法提取有效内容</em></p>"
    
    html_content = _convert_text_to_html(text)
    
    return text, html_content


def parse_doc(file_path: str) -> tuple[str, str]:
    """
    解析Word文档，自动检测格式并选择合适的解析器
    """
    file_path = Path(file_path)
    
    try:
        if is_docx_file(str(file_path)):
            return parse_docx(str(file_path))
        
        elif is_doc_file(str(file_path)):
            text, html = parse_old_doc(str(file_path))
            if text and _is_likely_valid_text(text):
                return text, html
            else:
                return f"[旧版Word文档 (.doc) - 无法提取有效内容]", "<p><em>旧版Word文档 (.doc) - 无法提取有效内容</em></p>"
        
        else:
            try:
                return parse_docx(str(file_path))
            except BadZipFile:
                try:
                    if olefile.isOleFile(str(file_path)):
                        text, html = parse_old_doc(str(file_path))
                        if text and _is_likely_valid_text(text):
                            return text, html
                except:
                    pass
                
                return f"[不支持的Word文档格式]", "<p><em>不支持的Word文档格式</em></p>"
    except Exception as e:
        print(f"Error parsing Word document: {e}")
        return f"[文档解析错误: {str(e)}]", f"<p><em>文档解析错误: {str(e)}</em></p>"
