"""Pytest configuration and fixtures."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Generator, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db
from app.main import app


TEST_DIR = Path(__file__).parent
TEST_DATA_DIR = TEST_DIR / "test_data"


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Fixture for test data directory."""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    return TEST_DATA_DIR


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Fixture for temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def temp_excel_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Fixture for creating a temporary Excel file."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    
    file_path = temp_dir / "test.xlsx"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    headers = ["Name", "Age", "City", "Salary"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    data = [
        ["Alice", 30, "New York", 75000],
        ["Bob", 25, "London", 60000],
        ["Charlie", 35, "Paris", 80000],
    ]
    
    for row_idx, row_data in enumerate(data, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    ws2 = wb.create_sheet("Sheet2")
    ws2.append(["Product", "Price", "Stock"])
    ws2.append(["Laptop", 999, 50])
    ws2.append(["Phone", 699, 100])
    
    wb.save(file_path)
    
    yield file_path
    
    if file_path.exists():
        file_path.unlink()


@pytest.fixture(scope="function")
def temp_docx_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Fixture for creating a temporary DOCX file."""
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    file_path = temp_dir / "test.docx"
    
    doc = Document()
    
    title = doc.add_heading("Test Document", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_heading("Introduction", level=2)
    para1 = doc.add_paragraph("This is a test paragraph with some ")
    run1 = para1.add_run("bold text")
    run1.bold = True
    para1.add_run(" and some ")
    run2 = para1.add_run("italic text")
    run2.italic = True
    para1.add_run(".")
    
    doc.add_heading("List Section", level=2)
    doc.add_paragraph("First item", style="List Bullet")
    doc.add_paragraph("Second item", style="List Bullet")
    doc.add_paragraph("Third item", style="List Bullet")
    
    doc.add_heading("Table Section", level=2)
    table = doc.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    
    headers = ["Name", "Age", "City"]
    for idx, header in enumerate(headers):
        table.rows[0].cells[idx].text = header
    
    table.rows[1].cells[0].text = "Alice"
    table.rows[1].cells[1].text = "30"
    table.rows[1].cells[2].text = "New York"
    
    table.rows[2].cells[0].text = "Bob"
    table.rows[2].cells[1].text = "25"
    table.rows[2].cells[2].text = "London"
    
    doc.save(file_path)
    
    yield file_path
    
    if file_path.exists():
        file_path.unlink()


@pytest.fixture(scope="function")
def temp_pptx_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Fixture for creating a temporary PPTX file."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    
    file_path = temp_dir / "test.pptx"
    
    prs = Presentation()
    
    title_slide_layout = prs.slide_layouts[0]
    slide1 = prs.slides.add_slide(title_slide_layout)
    title = slide1.shapes.title
    subtitle = slide1.placeholders[1]
    title.text = "Test Presentation"
    subtitle.text = "Created for testing purposes"
    
    bullet_slide_layout = prs.slide_layouts[1]
    slide2 = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide2.shapes
    
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    
    title_shape.text = "Second Slide"
    
    tf = body_shape.text_frame
    tf.text = "First bullet point"
    
    p = tf.add_paragraph()
    p.text = "Second bullet point"
    p.level = 1
    
    p = tf.add_paragraph()
    p.text = "Third bullet point"
    p.level = 1
    
    table_slide_layout = prs.slide_layouts[5]
    slide3 = prs.slides.add_slide(table_slide_layout)
    
    title_shape = slide3.shapes.title
    title_shape.text = "Table Slide"
    
    rows = 3
    cols = 3
    left = Inches(0.5)
    top = Inches(1.5)
    width = Inches(9)
    height = Inches(0.8)
    
    table = slide3.shapes.add_table(rows, cols, left, top, width, height).table
    
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Age"
    table.cell(0, 2).text = "City"
    
    table.cell(1, 0).text = "Alice"
    table.cell(1, 1).text = "30"
    table.cell(1, 2).text = "New York"
    
    table.cell(2, 0).text = "Bob"
    table.cell(2, 1).text = "25"
    table.cell(2, 2).text = "London"
    
    prs.save(file_path)
    
    yield file_path
    
    if file_path.exists():
        file_path.unlink()


@pytest.fixture(scope="function")
def temp_image_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Fixture for creating a temporary image file (1x1 PNG)."""
    file_path = temp_dir / "test_image.png"
    
    png_header = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])
    
    file_path.write_bytes(png_header)
    
    yield file_path
    
    if file_path.exists():
        file_path.unlink()


@pytest.fixture(scope="function")
def temp_markdown_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Fixture for creating a temporary Markdown file."""
    file_path = temp_dir / "test.md"
    
    content = """# Test Document

## Introduction

This is a test markdown document. It contains **bold text** and *italic text*.

## Features

- Feature 1
- Feature 2
- Feature 3

## Code Example

\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

## Table

| Name | Age | City |
|------|-----|------|
| Alice | 30 | New York |
| Bob | 25 | London |

## Conclusion

This is the end of the test document.
"""
    
    file_path.write_text(content, encoding="utf-8")
    
    yield file_path
    
    if file_path.exists():
        file_path.unlink()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Fixture for database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Fixture for FastAPI test client."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
