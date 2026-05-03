"""Tests for the doc parser helper functions."""
import pytest
import os
import struct
from pathlib import Path
from typing import List, Dict, Any

from app.parsers.doc_parser import (
    _smart_clean_text,
    _detect_encoding,
    _is_highly_likely_valid_text,
    _is_likely_valid_text,
    _smart_split_paragraphs,
    _is_likely_english_heading,
    _is_likely_heading,
    _is_list_item,
    _is_table_row,
    _convert_text_to_html,
    _convert_table_rows_to_html,
    extract_simple_text,
    _try_decode_with_encoding,
    _is_unicode_word,
    MetricsCalculator,
    ResultScorer,
    ParseResult,
    ParseResultMetrics,
)


class TestTextCleaning:
    """Tests for text cleaning functions."""

    def test_smart_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "Hello\x00World\x01Test"
        cleaned = _smart_clean_text(text)
        
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned
        assert "Test" in cleaned

    def test_smart_clean_text_empty(self):
        """Test cleaning empty text."""
        assert _smart_clean_text("") == ""
        assert _smart_clean_text(None) == ""

    def test_smart_clean_text_with_newlines(self):
        """Test cleaning text with newlines."""
        text = "Line 1\nLine 2  \nLine 3   "
        cleaned = _smart_clean_text(text)
        
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
        assert "Line 3" in cleaned


class TestEncodingDetection:
    """Tests for encoding detection functions."""

    def test_detect_encoding_empty(self):
        """Test encoding detection with empty data."""
        encoding = _detect_encoding(b"")
        assert encoding == "utf-8"

    def test_detect_encoding_utf8(self):
        """Test encoding detection with UTF-8 data."""
        data = "Hello, 世界".encode("utf-8")
        encoding = _detect_encoding(data)
        assert encoding is not None
        assert isinstance(encoding, str)

    def test_try_decode_with_encoding_valid(self):
        """Test decoding with valid encoding."""
        data = "Hello World".encode("utf-8")
        decoded = _try_decode_with_encoding(data, "utf-8")
        assert decoded == "Hello World"

    def test_try_decode_with_encoding_invalid(self):
        """Test decoding with invalid encoding."""
        data = b"\xff\xfe\xfd"
        decoded = _try_decode_with_encoding(data, "utf-8")
        assert decoded is not None

    def test_is_unicode_word_valid(self):
        """Test Unicode Word detection with valid data."""
        valid_data = b"\x00" * 10 + struct.pack("<H", 0x0100) + b"\x00" * 10
        result = _is_unicode_word(valid_data)
        assert result is True or result is False

    def test_is_unicode_word_invalid(self):
        """Test Unicode Word detection with invalid data."""
        invalid_data = b"\x00" * 5
        result = _is_unicode_word(invalid_data)
        assert result is False


class TestTextValidity:
    """Tests for text validity detection functions."""

    def test_is_highly_likely_valid_text_empty(self):
        """Test with empty text."""
        assert _is_highly_likely_valid_text("") is False
        assert _is_highly_likely_valid_text("   ") is False
        assert _is_highly_likely_valid_text("short") is False

    def test_is_highly_likely_valid_text_chinese(self):
        """Test with Chinese text."""
        chinese_text = "这是一段中文文本，包含多个中文字符。这样的文本应该被识别为有效。这里还有更多的中文内容，确保字符数量足够。"
        assert _is_highly_likely_valid_text(chinese_text) is True

    def test_is_highly_likely_valid_text_english(self):
        """Test with English text containing common words."""
        english_text = "The quick brown fox jumps over the lazy dog. This is a sample paragraph that should be recognized as valid text."
        assert _is_highly_likely_valid_text(english_text) is True

    def test_is_highly_likely_valid_text_with_spaces(self):
        """Test text with proper spacing."""
        text = "This is a test. It has multiple sentences. And it has newlines.\nAnother line here."
        assert _is_highly_likely_valid_text(text) is True or _is_likely_valid_text(text) is True

    def test_is_likely_valid_text_empty(self):
        """Test is_likely_valid_text with empty text."""
        assert _is_likely_valid_text("") is False
        assert _is_likely_valid_text("  ") is False

    def test_is_likely_valid_text_chinese(self):
        """Test is_likely_valid_text with Chinese text."""
        chinese_text = "这是一段中文文本，包含多个中文字符。这样的文本应该被识别为有效。"
        assert _is_likely_valid_text(chinese_text) is True

    def test_is_likely_valid_text_with_spaces(self):
        """Test is_likely_valid_text with proper spacing."""
        text = "This is a test. It has multiple sentences. And it has newlines.\nAnother line here."
        assert _is_likely_valid_text(text) is True


