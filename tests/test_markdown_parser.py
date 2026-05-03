"""Tests for the markdown parser module."""
import pytest
from pathlib import Path
from app.parsers.markdown_parser import (
    parse_markdown,
    parse_markdown_file,
    update_markdown_content,
    append_to_markdown,
    prepend_to_markdown,
    replace_section_in_markdown,
    add_heading_to_markdown,
    get_markdown_outline,
    get_markdown_metadata,
    get_markdown_data_as_json,
)


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
        with pytest.raises(Exception):
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


class TestMarkdownFileParsing:
    """Tests for detailed Markdown file parsing."""

    def test_parse_markdown_file_success(self, temp_dir: Path):
        """Test successful parsing with detailed result."""
        content = """# Main Title

## Introduction

This is the intro paragraph.

## Features

- Feature A
- Feature B

## Conclusion

The end.
"""
        file_path = temp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert result.success is True
        assert result.error_message == ""
        assert result.raw_content == content
        assert len(result.html_content) > 0
        assert result.metadata.title == "Main Title"
        assert len(result.headings) == 4
        assert result.outline is not None

    def test_parse_markdown_file_nonexistent(self, temp_dir: Path):
        """Test parsing a nonexistent file."""
        result = parse_markdown_file(str(temp_dir / "nonexistent.md"))
        
        assert result.success is False
        assert "不存在" in result.error_message or "exist" in result.error_message.lower()

    def test_parse_markdown_file_metadata_extraction(self, temp_dir: Path):
        """Test metadata extraction from markdown."""
        content = """# Document Title

## Section 1

This is a paragraph with [link](https://example.com).

## Section 2

| Name | Value |
|------|-------|
| A | 1 |
| B | 2 |

### Subsection

```python
print("hello")
```

![image](https://example.com/img.png)

## Section 3

Another paragraph.
"""
        file_path = temp_dir / "metadata_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert result.success is True
        assert result.metadata.title == "Document Title"
        assert result.metadata.heading_count == 5
        assert result.metadata.heading_levels.get(2) == 3
        assert result.metadata.heading_levels.get(3) == 1
        assert result.metadata.link_count >= 1
        assert result.metadata.table_count >= 1
        assert result.metadata.code_block_count >= 1
        assert result.metadata.image_count >= 1

    def test_parse_markdown_file_headings_extraction(self, temp_dir: Path):
        """Test heading extraction."""
        content = """# H1 Title

## H2 Section 1

### H3 Subsection

## H2 Section 2

### H3 Another

#### H4 Deep
"""
        file_path = temp_dir / "headings_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert len(result.headings) == 6
        
        levels = [h.level for h in result.headings]
        assert levels == [1, 2, 3, 2, 3, 4]
        
        texts = [h.text for h in result.headings]
        assert "H1 Title" in texts
        assert "H2 Section 1" in texts
        assert "H4 Deep" in texts

    def test_parse_markdown_file_code_blocks_extraction(self, temp_dir: Path):
        """Test code block extraction."""
        content = """# Code Test

```python
def hello():
    pass
```

```javascript
console.log("hello");
```

```
no language
```
"""
        file_path = temp_dir / "code_blocks_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert len(result.code_blocks) == 3
        
        languages = [cb.language for cb in result.code_blocks]
        assert "python" in languages
        assert "javascript" in languages
        assert None in languages or "" in languages

    def test_parse_markdown_file_links_extraction(self, temp_dir: Path):
        """Test link extraction."""
        content = """# Links

[Google](https://google.com)
[Example](https://example.com "Example Title")
[Link with spaces](https://test.com/path%20with%20spaces)
"""
        file_path = temp_dir / "links_extract_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert len(result.links) == 3
        
        urls = [l.url for l in result.links]
        assert "https://google.com" in urls
        assert "https://example.com" in urls

    def test_parse_markdown_file_tables_extraction(self, temp_dir: Path):
        """Test table extraction."""
        content = """# Tables

| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
| 4 | 5 | 6 |

| X | Y |
|---|---|
| a | b |
"""
        file_path = temp_dir / "tables_extract_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert len(result.tables) == 2
        
        assert result.tables[0].headers == ["A", "B", "C"]
        assert len(result.tables[0].rows) == 2
        
        assert result.tables[1].headers == ["X", "Y"]
        assert len(result.tables[1].rows) == 1

    def test_parse_markdown_file_outline_generation(self, temp_dir: Path):
        """Test outline generation."""
        content = """# H1

## H2-1

### H3-1

## H2-2

### H3-2

#### H4
"""
        file_path = temp_dir / "outline_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        result = parse_markdown_file(str(file_path))
        
        assert len(result.outline) == 6
        
        outline_texts = [o["text"] for o in result.outline]
        assert "H1" in outline_texts
        assert "H2-1" in outline_texts
        assert "H3-1" in outline_texts
        assert "H2-2" in outline_texts
        assert "H3-2" in outline_texts
        assert "H4" in outline_texts


