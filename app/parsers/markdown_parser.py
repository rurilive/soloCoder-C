import markdown
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


@dataclass
class HeadingInfo:
    level: int
    text: str
    line_number: int
    content_below: str = ""


@dataclass
class CodeBlockInfo:
    language: Optional[str]
    content: str
    start_line: int
    end_line: int


@dataclass
class LinkInfo:
    text: str
    url: str
    title: Optional[str]
    line_number: int


@dataclass
class TableInfo:
    headers: List[str]
    rows: List[List[str]]
    start_line: int


@dataclass
class MarkdownMetadata:
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    word_count: int = 0
    paragraph_count: int = 0
    heading_count: int = 0
    heading_levels: Dict[int, int] = field(default_factory=dict)
    code_block_count: int = 0
    table_count: int = 0
    link_count: int = 0
    image_count: int = 0


@dataclass
class ParseResult:
    success: bool
    error_message: str = ""
    raw_content: str = ""
    html_content: str = ""
    metadata: MarkdownMetadata = field(default_factory=MarkdownMetadata)
    headings: List[HeadingInfo] = field(default_factory=list)
    code_blocks: List[CodeBlockInfo] = field(default_factory=list)
    links: List[LinkInfo] = field(default_factory=list)
    tables: List[TableInfo] = field(default_factory=list)
    outline: List[Dict[str, Any]] = field(default_factory=list)


def parse_markdown(file_path: str) -> tuple[str, str]:
    """
    解析Markdown文件，返回原始内容和HTML内容
    （兼容旧接口）
    """
    result = parse_markdown_file(file_path)
    if result.success:
        return result.raw_content, result.html_content
    else:
        raise Exception(f"解析失败: {result.error_message}")