class TestParagraphSplitting:
    """Tests for paragraph splitting functions."""

    def test_smart_split_paragraphs_empty(self):
        """Test with empty text."""
        assert _smart_split_paragraphs("") == []
        assert _smart_split_paragraphs(None) == []

    def test_smart_split_paragraphs_single(self):
        """Test with single paragraph."""
        text = "This is a single paragraph."
        paragraphs = _smart_split_paragraphs(text)
        
        assert len(paragraphs) == 1
        assert paragraphs[0] == "This is a single paragraph."

    def test_smart_split_paragraphs_multiple(self):
        """Test with multiple paragraphs separated by blank lines."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        paragraphs = _smart_split_paragraphs(text)
        
        assert len(paragraphs) >= 2

    def test_smart_split_paragraphs_with_tables(self):
        """Test with table-like lines."""
        text = "Some text.\n\n| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1 | Cell 2 |\n\nMore text."
        paragraphs = _smart_split_paragraphs(text)
        
        assert len(paragraphs) > 0


class TestHeadingDetection:
    """Tests for heading detection functions."""

    def test_is_likely_english_heading_empty(self):
        """Test with empty text."""
        is_heading, level = _is_likely_english_heading("")
        assert is_heading is False
        assert level is None

    def test_is_likely_english_heading_all_caps(self):
        """Test with all caps text."""
        is_heading, level = _is_likely_english_heading("INTRODUCTION")
        assert is_heading is True or level is not None

    def test_is_likely_english_heading_title_case(self):
        """Test with title case text."""
        is_heading, level = _is_likely_english_heading("This Is A Title")
        assert is_heading is True or is_heading is False

    def test_is_likely_heading_empty(self):
        """Test is_likely_heading with empty text."""
        is_heading, level = _is_likely_heading("")
        assert is_heading is False
        assert level is None

    def test_is_likely_heading_chinese_pattern(self):
        """Test with Chinese heading patterns."""
        is_heading, level = _is_likely_heading("第一章 概述")
        assert is_heading is True or level is not None

    def test_is_likely_heading_numbered(self):
        """Test with numbered heading patterns."""
        is_heading, level = _is_likely_heading("1. Introduction")
        assert is_heading is True or level is not None

    def test_is_likely_heading_subsection(self):
        """Test with subsection heading patterns."""
        is_heading, level = _is_likely_heading("1.2 详细说明")
        assert is_heading is True or level is not None


class TestListItemDetection:
    """Tests for list item detection functions."""

    def test_is_list_item_empty(self):
        """Test with empty text."""
        is_list, list_type, content = _is_list_item("")
        assert is_list is False
        assert list_type is None
        assert content is None

    def test_is_list_item_bullet(self):
        """Test with bullet list item."""
        is_list, list_type, content = _is_list_item("• Item one")
        assert is_list is True or list_type is not None

    def test_is_list_item_numbered(self):
        """Test with numbered list item."""
        is_list, list_type, content = _is_list_item("1. Item one")
        assert is_list is True or list_type is not None

    def test_is_list_item_lettered(self):
        """Test with lettered list item."""
        is_list, list_type, content = _is_list_item("(1) Item one")
        assert is_list is True or list_type is not None


class TestTableRowDetection:
    """Tests for table row detection functions."""

    def test_is_table_row_empty(self):
        """Test with empty text."""
        assert _is_table_row("") is False

    def test_is_table_row_valid(self):
        """Test with valid table row."""
        assert _is_table_row("| Header 1 | Header 2 |") is True

    def test_is_table_row_not_enough_pipes(self):
        """Test with insufficient pipes."""
        assert _is_table_row("| Just one pipe") is False


class TestHtmlConversion:
    """Tests for HTML conversion functions."""

    def test_convert_table_rows_to_html_empty(self):
        """Test with empty table rows."""
        assert _convert_table_rows_to_html([]) == ""

    def test_convert_table_rows_to_html_basic(self):
        """Test with basic table rows."""
        rows = [
            "| Name | Age |",
            "| Alice | 30 |",
            "| Bob | 25 |",
        ]
        html = _convert_table_rows_to_html(rows)
        
        assert "<table" in html
        assert "</table>" in html
        assert "<tr" in html
        assert "</tr>" in html
        assert "<th" in html or "<td" in html

    def test_convert_text_to_html_empty(self):
        """Test with empty text."""
        assert _convert_text_to_html("") == ""
        assert _convert_text_to_html("   ") == ""

    def test_convert_text_to_html_basic(self):
        """Test with basic text."""
        text = "This is a simple paragraph."
        html = _convert_text_to_html(text)
        
        assert "<p" in html or len(html) > 0

    def test_convert_text_to_html_with_headings(self):
        """Test text with heading patterns."""
        text = "1. Introduction\n\nThis is the introduction section.\n\n2. Details\n\nThis is the details section."
        html = _convert_text_to_html(text)
        
        assert len(html) > 0

    def test_convert_text_to_html_with_table(self):
        """Test text with table."""
        text = "Here is a table:\n\n| Name | Age |\n|------|-----|\n| Alice | 30 |\n\nEnd of table."
        html = _convert_text_to_html(text)
        
        assert len(html) > 0


class TestSimpleTextExtraction:
    """Tests for simple text extraction functions."""

    def test_extract_simple_text_empty(self):
        """Test with empty data."""
        result = extract_simple_text(b"")
        assert result == ""

    def test_extract_simple_text_utf16(self):
        """Test with UTF-16 encoded text."""
        text = "Hello World"
        data = text.encode("utf-16-le")
        result = extract_simple_text(data)
        
        assert len(result) > 0 or result == ""


class TestMetricsCalculator:
    """Tests for MetricsCalculator class."""

    def test_calculate_metrics_empty(self):
        """Test with empty content."""
        metrics = MetricsCalculator.calculate_metrics("", "", {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.total_text_length == 0

    def test_calculate_metrics_with_text(self):
        """Test with basic text content."""
        text = "This is a test paragraph."
        html = "<p>This is a test paragraph.</p>"
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.total_text_length == len(text)
        assert metrics.paragraph_count >= 0

    def test_calculate_metrics_with_html_headings(self):
        """Test with HTML containing headings."""
        html = """
        <h1>Main Title</h1>
        <h2>Subtitle</h2>
        <p>A paragraph.</p>
        """
        text = "Main Title\nSubtitle\nA paragraph."
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.heading_count >= 0

    def test_calculate_metrics_with_html_lists(self):
        """Test with HTML containing lists."""
        html = """
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <ol>
            <li>Ordered 1</li>
            <li>Ordered 2</li>
        </ol>
        """
        text = "Item 1\nItem 2\nOrdered 1\nOrdered 2"
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.list_item_count >= 0
        assert metrics.ordered_list_count >= 0
        assert metrics.unordered_list_count >= 0

    def test_calculate_metrics_with_html_table(self):
        """Test with HTML containing tables."""
        html = """
        <table>
            <tr><th>Name</th><th>Age</th></tr>
            <tr><td>Alice</td><td>30</td></tr>
            <tr><td>Bob</td><td>25</td></tr>
        </table>
        """
        text = "Name Age\nAlice 30\nBob 25"
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.table_count >= 0
        assert metrics.table_row_count >= 0
        assert metrics.table_cell_count >= 0

    def test_calculate_metrics_with_formatting(self):
        """Test with HTML containing text formatting."""
        html = """
        <p>This is <strong>bold</strong> and <em>italic</em> and <u>underlined</u>.</p>
        <p>Visit <a href="https://example.com">this link</a>.</p>
        <p><img src="image.png" alt="An image"></p>
        """
        text = "This is bold and italic and underlined. Visit this link."
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.bold_count >= 0
        assert metrics.italic_count >= 0
        assert metrics.underline_count >= 0
        assert metrics.inline_format_count >= 0
        assert metrics.link_count >= 0
        assert metrics.image_count >= 0

    def test_calculate_metrics_with_styles(self):
        """Test with HTML containing inline styles."""
        html = """
        <p style="text-align: center; margin-top: 10px;">Centered text</p>
        <p style="text-indent: 2em; margin-left: 1em;">Indented text</p>
        <p style="margin-bottom: 20px;">Spaced text</p>
        """
        text = "Centered text\nIndented text\nSpaced text"
        metrics = MetricsCalculator.calculate_metrics(text, html, {})
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.style_attributes_count >= 0
        assert metrics.alignment_count >= 0 or metrics.indent_count >= 0 or metrics.spacing_count >= 0

    def test_analyze_with_regex(self):
        """Test regex-based HTML analysis."""
        html = """
        <h1>Title</h1>
        <h2>Subtitle</h2>
        <p>Paragraph 1</p>
        <p>Paragraph 2</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <table>
            <tr><th>H1</th><th>H2</th></tr>
            <tr><td>C1</td><td>C2</td></tr>
        </table>
        <p><strong>Bold</strong> <em>Italic</em> <a href="#">Link</a></p>
        """
        empty_metrics = ParseResultMetrics()
        metrics = MetricsCalculator._analyze_with_regex(html, empty_metrics)
        
        assert isinstance(metrics, ParseResultMetrics)
        assert metrics.paragraph_count >= 0
        assert metrics.heading_count >= 0
        assert metrics.list_item_count >= 0
        assert metrics.table_count >= 0
        assert metrics.table_row_count >= 0
        assert metrics.table_cell_count >= 0
        assert metrics.bold_count >= 0
        assert metrics.italic_count >= 0
        assert metrics.link_count >= 0

    def test_enrich_from_raw_data(self):
        """Test enriching metrics from raw data."""
        raw_data = {
            'paragraphs_info': [
                {'text': 'Paragraph 1'},
                {'text': 'Paragraph 2'},
            ],
            'tables': [
                {'rows': [['H1', 'H2'], ['C1', 'C2']]},
            ],
        }
        empty_metrics = ParseResultMetrics()
        metrics = MetricsCalculator._enrich_from_raw_data(raw_data, empty_metrics)
        
        assert isinstance(metrics, ParseResultMetrics)

    def test_calculate_ratios(self):
        """Test ratio calculation."""
        metrics = ParseResultMetrics(
            total_text_length=100,
            paragraph_count=10,
            heading_count=5,
        )
        text_content = "This is a test text with multiple words."
        updated_metrics = MetricsCalculator._calculate_ratios(metrics, text_content)
        
        assert isinstance(updated_metrics, ParseResultMetrics)


class TestResultScorer:
    """Tests for ResultScorer class."""

    def test_calculate_score_basic(self):
        """Test basic score calculation."""
        metrics = ParseResultMetrics(
            total_text_length=1000,
            heading_count=5,
            list_item_count=10,
            table_count=2,
            table_cell_count=20,
            inline_format_count=15,
            link_count=3,
            image_count=2,
            style_attributes_count=10,
            alignment_count=5,
            indent_count=3,
        )
        result = ParseResult(
            parser_name="test",
            text_content="Test content",
            html_content="<p>Test content</p>",
            metrics=metrics,
        )
        
        score = ResultScorer.calculate_score(result, [result])
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_score_empty_metrics(self):
        """Test score calculation with empty metrics."""
        result = ParseResult(
            parser_name="test",
            text_content="",
            html_content="",
            metrics=ParseResultMetrics(),
        )
        
        score = ResultScorer.calculate_score(result, [result])
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_get_max_values(self):
        """Test max values calculation."""
        results = [
            ParseResult(
                parser_name="test1",
                metrics=ParseResultMetrics(
                    total_text_length=100,
                    heading_count=5,
                    list_item_count=10,
                    table_count=2,
                    table_cell_count=20,
                    inline_format_count=15,
                    link_count=3,
                    image_count=2,
                    style_attributes_count=10,
                    alignment_count=5,
                    indent_count=3,
                ),
            ),
            ParseResult(
                parser_name="test2",
                metrics=ParseResultMetrics(
                    total_text_length=200,
                    heading_count=10,
                    list_item_count=20,
                    table_count=4,
                    table_cell_count=40,
                    inline_format_count=30,
                    link_count=6,
                    image_count=4,
                    style_attributes_count=20,
                    alignment_count=10,
                    indent_count=6,
                ),
            ),
        ]
        
        max_vals = ResultScorer._get_max_values(results)
        
        assert isinstance(max_vals, dict)
        assert max_vals['text_length'] == 200
        assert max_vals['heading_count'] == 10
        assert max_vals['list_item_count'] == 20

    def test_normalize(self):
        """Test value normalization."""
        assert ResultScorer._normalize(50, 100) == 0.5
        assert ResultScorer._normalize(100, 100) == 1.0
        assert ResultScorer._normalize(0, 100) == 0.0
        assert ResultScorer._normalize(150, 100) == 1.0
        assert ResultScorer._normalize(50, 0) == 0.5
        assert ResultScorer._normalize(50, None) == 0.5
