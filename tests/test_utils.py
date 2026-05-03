import pytest
from app.utils import (
    get_file_extension,
    get_file_type,
    generate_unique_filename,
    parse_file,
    SUPPORTED_TYPES,
)


class TestFileExtension:
    def test_get_file_extension_basic(self):
        assert get_file_extension("test.txt") == "txt"
        assert get_file_extension("test.DOCX") == "docx"
        assert get_file_extension("test.tar.gz") == "gz"
    
    def test_get_file_extension_no_extension(self):
        assert get_file_extension("test") == ""
        assert get_file_extension("test.") == ""


class TestFileType:
    def test_get_file_type_supported(self):
        assert get_file_type("test.md") == "markdown"
        assert get_file_type("test.docx") == "doc"
        assert get_file_type("test.xlsx") == "excel"
        assert get_file_type("test.pptx") == "ppt"
    
    def test_get_file_type_unsupported(self):
        assert get_file_type("test.txt") == "unknown"
        assert get_file_type("test.exe") == "unknown"
        assert get_file_type("test") == "unknown"


class TestUniqueFilename:
    def test_generate_unique_filename_basic(self):
        filename = generate_unique_filename("test.docx")
        assert filename.endswith(".docx")
        assert len(filename) > len("test.docx")
    
    def test_generate_unique_filename_no_extension(self):
        filename = generate_unique_filename("test")
        assert "." not in filename.split("_")[-1]


class TestParseFileEdgeCases:
    def test_parse_file_unknown_type(self):
        content, html = parse_file("/tmp/test.unknown", "unknown")
        assert content == ""
        assert html == ""
    
    def test_parse_file_invalid_path_markdown(self):
        content, html = parse_file("/nonexistent/path/file.md", "markdown")
        assert content == ""
        assert html == ""


class TestGetSnippet:
    def test_get_snippet_empty_content(self):
        from app.routers.search import get_snippet
        assert get_snippet("", "test") == ""
        assert get_snippet("content", "") == ""
        assert get_snippet(None, "test") == ""
    
    def test_get_snippet_match_at_start(self):
        from app.routers.search import get_snippet
        content = "test content here"
        snippet = get_snippet(content, "test")
        assert "test" in snippet
    
    def test_get_snippet_match_in_middle(self):
        from app.routers.search import get_snippet
        content = "a" * 50 + "test" + "b" * 50
        snippet = get_snippet(content, "test")
        assert "test" in snippet
    
    def test_get_snippet_no_match(self):
        from app.routers.search import get_snippet
        content = "This is some random content without the search term"
        snippet = get_snippet(content, "notfound")
        assert snippet != ""
    
    def test_get_snippet_long_content_no_match(self):
        from app.routers.search import get_snippet
        words = ["word" + str(i) for i in range(30)]
        content = " ".join(words)
        snippet = get_snippet(content, "notfound")
        assert "..." in snippet or len(snippet.split()) <= 20