class TestMarkdownEditing:
    """Tests for Markdown editing functions."""

    def test_update_markdown_content(self, temp_dir: Path):
        """Test updating entire markdown content."""
        file_path = temp_dir / "update_test.md"
        original_content = "# Original\n\nOriginal content."
        file_path.write_text(original_content, encoding="utf-8")
        
        new_content = "# Updated\n\nNew content here."
        success = update_markdown_content(str(file_path), new_content)
        
        assert success is True
        assert file_path.read_text(encoding="utf-8") == new_content

    def test_update_markdown_content_nonexistent(self, temp_dir: Path):
        """Test updating a nonexistent file."""
        success = update_markdown_content(str(temp_dir / "nonexistent.md"), "content")
        assert success is False

    def test_append_to_markdown(self, temp_dir: Path):
        """Test appending content to markdown."""
        file_path = temp_dir / "append_test.md"
        original_content = "# Original\n\nFirst paragraph."
        file_path.write_text(original_content, encoding="utf-8")
        
        append_content = "\n## New Section\n\nAppended content."
        success = append_to_markdown(str(file_path), append_content)
        
        assert success is True
        
        final_content = file_path.read_text(encoding="utf-8")
        assert "Original" in final_content
        assert "First paragraph" in final_content
        assert "New Section" in final_content
        assert "Appended content" in final_content

    def test_append_to_markdown_nonexistent(self, temp_dir: Path):
        """Test appending to a nonexistent file."""
        success = append_to_markdown(str(temp_dir / "nonexistent.md"), "content")
        assert success is False

    def test_prepend_to_markdown(self, temp_dir: Path):
        """Test prepending content to markdown."""
        file_path = temp_dir / "prepend_test.md"
        original_content = "# Original\n\nOriginal content."
        file_path.write_text(original_content, encoding="utf-8")
        
        prepend_content = "# New Header\n\nPrepended content."
        success = prepend_to_markdown(str(file_path), prepend_content)
        
        assert success is True
        
        final_content = file_path.read_text(encoding="utf-8")
        assert "New Header" in final_content
        assert "Prepended content" in final_content
        assert "Original" in final_content

    def test_replace_section_in_markdown(self, temp_dir: Path):
        """Test replacing a section in markdown."""
        content = """# Main Title

## Section 1

Original content for section 1.

## Section 2

Original content for section 2.

## Section 3

Original content for section 3.
"""
        file_path = temp_dir / "replace_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        new_section_content = "\n\nUpdated content for section 2.\n\nThis is new text.\n"
        success = replace_section_in_markdown(
            str(file_path),
            "Section 2",
            new_section_content
        )
        
        assert success is True
        
        final_content = file_path.read_text(encoding="utf-8")
        assert "Section 1" in final_content
        assert "Section 2" in final_content
        assert "Section 3" in final_content
        assert "Updated content for section 2" in final_content
        assert "Original content for section 2" not in final_content

    def test_replace_section_in_markdown_not_found(self, temp_dir: Path):
        """Test replacing a section that doesn't exist."""
        content = "# Title\n\nContent."
        file_path = temp_dir / "replace_notfound_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        success = replace_section_in_markdown(
            str(file_path),
            "Nonexistent Section",
            "New content"
        )
        
        assert success is False

    def test_add_heading_to_markdown(self, temp_dir: Path):
        """Test adding a new heading with content."""
        content = "# Original\n\nOriginal content."
        file_path = temp_dir / "add_heading_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        success = add_heading_to_markdown(
            str(file_path),
            "New Section",
            level=2,
            content="This is the content for the new section."
        )
        
        assert success is True
        
        final_content = file_path.read_text(encoding="utf-8")
        assert "## New Section" in final_content
        assert "This is the content for the new section" in final_content


