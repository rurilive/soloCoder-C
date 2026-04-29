from pathlib import Path
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from zipfile import BadZipFile
import olefile
import struct
import re
import chardet
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = Path(__file__).resolve().parent.parent.parent / 'log'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'doc_parser.log'

logger = logging.getLogger('doc_parser')
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
logger.info("doc_parser 模块初始化")
logger.info(f"日志文件: {LOG_FILE}")
logger.info("=" * 60)

try:
    from pyantiword.antiword_wrapper import extract_text_with_antiword as antiword_extract_text
    HAS_ANTIWORD = True
    logger.info("✅ pyantiword 已导入，函数: extract_text_with_antiword")
except ImportError as e:
    HAS_ANTIWORD = False
    logger.warning(f"⚠️ pyantiword 导入失败: {e}")

try:
    import mammoth
    HAS_MAMMOTH = True
    logger.info("✅ mammoth 已导入，可以更好地解析 docx 格式")
except ImportError as e:
    HAS_MAMMOTH = False
    logger.warning(f"⚠️ mammoth 导入失败: {e}，将使用 python-docx 作为备选")


def is_docx_file(file_path: str) -> bool:
    """
    检测文件是否是 .docx 格式（Open XML/ZIP格式）
    """
    logger.debug(f"[is_docx_file] 检查文件: {file_path}")
    with open(file_path, 'rb') as f:
        header = f.read(4)
        result = header == b'PK\x03\x04'
        logger.debug(f"[is_docx_file] 文件头: {header}, 结果: {result}")
        return result


def is_doc_file(file_path: str) -> bool:
    """
    检测文件是否是旧版 .doc 格式（OLE格式）
    """
    logger.debug(f"[is_doc_file] 检查文件: {file_path}")
    result = olefile.isOleFile(file_path)
    logger.debug(f"[is_doc_file] 结果: {result}")
    return result


def _get_alignment_style(alignment) -> str:
    """
    将 python-docx 的段落对齐枚举转换为 CSS text-align 样式
    返回: CSS 样式字符串，如 "text-align: center;"，如果是默认左对齐则返回空字符串
    """
    if alignment is None:
        return ""
    
    alignment_map = {
        WD_ALIGN_PARAGRAPH.LEFT: "",
        WD_ALIGN_PARAGRAPH.CENTER: "text-align: center;",
        WD_ALIGN_PARAGRAPH.RIGHT: "text-align: right;",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "text-align: justify;",
        WD_ALIGN_PARAGRAPH.DISTRIBUTE: "text-align: justify;",
        WD_ALIGN_PARAGRAPH.JUSTIFY_MED: "text-align: justify;",
        WD_ALIGN_PARAGRAPH.JUSTIFY_HI: "text-align: justify;",
        WD_ALIGN_PARAGRAPH.JUSTIFY_LOW: "text-align: justify;",
    }
    
    return alignment_map.get(alignment, "")


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
            logger.debug(f"[_detect_encoding] 检测到编码: {result['encoding']}, 置信度: {confidence}")
            if confidence > 0.5:
                return result['encoding']
    except:
        pass
    
    return 'utf-8'