def parse_markdown_file(file_path: str) -> ParseResult:
    """
    解析Markdown文件，返回详细的解析结果
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return ParseResult(
            success=False,
            error_message=f"文件不存在: {file_path}"
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
    except Exception as e:
        return ParseResult(
            success=False,
            error_message=f"读取文件失败: {str(e)}"
        )
    
    try:
        html_content = markdown.markdown(
            raw_content,
            extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.sane_lists',
            ]
        )
    except Exception as e:
        return ParseResult(
            success=False,
            error_message=f"转换HTML失败: {str(e)}"
        )
    
    metadata = extract_metadata(raw_content)
    headings = extract_headings(raw_content)
    code_blocks = extract_code_blocks(raw_content)
    links = extract_links(raw_content)
    tables = extract_tables(raw_content)
    outline = generate_outline(headings)
    
    return ParseResult(
        success=True,
        raw_content=raw_content,
        html_content=html_content,
        metadata=metadata,
        headings=headings,
        code_blocks=code_blocks,
        links=links,
        tables=tables,
        outline=outline,
    )


def extract_metadata(content: str) -> MarkdownMetadata:
    """
    从Markdown内容中提取元数据
    """
    metadata = MarkdownMetadata()
    
    lines = content.split('\n')
    word_count = 0
    paragraph_count = 0
    in_code_block = False
    current_paragraph = []
    
    heading_levels = defaultdict(int)
    heading_count = 0
    code_block_count = 0
    table_count = 0
    link_count = 0
    image_count = 0
    
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if not in_code_block:
                code_block_count += 1
            continue
        
        if in_code_block:
            continue
        
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_levels[level] += 1
            heading_count += 1
            if metadata.title is None and level == 1:
                metadata.title = heading_match.group(2).strip()
        
        if stripped.startswith('|') and stripped.endswith('|'):
            if line_num > 1 and lines[line_num - 2].strip().startswith('|'):
                if line_num == 2 or not re.match(r'^[\|\-\s:]+$', lines[line_num - 2].strip()):
                    pass
                else:
                    table_count += 1
        
        links_in_line = re.findall(r'\[([^\]]+)\]\(([^)]+)(?:\s+"([^"]+)")?\)', stripped)
        link_count += len(links_in_line)
        
        images_in_line = re.findall(r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]+)")?\)', stripped)
        image_count += len(images_in_line)
        
        if stripped:
            current_paragraph.append(stripped)
            words = re.findall(r'\b\w+\b', stripped)
            word_count += len(words)
        elif current_paragraph:
            paragraph_count += 1
            current_paragraph = []
    
    if current_paragraph:
        paragraph_count += 1
    
    metadata.word_count = word_count
    metadata.paragraph_count = paragraph_count
    metadata.heading_count = heading_count
    metadata.heading_levels = dict(heading_levels)
    metadata.code_block_count = code_block_count
    metadata.table_count = table_count
    metadata.link_count = link_count
    metadata.image_count = image_count
    
    return metadata


def extract_headings(content: str) -> List[HeadingInfo]:
    """
    提取Markdown中的所有标题
    """
    headings = []
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            
            content_below = []
            for next_line in lines[line_num:]:
                next_stripped = next_line.strip()
                if re.match(r'^#{1,6}\s+', next_stripped):
                    break
                if next_stripped:
                    content_below.append(next_stripped)
            
            headings.append(HeadingInfo(
                level=level,
                text=text,
                line_number=line_num,
                content_below='\n'.join(content_below)
            ))
        
        if line_num < len(lines):
            next_line = lines[line_num].strip() if line_num < len(lines) else ''
            if re.match(r'^=+$', next_stripped if 'next_stripped' in dir() else '') and stripped:
                headings.append(HeadingInfo(
                    level=1,
                    text=stripped,
                    line_number=line_num
                ))
            elif re.match(r'^-+$', next_stripped if 'next_stripped' in dir() else '') and stripped:
                headings.append(HeadingInfo(
                    level=2,
                    text=stripped,
                    line_number=line_num
                ))
    
    return headings


def extract_code_blocks(content: str) -> List[CodeBlockInfo]:
    """
    提取Markdown中的所有代码块
    """
    code_blocks = []
    lines = content.split('\n')
    
    in_code_block = False
    code_start = 0
    code_language = None
    code_lines = []
    
    for line_num, line in enumerate(lines, 1):
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_start = line_num
                lang_match = re.match(r'^```(\w+)?', line.strip())
                code_language = lang_match.group(1) if lang_match else None
                code_lines = []
            else:
                in_code_block = False
                code_blocks.append(CodeBlockInfo(
                    language=code_language,
                    content='\n'.join(code_lines),
                    start_line=code_start,
                    end_line=line_num
                ))
        elif in_code_block:
            code_lines.append(line)
    
    return code_blocks


def extract_links(content: str) -> List[LinkInfo]:
    """
    提取Markdown中的所有链接
    """
    links = []
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        matches_with_title = re.findall(r'\[([^\]]+)\]\(([^)\s"]+)\s+"([^"]+)"\)', line)
        for text, url, title in matches_with_title:
            if not line.strip().startswith('!'):
                links.append(LinkInfo(
                    text=text,
                    url=url,
                    title=title,
                    line_number=line_num
                ))
        
        matches_without_title = re.findall(r'\[([^\]]+)\]\(([^)"\s]+)\)(?![^[]*\])', line)
        for text, url in matches_without_title:
            if not line.strip().startswith('!'):
                already_added = any(l.url == url and l.text == text for l in links)
                if not already_added:
                    links.append(LinkInfo(
                        text=text,
                        url=url,
                        title=None,
                        line_number=line_num
                    ))
    
    return links


def extract_tables(content: str) -> List[TableInfo]:
    """
    提取Markdown中的所有表格
    """
    tables = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('|') and line.endswith('|'):
            table_start = i
            headers = []
            rows = []
            
            header_cells = re.split(r'\s*\|\s*', line)
            header_cells = [cell.strip() for cell in header_cells if cell.strip()]
            headers = header_cells
            
            i += 1
            if i < len(lines):
                separator_line = lines[i].strip()
                if re.match(r'^[\|\-\s:]+$', separator_line):
                    i += 1
                    
                    while i < len(lines):
                        row_line = lines[i].strip()
                        if row_line.startswith('|') and row_line.endswith('|'):
                            row_cells = re.split(r'\s*\|\s*', row_line)
                            row_cells = [cell.strip() for cell in row_cells if cell.strip()]
                            rows.append(row_cells)
                            i += 1
                        else:
                            break
                    
                    if headers or rows:
                        tables.append(TableInfo(
                            headers=headers,
                            rows=rows,
                            start_line=table_start + 1
                        ))
                else:
                    i = table_start + 1
            else:
                i += 1
        else:
            i += 1
    
    return tables


def generate_outline(headings: List[HeadingInfo]) -> List[Dict[str, Any]]:
    """
    根据标题生成文档大纲
    """
    if not headings:
        return []
    
    root = {'children': [], 'level': 0}
    stack = [root]
    
    for heading in headings:
        while stack[-1]['level'] >= heading.level:
            stack.pop()
        
        node = {
            'text': heading.text,
            'level': heading.level,
            'line_number': heading.line_number,
            'children': []
        }
        
        stack[-1]['children'].append(node)
        stack.append(node)
    
    def flatten_outline(nodes: List[Dict], level: int = 0) -> List[Dict]:
        result = []
        for node in nodes:
            result.append({
                'text': node['text'],
                'level': node['level'],
                'line_number': node['line_number'],
                'depth': level
            })
            result.extend(flatten_outline(node.get('children', []), level + 1))
        return result
    
    return flatten_outline(root['children'])


def update_markdown_content(file_path: str, new_content: str) -> bool:
    """
    更新Markdown文件的内容
    
    Args:
        file_path: Markdown文件路径
        new_content: 新的Markdown内容
    
    Returns:
        是否成功
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"更新Markdown文件失败: {e}")
        return False


