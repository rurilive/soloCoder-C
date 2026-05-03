"""Tests for the markdown parser module."""
import pytest
from pathlib import Path
from app.parsers.markdown_parser import parse_markdown


class TestMarkdownParserBasics:
    """Tests for basic Markdown parsing."""

    def test_parse_markdown_basic(self, temp_dir: Path):
        """Test basic markdown parsing returning text and HTML."""
        markdown_content = """# Test Document

This is a test paragraph.

## Second Section

Some more content here.

### Third Level Heading

- List item 1
- List item 2
- List item 3

1. Ordered item 1
2. Ordered item 2

| Name | Age | City |
|------|-----|------|
| Alice | 30 | New York |
| Bob | 25 | London |

```python
def hello():
    print("Hello, World!")
```

**Bold text** and *italic text*.
"""
        file_path = temp_dir / "test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert text_content is not None
        assert html_content is not None
        assert len(text_content) > 0
        assert len(html_content) > 0
        
        assert "Test Document" in text_content
        assert "test paragraph" in text_content
        
        assert "<h1" in html_content or "<h2" in html_content
        assert "<p" in html_content
        assert "<li" in html_content or "<ul" in html_content or "<ol" in html_content
        assert "<table" in html_content or "<code" in html_content

    def test_parse_markdown_empty_file(self, temp_dir: Path):
        """Test parsing an empty markdown file."""
        file_path = temp_dir / "empty.md"
        file_path.write_text("", encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert text_content == ""
        assert html_content == ""

    def test_parse_markdown_with_code_block(self, temp_dir: Path):
        """Test markdown parsing with code blocks."""
        markdown_content = """# Code Example

Here is some Python code:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

And some JavaScript:

```javascript
const hello = () => console.log("Hello");
```
"""
        file_path = temp_dir / "code_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Code Example" in text_content
        assert "factorial" in text_content
        
        assert "<code" in html_content or "<pre" in html_content

    def test_parse_markdown_with_tables(self, temp_dir: Path):
        """Test markdown parsing with tables."""
        markdown_content = """# Table Test

| Product | Price | Stock |
|---------|-------|-------|
| Laptop | $999 | 50 |
| Phone | $699 | 100 |
| Tablet | $299 | 75 |

This is a table of products.
"""
        file_path = temp_dir / "table_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Table Test" in text_content
        assert "Laptop" in text_content
        assert "$999" in text_content

    def test_parse_markdown_with_links_and_images(self, temp_dir: Path):
        """Test markdown parsing with links and images."""
        markdown_content = """# Links and Images

Visit [Google](https://www.google.com) for more information.

Here is an image:

![Alt text](https://example.com/image.png)

And a [link with title](https://example.com "Example Title").
"""
        file_path = temp_dir / "links_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Links and Images" in text_content
        assert "Google" in text_content
        
        assert '<a href="' in html_content or "<a " in html_content

    def test_parse_markdown_nonexistent_file(self):
        """Test parsing a nonexistent markdown file."""
        with pytest.raises(FileNotFoundError):
            parse_markdown("/nonexistent/file.md")

    def test_parse_markdown_with_emphasis(self, temp_dir: Path):
        """Test markdown parsing with bold and italic text."""
        markdown_content = """# Emphasis Test

This is **bold text** and this is *italic text*.

This is ***bold and italic*** text.

This is _also italic_ and __also bold__.
"""
        file_path = temp_dir / "emphasis_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Emphasis Test" in text_content
        assert "bold text" in text_content
        assert "italic text" in text_content

    def test_parse_markdown_with_blockquotes(self, temp_dir: Path):
        """Test markdown parsing with blockquotes."""
        markdown_content = """# Blockquote Test

Here is a quote:

> This is a blockquote.
> It can span multiple lines.

> This is another quote.
>> This is a nested quote.

Normal text after quotes.
"""
        file_path = temp_dir / "blockquote_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Blockquote Test" in text_content
        assert "blockquote" in text_content.lower()

    def test_parse_markdown_with_horizontal_rule(self, temp_dir: Path):
        """Test markdown parsing with horizontal rules."""
        markdown_content = """# Horizontal Rule Test

Section 1

---

Section 2

***

Section 3

___

End of document.
"""
        file_path = temp_dir / "hr_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Horizontal Rule Test" in text_content
        assert "Section 1" in text_content
        assert "Section 2" in text_content
        assert "Section 3" in text_content

    def test_parse_markdown_with_definition_lists(self, temp_dir: Path):
        """Test markdown parsing with definition lists (if supported by extensions)."""
        markdown_content = """# Definition List Test

Term 1
: Definition 1

Term 2
: Definition 2a
: Definition 2b
"""
        file_path = temp_dir / "definition_test.md"
        file_path.write_text(markdown_content, encoding="utf-8")
        
        text_content, html_content = parse_markdown(str(file_path))
        
        assert "Definition List Test" in text_content
        assert "Term 1" in text_content
        assert "Term 2" in text_content
