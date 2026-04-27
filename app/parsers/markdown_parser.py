import markdown
from pathlib import Path


def parse_markdown(file_path: str) -> tuple[str, str]:
    """
    解析Markdown文件，返回原始内容和HTML内容
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    html_content = markdown.markdown(
        content,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.sane_lists',
        ]
    )
    
    return content, html_content