def append_to_markdown(file_path: str, content: str) -> bool:
    """
    向Markdown文件追加内容
    
    Args:
        file_path: Markdown文件路径
        content: 要追加的内容
    
    Returns:
        是否成功
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        if existing_content and not existing_content.endswith('\n'):
            existing_content += '\n\n'
        elif existing_content and not existing_content.endswith('\n\n'):
            existing_content += '\n'
        
        new_content = existing_content + content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"追加内容到Markdown文件失败: {e}")
        return False


def prepend_to_markdown(file_path: str, content: str) -> bool:
    """
    向Markdown文件开头插入内容
    
    Args:
        file_path: Markdown文件路径
        content: 要插入的内容
    
    Returns:
        是否成功
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        if not content.endswith('\n'):
            content += '\n\n'
        elif not content.endswith('\n\n'):
            content += '\n'
        
        new_content = content + existing_content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"向Markdown文件开头插入内容失败: {e}")
        return False


def replace_section_in_markdown(
    file_path: str, 
    heading_text: str, 
    new_content: str,
    heading_level: Optional[int] = None
) -> bool:
    """
    替换Markdown文件中指定标题下的内容
    
    Args:
        file_path: Markdown文件路径
        heading_text: 标题文本
        new_content: 新的内容
        heading_level: 可选，指定标题级别（1-6）
    
    Returns:
        是否成功
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        result_lines = []
        found = False
        skip_mode = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                
                if skip_mode:
                    current_heading_level = level
                    if heading_level is None:
                        if current_heading_level <= found_heading_level:
                            skip_mode = False
                            result_lines.append(new_content)
                    else:
                        if current_heading_level <= heading_level:
                            skip_mode = False
                            result_lines.append(new_content)
                
                if not found and text == heading_text:
                    if heading_level is None or level == heading_level:
                        found = True
                        found_heading_level = level
                        skip_mode = True
                        result_lines.append(line)
                        continue
            
            if skip_mode:
                continue
            
            result_lines.append(line)
        
        if skip_mode:
            result_lines.append(new_content)
        
        if not found:
            return False
        
        new_content_str = '\n'.join(result_lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content_str)
        
        return True
    except Exception as e:
        print(f"替换Markdown章节失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_heading_to_markdown(
    file_path: str, 
    heading_text: str, 
    level: int = 2,
    content: str = ""
) -> bool:
    """
    向Markdown文件添加新的标题和可选内容
    
    Args:
        file_path: Markdown文件路径
        heading_text: 标题文本
        level: 标题级别（1-6，默认2）
        content: 标题下的可选内容
    
    Returns:
        是否成功
    """
    level = max(1, min(6, level))
    heading = '#' * level + ' ' + heading_text
    
    full_content = heading
    if content:
        full_content += '\n\n' + content
    
    return append_to_markdown(file_path, full_content)


def get_markdown_outline(file_path: str) -> List[Dict[str, Any]]:
    """
    获取Markdown文件的大纲结构
    
    Args:
        file_path: Markdown文件路径
    
    Returns:
        大纲列表
    """
    result = parse_markdown_file(file_path)
    if result.success:
        return result.outline
    return []


def get_markdown_metadata(file_path: str) -> Dict[str, Any]:
    """
    快速获取Markdown文件的元数据
    
    Args:
        file_path: Markdown文件路径
    
    Returns:
        包含元数据的字典
    """
    result = parse_markdown_file(file_path)
    if result.success:
        return {
            'success': True,
            'title': result.metadata.title,
            'word_count': result.metadata.word_count,
            'paragraph_count': result.metadata.paragraph_count,
            'heading_count': result.metadata.heading_count,
            'heading_levels': result.metadata.heading_levels,
            'code_block_count': result.metadata.code_block_count,
            'table_count': result.metadata.table_count,
            'link_count': result.metadata.link_count,
            'image_count': result.metadata.image_count,
        }
    return {'success': False, 'error': result.error_message}


def get_markdown_data_as_json(file_path: str) -> Dict[str, Any]:
    """
    获取Markdown文件的完整数据（JSON格式）
    
    Args:
        file_path: Markdown文件路径
    
    Returns:
        包含完整数据的字典
    """
    result = parse_markdown_file(file_path)
    
    if not result.success:
        return {'success': False, 'error': result.error_message}
    
    return {
        'success': True,
        'raw_content': result.raw_content,
        'html_content': result.html_content,
        'metadata': {
            'title': result.metadata.title,
            'word_count': result.metadata.word_count,
            'paragraph_count': result.metadata.paragraph_count,
            'heading_count': result.metadata.heading_count,
            'heading_levels': result.metadata.heading_levels,
            'code_block_count': result.metadata.code_block_count,
            'table_count': result.metadata.table_count,
            'link_count': result.metadata.link_count,
            'image_count': result.metadata.image_count,
        },
        'outline': result.outline,
        'headings': [
            {
                'text': h.text,
                'level': h.level,
                'line_number': h.line_number,
            }
            for h in result.headings
        ],
        'code_blocks': [
            {
                'language': cb.language,
                'start_line': cb.start_line,
                'end_line': cb.end_line,
                'line_count': cb.end_line - cb.start_line - 1,
            }
            for cb in result.code_blocks
        ],
        'links': [
            {
                'text': l.text,
                'url': l.url,
                'title': l.title,
                'line_number': l.line_number,
            }
            for l in result.links
        ],
        'tables': [
            {
                'headers': t.headers,
                'row_count': len(t.rows),
                'start_line': t.start_line,
            }
            for t in result.tables
        ],
    }
