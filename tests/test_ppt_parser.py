"""Tests for PowerPoint parser."""
import sys
from pathlib import Path

import pytest
from pptx import Presentation

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers.ppt_parser import parse_ppt


class TestPptParserBasics:
    """Tests for basic PowerPoint parsing functionality."""

    def test_parse_ppt_basic(self, temp_pptx_file: Path):
        """Test basic pptx parsing returning text and HTML."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert text_content is not None
        assert html_content is not None
        assert len(text_content) > 0
        assert len(html_content) > 0
        
        assert "Test Presentation" in text_content
        assert "Created for testing purposes" in text_content

    def test_parse_ppt_nonexistent_file(self):
        """Test parsing a non-existent file."""
        with pytest.raises(Exception):
            parse_ppt("/nonexistent/file.pptx")


class TestPptParserSlides:
    """Tests for slide parsing functionality."""

    def test_parse_ppt_slide_count(self, temp_pptx_file: Path):
        """Test that correct number of slides are parsed."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "幻灯片 1" in text_content or "Slide 1" in text_content
        assert "幻灯片 2" in text_content or "Slide 2" in text_content
        assert "幻灯片 3" in text_content or "Slide 3" in text_content

    def test_parse_ppt_title_slide(self, temp_pptx_file: Path):
        """Test that title slide content is correctly parsed."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "Test Presentation" in text_content
        assert "Created for testing purposes" in text_content

    def test_parse_ppt_bullet_slide(self, temp_pptx_file: Path):
        """Test that bullet points are correctly parsed."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "First bullet point" in text_content
        assert "Second bullet point" in text_content
        assert "Third bullet point" in text_content

    def test_parse_ppt_table_slide(self, temp_pptx_file: Path):
        """Test that tables in slides are correctly parsed."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "Name" in text_content
        assert "Age" in text_content
        assert "City" in text_content
        assert "Alice" in text_content
        assert "Bob" in text_content


class TestPptParserHtmlGeneration:
    """Tests for HTML generation from PowerPoint."""

    def test_ppt_html_contains_slide_headers(self, temp_pptx_file: Path):
        """Test that HTML contains slide headers."""
        _, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "<h2" in html_content
        assert "幻灯片 1" in html_content or "Slide 1" in html_content

    def test_ppt_html_contains_paragraphs(self, temp_pptx_file: Path):
        """Test that HTML contains paragraph tags."""
        _, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "<p" in html_content
        assert "</p>" in html_content

    def test_ppt_html_contains_tables(self, temp_pptx_file: Path):
        """Test that HTML contains table tags for table slides."""
        _, html_content = parse_ppt(str(temp_pptx_file))
        
        assert "<table" in html_content
        assert "<tr" in html_content
        assert "<td" in html_content
        assert "</table>" in html_content


class TestPptParserEdgeCases:
    """Tests for edge cases in PowerPoint parsing."""

    def test_parse_empty_pptx(self, temp_dir: Path):
        """Test parsing an empty PowerPoint file."""
        file_path = temp_dir / "empty.pptx"
        
        prs = Presentation()
        prs.save(file_path)
        
        text_content, html_content = parse_ppt(str(file_path))
        
        assert text_content is not None
        assert html_content is not None

    def test_parse_pptx_with_only_title(self, temp_dir: Path):
        """Test parsing a PowerPoint with only a title slide."""
        file_path = temp_dir / "title_only.pptx"
        
        prs = Presentation()
        
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = "Single Slide Presentation"
        subtitle.text = "Only one slide"
        
        prs.save(file_path)
        
        text_content, html_content = parse_ppt(str(file_path))
        
        assert "Single Slide Presentation" in text_content
        assert "Only one slide" in text_content

    def test_parse_pptx_with_multiple_shapes(self, temp_dir: Path):
        """Test parsing a PowerPoint with multiple text shapes."""
        file_path = temp_dir / "multiple_shapes.pptx"
        
        prs = Presentation()
        
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        title.text = "Main Title"
        
        bullet_slide_layout = prs.slide_layouts[1]
        slide2 = prs.slides.add_slide(bullet_slide_layout)
        
        title_shape = slide2.shapes.title
        title_shape.text = "Bullet Slide"
        
        body_shape = slide2.shapes.placeholders[1]
        tf = body_shape.text_frame
        tf.text = "First point"
        
        p = tf.add_paragraph()
        p.text = "Second point"
        p.level = 1
        
        p = tf.add_paragraph()
        p.text = "Third point"
        p.level = 2
        
        prs.save(file_path)
        
        text_content, html_content = parse_ppt(str(file_path))
        
        assert "Main Title" in text_content
        assert "Bullet Slide" in text_content
        assert "First point" in text_content
        assert "Second point" in text_content
        assert "Third point" in text_content


class TestPptParserIntegration:
    """Integration tests for PowerPoint parser."""

    def test_full_parsing_workflow(self, temp_pptx_file: Path):
        """Test the complete parsing workflow."""
        text_content, html_content = parse_ppt(str(temp_pptx_file))
        
        assert len(text_content) > 0
        assert len(html_content) > 0
        
        assert "Test Presentation" in text_content
        assert "Second Slide" in text_content
        assert "Table Slide" in text_content
        
        assert "<h2" in html_content
        assert "<p" in html_content
        assert "<table" in html_content

    def test_parser_consistency(self, temp_pptx_file: Path):
        """Test that parsing is consistent across multiple calls."""
        text1, html1 = parse_ppt(str(temp_pptx_file))
        text2, html2 = parse_ppt(str(temp_pptx_file))
        
        assert text1 == text2
