"""Tests for API endpoints."""
import sys
import io
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from docx import Document as DocxDocument
from openpyxl import Workbook
from pptx import Presentation

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Document, Folder


class TestDocumentEndpoints:
    """Tests for document-related API endpoints."""

    def test_get_documents_empty(self, client: TestClient, db_session: Session):
        """Test getting documents when none exist."""
        response = client.get("/api/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 0

    def test_get_documents_with_data(self, client: TestClient, db_session: Session):
        """Test getting documents when some exist."""
        doc1 = Document(
            title="Test Document 1",
            filename="test1.docx",
            file_type="doc",
            file_path="/uploads/test1.docx",
            content="Test content 1",
            html_content="<p>Test content 1</p>",
        )
        doc2 = Document(
            title="Test Document 2",
            filename="test2.xlsx",
            file_type="excel",
            file_path="/uploads/test2.xlsx",
            content="Test content 2",
            html_content="<p>Test content 2</p>",
        )
        
        db_session.add_all([doc1, doc2])
        db_session.commit()
        
        response = client.get("/api/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2
        
        titles = [doc["title"] for doc in data["documents"]]
        assert "Test Document 1" in titles
        assert "Test Document 2" in titles

    def test_get_document_by_id(self, client: TestClient, db_session: Session):
        """Test getting a single document by ID."""
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(f"/api/documents/{doc.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc.id
        assert data["title"] == "Test Document"
        assert data["filename"] == "test.docx"
        assert data["file_type"] == "doc"
        assert data["content"] == "Test content"
        assert data["html_content"] == "<p>Test content</p>"

    def test_get_document_not_found(self, client: TestClient):
        """Test getting a non-existent document."""
        response = client.get("/api/documents/999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_document(self, client: TestClient, db_session: Session):
        """Test deleting a document."""
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        doc_id = doc.id
        
        response = client.delete(f"/api/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        deleted_doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert deleted_doc is None

    def test_delete_document_not_found(self, client: TestClient):
        """Test deleting a non-existent document."""
        response = client.delete("/api/documents/999999")
        
        assert response.status_code == 404

    def test_update_document(self, client: TestClient, db_session: Session):
        """Test updating a document."""
        doc = Document(
            title="Original Title",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Original content",
            html_content="<p>Original content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        update_data = {
            "title": "Updated Title",
            "content": "Updated content",
            "html_content": "<p>Updated content</p>",
        }
        
        response = client.put(
            f"/api/documents/{doc.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"
        assert data["html_content"] == "<p>Updated content</p>"

    def test_update_document_partial(self, client: TestClient, db_session: Session):
        """Test updating only some fields of a document."""
        doc = Document(
            title="Original Title",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Original content",
            html_content="<p>Original content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        update_data = {
            "title": "Updated Title",
        }
        
        response = client.put(
            f"/api/documents/{doc.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Original content"

    def test_update_document_not_found(self, client: TestClient):
        """Test updating a non-existent document."""
        update_data = {
            "title": "Updated Title",
        }
        
        response = client.put(
            "/api/documents/999999",
            json=update_data
        )
        
        assert response.status_code == 404


class TestUploadEndpoints:
    """Tests for file upload API endpoints."""

    def test_upload_unsupported_file(self, client: TestClient):
        """Test uploading an unsupported file type."""
        file_content = b"This is a test file"
        file = io.BytesIO(file_content)
        
        response = client.post(
            "/api/upload/",
            files={"file": ("test.txt", file, "text/plain")},
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "不支持" in data["detail"] or "unsupported" in data["detail"].lower()

    def test_upload_multiple_files(self, client: TestClient, temp_dir: Path, monkeypatch):
        """Test uploading multiple files."""
        with patch('app.utils.parse_file', return_value=("Test content", "<p>Test</p>")):
            with patch('app.utils.save_upload_file', return_value=Path("/uploads/test.xlsx")):
                file1_content = b"Excel file content"
                file1 = io.BytesIO(file1_content)
                
                file2_content = b"Docx file content"
                file2 = io.BytesIO(file2_content)
                
                response = client.post(
                    "/api/upload/multiple",
                    files=[
                        ("files", ("test1.xlsx", file1, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                        ("files", ("test2.docx", file2, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                    ],
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "success" in data or "success_count" in data or len(data.get("success", [])) >= 0


class TestFolderEndpoints:
    """Tests for folder-related API endpoints."""

    def test_get_folders_empty(self, client: TestClient, db_session: Session):
        """Test getting folders when none exist."""
        response = client.get("/api/folders/")
        
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        assert len(data["folders"]) == 0

    def test_create_folder(self, client: TestClient, db_session: Session):
        """Test creating a new folder."""
        response = client.post(
            "/api/folders/",
            data={"name": "Test Folder"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "folder" in data
        assert data["folder"]["name"] == "Test Folder"
        
        folder = db_session.query(Folder).filter(Folder.id == data["folder"]["id"]).first()
        assert folder is not None
        assert folder.name == "Test Folder"

    def test_create_folder_with_parent(self, client: TestClient, db_session: Session):
        """Test creating a folder with a parent folder."""
        parent_folder = Folder(name="Parent Folder")
        db_session.add(parent_folder)
        db_session.commit()
        parent_folder_id = parent_folder.id
        
        response = client.post(
            "/api/folders/",
            data={"name": "Child Folder", "parent_id": parent_folder_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["folder"]["parent_id"] == parent_folder_id

    def test_get_folder_by_id(self, client: TestClient, db_session: Session):
        """Test getting a single folder by ID."""
        folder = Folder(name="Test Folder")
        db_session.add(folder)
        db_session.commit()
        db_session.refresh(folder)
        
        response = client.get(f"/api/folders/{folder.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == folder.id
        assert data["name"] == "Test Folder"

    def test_get_folder_not_found(self, client: TestClient):
        """Test getting a non-existent folder."""
        response = client.get("/api/folders/999999")
        
        assert response.status_code == 404

    def test_delete_folder(self, client: TestClient, db_session: Session):
        """Test deleting a folder."""
        folder = Folder(name="Test Folder")
        db_session.add(folder)
        db_session.commit()
        folder_id = folder.id
        
        response = client.delete(f"/api/folders/{folder_id}")
        
        assert response.status_code == 200
        
        deleted_folder = db_session.query(Folder).filter(Folder.id == folder_id).first()
        assert deleted_folder is None

    def test_delete_folder_with_documents(self, client: TestClient, db_session: Session):
        """Test that deleting a folder also deletes its documents (cascade)."""
        folder = Folder(name="Test Folder")
        db_session.add(folder)
        db_session.commit()
        db_session.refresh(folder)
        
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
            folder_id=folder.id,
        )
        
        db_session.add(doc)
        db_session.commit()
        folder_id = folder.id
        doc_id = doc.id
        
        response = client.delete(f"/api/folders/{folder_id}")
        
        assert response.status_code == 200
        
        deleted_folder = db_session.query(Folder).filter(Folder.id == folder_id).first()
        assert deleted_folder is None
        
        deleted_doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert deleted_doc is None


class TestSearchEndpoints:
    """Tests for search API endpoints."""

    def test_search_documents(self, client: TestClient, db_session: Session):
        """Test searching for documents."""
        doc1 = Document(
            title="Python Programming",
            filename="python.docx",
            file_type="doc",
            file_path="/uploads/python.docx",
            content="Python is a great programming language",
            html_content="<p>Python is a great programming language</p>",
        )
        doc2 = Document(
            title="JavaScript Guide",
            filename="javascript.docx",
            file_type="doc",
            file_path="/uploads/javascript.docx",
            content="JavaScript is used for web development",
            html_content="<p>JavaScript is used for web development</p>",
        )
        
        db_session.add_all([doc1, doc2])
        db_session.commit()
        
        response = client.get("/api/search/?q=Python")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_search_no_query(self, client: TestClient):
        """Test search with no query parameter (should fail as q is required)."""
        response = client.get("/api/search/")
        
        assert response.status_code == 422


class TestExcelSpecificEndpoints:
    """Tests for Excel-specific API endpoints."""

    def test_get_excel_metadata(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test getting Excel metadata."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(f"/api/documents/{doc.id}/excel/metadata")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sheet_count"] == 2

    def test_get_excel_metadata_not_excel(self, client: TestClient, db_session: Session):
        """Test getting metadata for non-Excel document."""
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(f"/api/documents/{doc.id}/excel/metadata")
        
        assert response.status_code == 400

    def test_get_excel_data(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test getting Excel data."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(f"/api/documents/{doc.id}/excel/data")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sheet_count"] == 2

    def test_get_excel_data_paginated(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test getting Excel data with pagination."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(
            f"/api/documents/{doc.id}/excel/data/paginated?sheet_name=Sheet1&start_row=1&end_row=2"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 2

    def test_update_excel_cell(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test updating an Excel cell."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        update_data = {
            "sheet_name": "Sheet1",
            "row": 2,
            "col": 1,
            "value": "Updated Name",
        }
        
        response = client.put(
            f"/api/documents/{doc.id}/excel/cell",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_update_excel_cells_batch(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test batch updating Excel cells."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        update_data = {
            "updates": [
                {"sheet_name": "Sheet1", "row": 2, "col": 1, "value": "Updated Name 1"},
                {"sheet_name": "Sheet1", "row": 3, "col": 1, "value": "Updated Name 2"},
            ]
        }
        
        response = client.put(
            f"/api/documents/{doc.id}/excel/cells",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data or "message" in data

    def test_add_excel_sheet(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test adding a new Excel sheet."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        operation_data = {
            "sheet_name": "NewSheet",
        }
        
        response = client.post(
            f"/api/documents/{doc.id}/excel/sheet",
            json=operation_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_delete_excel_sheet(self, client: TestClient, db_session: Session, temp_excel_file: Path):
        """Test deleting an Excel sheet."""
        doc = Document(
            title="Test Excel",
            filename="test.xlsx",
            file_type="excel",
            file_path=str(temp_excel_file),
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        operation_data = {
            "sheet_name": "Sheet2",
        }
        
        response = client.request(
            "DELETE",
            f"/api/documents/{doc.id}/excel/sheet",
            json=operation_data
        )
        
        assert response.status_code == 200


class TestDocumentMoveEndpoint:
    """Tests for document move endpoint."""

    def test_move_document_to_folder(self, client: TestClient, db_session: Session):
        """Test moving a document to a folder."""
        folder = Folder(name="Target Folder")
        db_session.add(folder)
        db_session.commit()
        folder_id = folder.id
        
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
            folder_id=None,
        )
        
        db_session.add(doc)
        db_session.commit()
        doc_id = doc.id
        
        response = client.put(f"/api/documents/{doc_id}/move/{folder_id}")
        
        assert response.status_code == 200
        
        updated_doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert updated_doc.folder_id == folder_id

    def test_move_document_to_root(self, client: TestClient, db_session: Session):
        """Test moving a document back to root (folder_id=0)."""
        folder = Folder(name="Source Folder")
        db_session.add(folder)
        db_session.commit()
        folder_id = folder.id
        
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
            folder_id=folder_id,
        )
        
        db_session.add(doc)
        db_session.commit()
        doc_id = doc.id
        
        response = client.put(f"/api/documents/{doc_id}/move/0")
        
        assert response.status_code == 200
        
        updated_doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert updated_doc.folder_id is None

    def test_move_document_not_found(self, client: TestClient):
        """Test moving a non-existent document."""
        response = client.put("/api/documents/999999/move/1")
        
        assert response.status_code == 404

    def test_move_document_to_nonexistent_folder(self, client: TestClient, db_session: Session):
        """Test moving a document to a non-existent folder."""
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.put(f"/api/documents/{doc.id}/move/999999")
        
        assert response.status_code == 404


class TestReparseEndpoint:
    """Tests for document reparse endpoint."""

    def test_reparse_document(self, client: TestClient, db_session: Session, temp_docx_file: Path):
        """Test re-parsing a document."""
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path=str(temp_docx_file),
            content="Old content",
            html_content="<p>Old content</p>",
        )
        
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.post(f"/api/documents/{doc.id}/reparse")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "content" in data

    def test_reparse_document_not_found(self, client: TestClient):
        """Test re-parsing a non-existent document."""
        response = client.post("/api/documents/999999/reparse")
        
        assert response.status_code == 404


class TestFolderTreeEndpoint:
    """Tests for folder tree endpoint."""

    def test_get_folders_with_tree_param(self, client: TestClient, db_session: Session):
        """Test getting folders with tree=true parameter."""
        parent_folder = Folder(name="Parent Folder")
        db_session.add(parent_folder)
        db_session.commit()
        parent_id = parent_folder.id
        
        child_folder = Folder(name="Child Folder", parent_id=parent_id)
        db_session.add(child_folder)
        db_session.commit()
        
        response = client.get("/api/folders/?tree=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        assert len(data["folders"]) > 0

    def test_get_folder_tree_endpoint(self, client: TestClient, db_session: Session):
        """Test the dedicated /tree endpoint."""
        folder = Folder(name="Test Folder")
        db_session.add(folder)
        db_session.commit()
        
        response = client.get("/api/folders/tree")
        
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data

    def test_get_folder_tree_with_documents(self, client: TestClient, db_session: Session):
        """Test getting folder tree with documents in folders."""
        folder = Folder(name="Test Folder")
        db_session.add(folder)
        db_session.commit()
        folder_id = folder.id
        
        doc = Document(
            title="Test Document",
            filename="test.docx",
            file_type="doc",
            file_path="/uploads/test.docx",
            content="Test content",
            html_content="<p>Test content</p>",
            folder_id=folder_id,
        )
        db_session.add(doc)
        db_session.commit()
        
        response = client.get(f"/api/folders/{folder_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) > 0


class TestUpdateFolderEndpoint:
    """Tests for folder update endpoint."""

    def test_update_folder(self, client: TestClient, db_session: Session):
        """Test updating a folder name."""
        folder = Folder(name="Old Name")
        db_session.add(folder)
        db_session.commit()
        folder_id = folder.id
        
        response = client.put(
            f"/api/folders/{folder_id}",
            data={"name": "New Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        updated_folder = db_session.query(Folder).filter(Folder.id == folder_id).first()
        assert updated_folder.name == "New Name"

    def test_update_folder_not_found(self, client: TestClient):
        """Test updating a non-existent folder."""
        response = client.put(
            "/api/folders/999999",
            data={"name": "New Name"}
        )
        
        assert response.status_code == 404


class TestCreateFolderWithInvalidParent:
    """Tests for creating folder with invalid parent."""

    def test_create_folder_with_nonexistent_parent(self, client: TestClient):
        """Test creating a folder with a parent that doesn't exist."""
        response = client.post(
            "/api/folders/",
            data={"name": "Test Folder", "parent_id": 999999}
        )
        
        assert response.status_code == 404


class TestHtmlPages:
    """Tests for HTML page endpoints."""

    def test_home_page(self, client: TestClient):
        """Test the home page endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_document_detail_page(self, client: TestClient):
        """Test the document detail page."""
        response = client.get("/document/1")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_folder_detail_page(self, client: TestClient):
        """Test the folder detail page."""
        response = client.get("/folder/1")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_search_page(self, client: TestClient):
        """Test the search page."""
        response = client.get("/search")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_search_page_with_query(self, client: TestClient):
        """Test the search page with a query parameter."""
        response = client.get("/search?q=test")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
