import os
from typing import List, Tuple, Optional
from pathlib import Path


ALLOWED_TEXT_EXTENSIONS = {
    '.txt', '.text', '.log', '.csv', '.tsv',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.json',
    '.java', '.kt', '.scala', '.groovy',
    '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
    '.cs', '.vb', '.fs',
    '.go', '.rs', '.swift',
    '.rb', '.php', '.perl', '.pl', '.pm',
    '.sh', '.bash', '.zsh', '.fish',
    '.sql', '.sqlite', '.mysql', '.pgsql',
    '.html', '.htm', '.css', '.scss', '.sass', '.less',
    '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.md', '.markdown', '.rst',
    '.bat', '.cmd', '.ps1',
    '.lua', '.r', '.dart', '.kotlin',
    '.tf', '.hcl', '.dockerfile',
    '.env', '.env.example', '.gitignore',
    '.makefile', '.gnumakefile',
    '.nginx', '.apache',
    '.proto', '.thrift',
    '.graphql', '.gql',
    '.vue', '.svelte',
    '.coffee', '.litcoffee',
    '.jade', '.pug',
    '.haml', '.slim',
    '.ejs', '.handlebars', '.hbs',
    '.mustache', '.jinja', '.jinja2',
    '.twig', '.blade',
    '.asp', '.aspx',
    '.jsp', '.jspx',
    '.clj', '.cljs', '.cljc',
    '.ex', '.exs',
    '.erl', '.hrl',
    '.hs', '.lhs',
    '.ml', '.mli',
    '.fsx', '.fsi',
    '.vbhtml',
    '.tex', '.ltx',
    '.bib',
    '.man',
}


BINARY_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.bin',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico',
    '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv', '.flv',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp',
    '.class', '.jar', '.war', '.ear',
    '.iso', '.img', '.dmg',
    '.deb', '.rpm', '.msi',
}


def is_text_file_by_extension(filename: str) -> Tuple[bool, str]:
    """
    检查文件扩展名是否为允许的文本文件类型
    
    Returns:
        (is_allowed, message)
    """
    if not filename:
        return False, "Filename is empty"
    
    file_ext = Path(filename).suffix.lower()
    
    if not file_ext:
        return True, "File has no extension, will check content"
    
    if file_ext in BINARY_EXTENSIONS:
        return False, f"Binary files with extension {file_ext} are not allowed"
    
    if file_ext in ALLOWED_TEXT_EXTENSIONS:
        return True, f"Allowed text file extension: {file_ext}"
    
    return True, f"Unknown extension {file_ext}, will check content"


def is_binary_content(content: bytes) -> Tuple[bool, str]:
    """
    检查文件内容是否为二进制文件
    
    判断标准:
    1. 包含空字节 (null byte) - 通常表示二进制文件
    2. 包含大量不可打印字符 (超过 30%)
    """
    if not content:
        return False, "Empty file"
    
    if b'\x00' in content:
        return True, "File contains null bytes, likely binary"
    
    sample_size = min(8192, len(content))
    sample = content[:sample_size]
    
    printable_chars = 0
    control_chars = 0
    
    for byte in sample:
        if 32 <= byte <= 126 or byte in (9, 10, 13):
            printable_chars += 1
        else:
            control_chars += 1
    
    if sample_size > 0:
        control_ratio = control_chars / sample_size
        if control_ratio > 0.3:
            return True, f"File contains {control_ratio*100:.1f}% control characters, likely binary"
    
    return False, "Content appears to be text"


def validate_uploaded_file(filename: str, content: bytes) -> Tuple[bool, str]:
    """
    综合验证上传的文件是否为文本文件
    
    Returns:
        (is_valid, error_message)
    """
    ext_ok, ext_msg = is_text_file_by_extension(filename)
    
    if not ext_ok:
        return False, ext_msg
    
    binary_check, binary_msg = is_binary_content(content)
    
    if binary_check:
        return False, f"File '{filename}' appears to be a binary file: {binary_msg}"
    
    return True, "Valid text file"


def get_supported_extensions() -> List[str]:
    """
    返回所有支持的文本文件扩展名列表
    """
    return sorted(list(ALLOWED_TEXT_EXTENSIONS))