class TestMarkdownHelperFunctions:
    """Tests for helper functions."""

    def test_get_markdown_outline(self, temp_dir: Path):
        """Test getting markdown outline."""
        content = """# H1

## H2-1

### H3-1

## H2-2
"""
        file_path = temp_dir / "outline_helper_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        outline = get_markdown_outline(str(file_path))
        
        assert len(outline) == 4
        assert outline[0]["text"] == "H1"
        assert outline[0]["level"] == 1
        assert outline[1]["text"] == "H2-1"
        assert outline[2]["text"] == "H3-1"
        assert outline[3]["text"] == "H2-2"

    def test_get_markdown_outline_nonexistent(self, temp_dir: Path):
        """Test getting outline for nonexistent file."""
        outline = get_markdown_outline(str(temp_dir / "nonexistent.md"))
        assert outline == []

    def test_get_markdown_metadata(self, temp_dir: Path):
        """Test getting markdown metadata."""
        content = """# Test Document

## Section 1

[link](https://example.com)

| A | B |
|---|---|
| 1 | 2 |

```python
print("hi")
```

![img](https://example.com/img.png)
"""
        file_path = temp_dir / "metadata_helper_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        metadata = get_markdown_metadata(str(file_path))
        
        assert metadata["success"] is True
        assert metadata["title"] == "Test Document"
        assert metadata["heading_count"] == 2
        assert metadata["link_count"] >= 1
        assert metadata["table_count"] >= 1
        assert metadata["code_block_count"] >= 1
        assert metadata["image_count"] >= 1

    def test_get_markdown_metadata_nonexistent(self, temp_dir: Path):
        """Test getting metadata for nonexistent file."""
        metadata = get_markdown_metadata(str(temp_dir / "nonexistent.md"))
        assert metadata["success"] is False
        assert "error" in metadata

    def test_get_markdown_data_as_json(self, temp_dir: Path):
        """Test getting full markdown data as JSON."""
        content = """# JSON Test

## Section 1

Content here.

### Subsection

| Name | Age |
|------|-----|
| Alice | 30 |

```python
def test():
    pass
```

[Link](https://test.com)
"""
        file_path = temp_dir / "json_data_test.md"
        file_path.write_text(content, encoding="utf-8")
        
        data = get_markdown_data_as_json(str(file_path))
        
        assert data["success"] is True
        assert data["raw_content"] == content
        assert len(data["html_content"]) > 0
        assert data["metadata"]["title"] == "JSON Test"
        assert len(data["outline"]) > 0
        assert len(data["headings"]) == 3
        assert len(data["code_blocks"]) == 1
        assert len(data["links"]) == 1
        assert len(data["tables"]) == 1

    def test_get_markdown_data_as_json_nonexistent(self, temp_dir: Path):
        """Test getting JSON data for nonexistent file."""
        data = get_markdown_data_as_json(str(temp_dir / "nonexistent.md"))
        assert data["success"] is False
        assert "error" in data