def _smart_clean_text(text: str) -> str:
    """
    智能清理从 Word 文档中提取的文本
    保留段落结构，只清理不可见字符
    """
    if not text:
        return ""
    
    logger.debug(f"[_smart_clean_text] 清理前长度: {len(text)}")
    logger.debug(f"[_smart_clean_text] 原始内容 (repr): {repr(text[:200])}")
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', line)
        
        original_line = line
        line = line.rstrip()
        
        if re.match(r'^\s+\S', line):
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 20:
                logger.debug(f"[_smart_clean_text] 行前有大量空格 ({leading_spaces}个)，可能是缩进格式: {repr(original_line[:50])}")
        
        cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    logger.debug(f"[_smart_clean_text] 清理后长度: {len(result)}")
    logger.debug(f"[_smart_clean_text] 清理后内容 (repr): {repr(result[:200])}")
    
    return result


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
        common_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'own', 'say', 'she', 'too', 'use', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'been', 'call', 'make', 'come', 'time', 'just', 'know', 'take', 'into', 'year', 'some', 'want', 'look', 'work', 'give', 'over', 'think', 'most', 'find', 'day', 'also', 'after', 'way', 'many', 'must', 'look', 'before', 'great', 'back', 'through', 'long', 'where', 'much', 'should', 'well', 'people', 'down', 'own', 'upon', 'good', 'part', 'place', 'write', 'word', 'about', 'read', 'man', 'find', 'change', 'went', 'light', 'kind', 'off', 'need', 'house', 'picture', 'try', 'again', 'animal', 'point', 'mother', 'world', 'near', 'build', 'self', 'earth', 'father', 'head', 'stand', 'page', 'country', 'found', 'answer', 'school', 'grow', 'study', 'learn', 'plant', 'cover', 'food', 'sun', 'thought', 'let', 'keep', 'eye', 'never', 'last', 'door', 'between', 'city', 'tree', 'cross', 'since', 'hard', 'start', 'might', 'story', 'saw', 'far', 'sea', 'draw', 'left', 'late', 'run', "don't", 'while', 'press', 'close', 'night', 'real', 'life', 'few', 'north', 'book', 'carry', 'took', 'science', 'eat', 'room', 'friend', 'began', 'idea', 'fish', 'mountain', 'stop', 'once', 'base', 'hear', 'horse', 'cut', 'sure', 'watch', 'color', 'face', 'wood', 'main', 'open', 'seem', 'together', 'next', 'white', 'children', 'begin', 'got', 'walk', 'example', 'ease', 'paper', 'group', 'always', 'music', 'those', 'both', 'mark', 'often', 'letter', 'until', 'mile', 'river', 'car', 'feet', 'care', 'second', 'book', 'remember', 'early', 'game', 'line', 'quite', 'move', 'thing', 'light', 'kilogram', 'common', 'come', 'difference', 'use', 'language', 'govern', 'please', 'simple', 'third', 'order', 'fire', 'south', 'problem', 'full', 'hear', 'ask', 'force', 'air', 'today', 'important', 'girl', 'leave', 'continue', 'family', 'later', 'show', 'interest', 'state', 'same', 'fact', 'during', 'general', 'public', 'small', 'large', 'little', 'only', 'such', 'other', 'each', 'which', 'their', 'these', 'those', 'some', 'any', 'every', 'each', 'all', 'both', 'few', 'most', 'other', 'some', 'such', 'that', 'this', 'these', 'those', 'what', 'which', 'who', 'whom', 'whose', 'why', 'how', 'when', 'where', 'whether', 'why']
        
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
    改进：更好地处理 Word 文档中的格式
    """
    if not text:
        return []
    
    logger.debug(f"[_smart_split_paragraphs] 原始文本长度: {len(text)}")
    logger.debug(f"[_smart_split_paragraphs] 原始文本 (repr): {repr(text[:300])}")
    
    lines = text.split('\n')
    logger.debug(f"[_smart_split_paragraphs] 按 \\n 分割为 {len(lines)} 行")
    
    paragraphs = []
    current_para = []
    blank_line_count = 0
    
    for i, line in enumerate(lines):
        line = line.rstrip()
        
        if not line:
            blank_line_count += 1
            if current_para:
                para_text = ' '.join(current_para).strip()
                if para_text:
                    paragraphs.append(para_text)
                current_para = []
            continue
        
        blank_line_count = 0
        
        line_stripped = line.strip()
        
        if line.startswith('|') and line.endswith('|'):
            if current_para:
                para_text = ' '.join(current_para).strip()
                if para_text:
                    paragraphs.append(para_text)
                current_para = []
            paragraphs.append(line)
            continue
        
        leading_spaces = len(line) - len(line.lstrip())
        
        if leading_spaces > 10 and current_para:
            logger.debug(f"[_smart_split_paragraphs] 行 {i} 有大量前导空格 ({leading_spaces}个)，可能是新段落: {repr(line_stripped[:30])}")
            para_text = ' '.join(current_para).strip()
            if para_text:
                paragraphs.append(para_text)
            current_para = [line_stripped]
            continue
        
        if current_para:
            last_para = current_para[-1]
            if last_para and last_para.endswith(('。', '！', '？', '；', '：', '.', '!', '?', ';', ':')):
                logger.debug(f"[_smart_split_paragraphs] 前一行以标点结尾，可能是新段落")
                para_text = ' '.join(current_para).strip()
                if para_text:
                    paragraphs.append(para_text)
                current_para = [line_stripped]
                continue
        
        current_para.append(line_stripped)
    
    if current_para:
        para_text = ' '.join(current_para).strip()
        if para_text:
            paragraphs.append(para_text)
    
    logger.debug(f"[_smart_split_paragraphs] 最终分割为 {len(paragraphs)} 个段落")
    for i, para in enumerate(paragraphs):
        logger.debug(f"  [{i}] {repr(para[:50])}")
    
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
    logger.debug(f"[_is_likely_english_heading] 英文比例: {english_ratio:.2f}, 长度: {para_len}, 内容: {repr(para)}")
    
    if chinese_count == 0 and english_ratio > 0.8:
        logger.debug(f"[_is_likely_english_heading] 纯英文段落，可能是标题")
        
        if para.isupper() and para_len >= 2:
            logger.debug(f"[_is_likely_english_heading] 全部大写英文，识别为标题")
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
                logger.debug(f"[_is_likely_english_heading] 标题格式英文，识别为标题")
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
                logger.debug(f"[_is_likely_english_heading] 纯英文短句，识别为标题")
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
    
    if para.startswith('|') and para.endswith('|'):
        return False, None
    
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
            logger.debug(f"[_is_likely_heading] 匹配标题模式: {para[:30]}..., 级别: h{level}")
            return True, f'h{level}'
    
    is_eng_heading, eng_level = _is_likely_english_heading(para)
    if is_eng_heading:
        logger.debug(f"[_is_likely_heading] 识别为英文标题: {para[:30]}..., 级别: {eng_level}")
        return True, eng_level
    
    if para_len <= 80:
        ends_with_punctuation = para.endswith(('。', '！', '？', '，', '；', '：', '.', '!', '?', ',', ';', ':'))
        
        if not ends_with_punctuation:
            chinese_count = sum(1 for c in para if '\u4e00' <= c <= '\u9fff')
            if chinese_count > 0:
                has_common_words = any(word in para for word in ['的', '是', '在', '了', '和', '与', '或', '中', '上', '下', '这', '那', '有', '为', '以', '及', '等', '也', '都', '就', '被', '把', '让', '给', '到', '从', '向', '对', '跟', '和', '同', '与', '比', '被', '把', '让', '给', '到', '从', '向', '对', '跟'])
                
                if has_common_words:
                    logger.debug(f"[_is_likely_heading] 包含常见连接词，不识别为标题: {para[:30]}...")
                    return False, None
                
                has_next_content = next_para and len(next_para.strip()) > 50
                has_prev_content = prev_para and len(prev_para.strip()) > 0
                
                if has_next_content or (not has_prev_content and not next_para):
                    logger.debug(f"[_is_likely_heading] 识别为中文标题: {para[:30]}...")
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
                    logger.debug(f"[_is_likely_heading] 上下文判断为标题: {para[:30]}...")
                    return True, 'h3'
    
    logger.debug(f"[_is_likely_heading] 不识别为标题: {para[:30]}...")
    return False, None


def _is_list_item(para: str) -> tuple:
    """
    判断段落是否是列表项
    返回: (是否是列表项, 列表类型: 'ul' 或 'ol', 列表项内容)
    """
    if not para or len(para.strip()) == 0:
        return False, None, None
    
    if para.startswith('|') and para.endswith('|'):
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
            logger.debug(f"[_is_list_item] 识别为无序列表项: {content[:30]}...")
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
            logger.debug(f"[_is_list_item] 识别为有序列表项: {content[:30]}...")
            return True, list_type, content
    
    return False, None, None


def _is_table_row(para: str) -> bool:
    """
    判断段落是否是表格行（以 | 分隔）
    """
    if not para or len(para.strip()) == 0:
        return False
    
    para = para.strip()
    
    if para.startswith('|') and para.endswith('|'):
        pipe_count = para.count('|')
        if pipe_count >= 3:
            logger.debug(f"[_is_table_row] 识别为表格行: {para[:50]}...")
            return True
    
    return False


def _convert_text_to_html(text: str) -> str:
    """
    智能转换文本到HTML，识别标题、列表、表格、段落等格式
    """
    logger.info(f"[_convert_text_to_html] 开始转换，文本长度: {len(text)}")
    
    if not text or len(text.strip()) == 0:
        logger.warning("[_convert_text_to_html] 文本为空")
        return ""
    
    paragraphs = _smart_split_paragraphs(text)
    
    if not paragraphs:
        return ""
    
    html_parts = []
    in_list = False
    list_type = None
    in_table = False
    table_rows = []
    
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        
        prev_para = paragraphs[i-1].strip() if i > 0 else None
        next_para = paragraphs[i+1].strip() if i < len(paragraphs)-1 else None
        
        is_table_row = _is_table_row(para)
        
        if is_table_row:
            if not in_table:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                in_table = True
                table_rows = []
            
            table_rows.append(para)
            continue
        
        if in_table:
            html_table = _convert_table_rows_to_html(table_rows)
            html_parts.append(html_table)
            in_table = False
            table_rows = []
        
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
    
    if in_table and table_rows:
        html_table = _convert_table_rows_to_html(table_rows)
        html_parts.append(html_table)
    
    result = '\n'.join(html_parts)
    logger.info(f"[_convert_text_to_html] 转换完成，HTML长度: {len(result)}")
    logger.debug(f"[_convert_text_to_html] HTML内容: {result[:300]}...")
    
    return result


def _convert_table_rows_to_html(table_rows: list) -> str:
    """
    将表格行（以 | 分隔）转换为 HTML 表格
    """
    if not table_rows:
        return ""
    
    logger.info(f"[_convert_table_rows_to_html] 转换 {len(table_rows)} 行表格")
    
    html_parts = ["<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"]
    
    for row_idx, row in enumerate(table_rows):
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        
        if row_idx == 0:
            cell_tag = 'th'
        else:
            cell_tag = 'td'
        
        html_row = f"<tr>"
        for cell in cells:
            html_row += f"<{cell_tag}>{cell}</{cell_tag}>"
        html_row += "</tr>"
        html_parts.append(html_row)
    
    html_parts.append("</table>")
    
    result = '\n'.join(html_parts)
    logger.debug(f"[_convert_table_rows_to_html] 转换结果: {result[:200]}...")
    
    return result


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
    return _smart_clean_text(result)


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
    logger.warning(f"[extract_text_from_doc] 使用自定义解析器（备选方案）: {file_path}")
    
    if not olefile.isOleFile(file_path):
        logger.error("[extract_text_from_doc] 不是有效的 OLE 文件")
        return ""
    
    try:
        ole = olefile.OleFileIO(file_path)
        
        if not ole.exists('WordDocument'):
            logger.error("[extract_text_from_doc] 找不到 WordDocument 流")
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
            
            logger.debug(f"[extract_text_from_doc] fc_min={fc_min}, fc_max={fc_max}")
            
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
                            cleaned_text = _smart_clean_text(text)
                            if cleaned_text and len(cleaned_text.strip()) > 20:
                                if _is_highly_likely_valid_text(cleaned_text):
                                    logger.info(f"[extract_text_from_doc] 使用编码 {encoding} 提取成功，长度: {len(cleaned_text)}")
                                    return cleaned_text
                                elif _is_likely_valid_text(cleaned_text):
                                    extracted_texts.append(cleaned_text)
                        except:
                            continue
        except Exception as e:
            logger.warning(f"[extract_text_from_doc] 尝试提取时出错: {e}")
        
        for encoding in ['utf-16-le', 'utf-16-be', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-8', 'latin-1', 'cp1252']:
            try:
                text = _try_decode_with_encoding(word_data, encoding)
                cleaned_text = _smart_clean_text(text)
                if cleaned_text and len(cleaned_text.strip()) > 20:
                    if _is_highly_likely_valid_text(cleaned_text):
                        logger.info(f"[extract_text_from_doc] 使用编码 {encoding} 提取成功")
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
        logger.error(f"[extract_text_from_doc] 提取文本时出错: {e}")
        import traceback
        traceback.print_exc()
        return ""


def _enhance_html_with_alignment(html_content: str, file_path: str) -> str:
    """
    使用 python-docx 读取对齐信息，并增强 mammoth 生成的 HTML
    """
    try:
        doc = DocxDocument(file_path)
        
        paragraphs_info = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                alignment = para.alignment
                align_style = _get_alignment_style(alignment)
                paragraphs_info.append({
                    'text': text,
                    'align_style': align_style,
                    'alignment': alignment
                })
        
        if not paragraphs_info:
            return html_content
        
        def add_alignment_to_tag(match):
            tag = match.group(1)
            existing_attrs = match.group(2) or ''
            content = match.group(3)
            
            content_clean = re.sub(r'<[^>]+>', '', content).strip()
            
            for para_info in paragraphs_info:
                para_text = para_info['text']
                if para_text and content_clean and (para_text in content_clean or content_clean in para_text):
                    if para_info['align_style']:
                        if 'style=' in existing_attrs:
                            existing_attrs = re.sub(
                                r'style="([^"]*)"',
                                f'style="\\1 {para_info["align_style"]}"',
                                existing_attrs
                            )
                        else:
                            existing_attrs = f' style="{para_info["align_style"]}" {existing_attrs}'
                    break
            
            return f'<{tag}{existing_attrs}>{content}</{tag}>'
        
        html_content = re.sub(
            r'<(h[1-6]|p|li)([^>]*)>(.*?)</\1>',
            add_alignment_to_tag,
            html_content,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        return html_content
        
    except Exception as e:
        logger.warning(f"[_enhance_html_with_alignment] 增强对齐样式失败: {e}")
        return html_content


def parse_docx_with_mammoth(file_path: str) -> tuple[str, str]:
    """
    使用 mammoth 解析 .docx 文件（保留格式：标题、列表、表格、加粗、斜体等）
    并使用 python-docx 补充对齐样式
    """
    logger.info(f"[parse_docx_with_mammoth] 使用 mammoth 解析: {file_path}")
    
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html_content = result.value
            messages = result.messages
            
            logger.info(f"[parse_docx_with_mammoth] 转换成功，原始HTML长度: {len(html_content)}")
            
            if messages:
                logger.warning(f"[parse_docx_with_mammoth] 转换消息: {messages}")
            
            logger.info("[parse_docx_with_mammoth] 正在增强对齐样式...")
            html_content = _enhance_html_with_alignment(html_content, file_path)
            logger.info(f"[parse_docx_with_mammoth] 增强后HTML长度: {len(html_content)}")
            
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            logger.info(f"[parse_docx_with_mammoth] 文本长度: {len(text_content)}")
            logger.debug(f"[parse_docx_with_mammoth] HTML内容: {html_content[:300]}...")
            
            return text_content, html_content
            
    except Exception as e:
        logger.error(f"[parse_docx_with_mammoth] 解析出错: {e}")
        import traceback
        traceback.print_exc()
        raise


def parse_docx(file_path: str) -> tuple[str, str]:
    """
    解析 .docx 文件（Open XML格式）
    优先使用 mammoth（保留格式），备选使用 python-docx
    """
    logger.info(f"[parse_docx] 开始解析 .docx 文件: {file_path}")
    
    if HAS_MAMMOTH:
        try:
            return parse_docx_with_mammoth(file_path)
        except Exception as e:
            logger.warning(f"[parse_docx] mammoth 解析失败，回退到 python-docx: {e}")
    else:
        logger.warning("[parse_docx] mammoth 不可用，使用 python-docx")
    
    logger.info("[parse_docx] 使用 python-docx 解析")
    doc = DocxDocument(file_path)
    
    content_parts = []
    html_parts = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            content_parts.append(text)
            
            style = para.style.name.lower()
            alignment = para.alignment
            align_style = _get_alignment_style(alignment)
            
            logger.debug(f"[parse_docx] 段落样式: {style}, 对齐: {alignment}, 内容: {text[:30]}...")
            
            style_attr = f' style="{align_style}"' if align_style else ''
            
            if 'heading 1' in style:
                html_parts.append(f"<h1{style_attr}>{text}</h1>")
            elif 'heading 2' in style:
                html_parts.append(f"<h2{style_attr}>{text}</h2>")
            elif 'heading 3' in style:
                html_parts.append(f"<h3{style_attr}>{text}</h3>")
            elif 'heading 4' in style:
                html_parts.append(f"<h4{style_attr}>{text}</h4>")
            elif 'heading 5' in style:
                html_parts.append(f"<h5{style_attr}>{text}</h5>")
            elif 'heading 6' in style:
                html_parts.append(f"<h6{style_attr}>{text}</h6>")
            elif 'list' in style or 'bullet' in style:
                html_parts.append(f"<li{style_attr}>{text}</li>")
            else:
                html_parts.append(f"<p{style_attr}>{text}</p>")
    
    for table in doc.tables:
        logger.info(f"[parse_docx] 发现表格")
        html_table = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
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
    
    logger.info(f"[parse_docx] 解析完成，content长度: {len(content)}, html长度: {len(html_content)}")
    
    return content, html_content


def parse_old_doc(file_path: str) -> tuple[str, str]:
    """
    解析旧版 .doc 文件（OLE格式）
    优先使用 pyantiword，如果失败则使用自定义解析逻辑
    """
    logger.info(f"[parse_old_doc] 开始解析 .doc 文件: {file_path}")
    
    text = ""
    
    if HAS_ANTIWORD:
        logger.info("[parse_old_doc] 尝试使用 pyantiword")
        try:
            text = antiword_extract_text(file_path)
            logger.info(f"[parse_old_doc] pyantiword 提取成功，原始长度: {len(text)}")
            logger.debug(f"[parse_old_doc] 原始内容 (repr): {repr(text[:300])}")
            
            if text:
                text = text.strip()
                if len(text) > 10:
                    text = _smart_clean_text(text)
                    logger.info(f"[parse_old_doc] 清理后长度: {len(text)}")
                    
                    if _is_highly_likely_valid_text(text):
                        logger.info("[parse_old_doc] 文本有效，转换为HTML")
                        html_content = _convert_text_to_html(text)
                        return text, html_content
                    elif _is_likely_valid_text(text):
                        logger.info("[parse_old_doc] 文本可能有效，继续尝试其他方法")
                        pass
        except Exception as e:
            logger.error(f"[parse_old_doc] pyantiword 解析出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("[parse_old_doc] pyantiword 不可用")
    
    logger.warning("[parse_old_doc] 回退到自定义解析器")
    text = extract_text_from_doc(file_path)
    
    if not text or len(text.strip()) < 10:
        logger.warning("[parse_old_doc] 自定义解析器提取失败，尝试简单提取")
        with open(file_path, 'rb') as f:
            data = f.read()
            text = extract_simple_text(data)
    
    if not text or not _is_likely_valid_text(text):
        logger.error("[parse_old_doc] 无法提取有效内容")
        return "[旧版Word文档 (.doc) - 无法提取有效内容]", "<p><em>旧版Word文档 (.doc) - 无法提取有效内容</em></p>"
    
    html_content = _convert_text_to_html(text)
    
    logger.info(f"[parse_old_doc] 解析完成，content长度: {len(text)}, html长度: {len(html_content)}")
    
    return text, html_content


def parse_doc(file_path: str) -> tuple[str, str]:
    """
    解析Word文档，自动检测格式并选择合适的解析器
    """
    logger.info("=" * 60)
    logger.info(f"[parse_doc] 开始解析文件: {file_path}")
    logger.info("=" * 60)
    
    file_path = Path(file_path)
    
    try:
        if is_docx_file(str(file_path)):
            logger.info("[parse_doc] 检测为 .docx 格式")
            return parse_docx(str(file_path))
        
        elif is_doc_file(str(file_path)):
            logger.info("[parse_doc] 检测为 .doc 格式")
            text, html = parse_old_doc(str(file_path))
            if text and _is_likely_valid_text(text):
                return text, html
            else:
                logger.warning("[parse_doc] .doc 解析结果无效")
                return f"[旧版Word文档 (.doc) - 无法提取有效内容]", "<p><em>旧版Word文档 (.doc) - 无法提取有效内容</em></p>"
        
        else:
            logger.warning("[parse_doc] 格式不明确，尝试各种解析器")
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
                
                logger.error("[parse_doc] 无法识别文件格式")
                return f"[不支持的Word文档格式]", "<p><em>不支持的Word文档格式</em></p>"
    except Exception as e:
        logger.error(f"[parse_doc] 解析出错: {e}")
        import traceback
        traceback.print_exc()
        return f"[文档解析错误: {str(e)}]", f"<p><em>文档解析错误: {str(e)}</em></p>"
