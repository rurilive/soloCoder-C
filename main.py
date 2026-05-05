import os
import uuid
import zipfile
import io
import json
import aiofiles
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, select, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

app = FastAPI(title="网络剪切板", description="临时存储文字和文件的网络剪切板")

DATA_DIR = "clipboard_data"
MAX_STORAGE_HOURS = 24

os.makedirs(DATA_DIR, exist_ok=True)

DB_HOST = "64.83.36.96"
DB_PORT = 53306
DB_USER = "mas5NrZGhvvFlLRwtnRh"
DB_PASSWORD = "lsTiBCoLk3cWvQKMZ4Mq"
DB_NAME = "cc"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ClipboardItem(Base):
    __tablename__ = "clipboard_items"

    id = Column(String(8), primary_key=True, index=True)
    type = Column(String(10), nullable=False)
    content = Column(Text, nullable=True)
    filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_count = Column(Integer, nullable=True, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    expires_at = Column(DateTime, nullable=False)


class ClipboardFile(Base):
    __tablename__ = "clipboard_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(String(8), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    original_path = Column(String(1024), nullable=True)
    file_size = Column(Integer, nullable=False)
    stored_filename = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    alembic_cfg = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
    
    command.upgrade(alembic_cfg, "head")
    
    print("Database migrations completed successfully.")


class ClipboardText(BaseModel):
    content: str
    expires_hours: int = 24


class ClipboardFileResponse(BaseModel):
    id: int
    filename: str
    original_path: Optional[str] = None
    file_size: int
    stored_filename: str


class ClipboardResponse(BaseModel):
    id: str
    type: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    content: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    file_count: Optional[int] = None
    files: Optional[list[ClipboardFileResponse]] = None


storage: Dict[str, Dict[str, Any]] = {}


def generate_id() -> str:
    return str(uuid.uuid4())[:8]


def generate_stored_filename() -> str:
    return str(uuid.uuid4())


def get_expiration_time(hours: int) -> datetime:
    return datetime.now() + timedelta(hours=min(hours, MAX_STORAGE_HOURS))


def is_expired(item: Dict[str, Any]) -> bool:
    return datetime.now() > item["expires_at"]


def cleanup_expired():
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.expires_at < datetime.now())
        expired_items = db.execute(stmt).scalars().all()
        
        for item in expired_items:
            if item.type == "file":
                file_stmt = select(ClipboardFile).where(ClipboardFile.item_id == item.id)
                files = db.execute(file_stmt).scalars().all()
                
                for file_record in files:
                    filepath = os.path.join(DATA_DIR, file_record.stored_filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                
                delete_files_stmt = delete(ClipboardFile).where(ClipboardFile.item_id == item.id)
                db.execute(delete_files_stmt)
                
                old_filepath = os.path.join(DATA_DIR, item.id)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
        
        delete_stmt = delete(ClipboardItem).where(ClipboardItem.expires_at < datetime.now())
        db.execute(delete_stmt)
        db.commit()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>网络剪切板</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { text-align: center; color: white; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
            .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
            .tab-container { display: flex; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; }
            .tab { padding: 12px 24px; cursor: pointer; border: none; background: none; font-size: 16px; color: #666; position: relative; }
            .tab.active { color: #667eea; }
            .tab.active::after { content: ''; position: absolute; bottom: -2px; left: 0; right: 0; height: 2px; background: #667eea; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            textarea { width: 100%; min-height: 200px; padding: 16px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; resize: vertical; margin-bottom: 16px; }
            textarea:focus { outline: none; border-color: #667eea; }
            .form-group { margin-bottom: 16px; }
            label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
            select, input[type="file"] { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; }
            select:focus { outline: none; border-color: #667eea; }
            .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 14px 32px; border-radius: 8px; font-size: 16px; cursor: pointer; width: 100%; font-weight: 500; transition: transform 0.2s, box-shadow 0.2s; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
            .btn:active { transform: translateY(0); }
            .btn-secondary { background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; margin-right: 8px; margin-top: 8px; }
            .btn-secondary:hover { background: #5a6268; }
            .btn-success { background: #28a745; color: white; }
            .btn-success:hover { background: #218838; }
            .btn-warning { background: #ffc107; color: #333; }
            .btn-warning:hover { background: #e0a800; }
            .result { margin-top: 20px; padding: 16px; background: #f8f9fa; border-radius: 8px; display: none; }
            .result.show { display: block; }
            .result h3 { color: #667eea; margin-bottom: 12px; }
            .result-item { display: flex; align-items: center; margin-bottom: 8px; }
            .result-item label { min-width: 80px; margin-bottom: 0; }
            .result-item span { flex: 1; word-break: break-all; font-family: monospace; background: white; padding: 8px 12px; border-radius: 4px; }
            .copy-btn { margin-left: 12px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; }
            .retrieve-section { margin-top: 20px; padding-top: 20px; border-top: 2px solid #e0e0e0; }
            .retrieve-input { display: flex; gap: 12px; }
            .retrieve-input input { flex: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; }
            .retrieve-input input:focus { outline: none; border-color: #667eea; }
            .retrieve-input button { padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; }
            .retrieved-content { margin-top: 16px; padding: 16px; background: #f8f9fa; border-radius: 8px; display: none; }
            .retrieved-content.show { display: block; }
            .retrieved-text { background: white; padding: 12px; border-radius: 4px; margin-bottom: 12px; white-space: pre-wrap; word-break: break-all; }
            .download-btn { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin-top: 12px; }
            .paste-hint { padding: 20px; background: #e8f4fd; border: 2px dashed #667eea; border-radius: 8px; text-align: center; margin-bottom: 16px; color: #667eea; }
            .paste-hint.active { background: #d4edda; border-color: #28a745; color: #28a745; }
            .edit-mode { background: #fff3cd; padding: 12px; border-radius: 8px; margin-bottom: 16px; display: none; }
            .edit-mode.active { display: block; }
            .action-buttons { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
            .extend-section { margin-top: 16px; padding: 12px; background: #e7f3ff; border-radius: 8px; }
            .extend-row { display: flex; gap: 12px; align-items: center; }
            .extend-row select { flex: 1; }
            .hidden { display: none !important; }
            .edit-textarea { width: 100%; min-height: 150px; padding: 12px; border: 2px solid #ffc107; border-radius: 8px; font-size: 14px; resize: vertical; margin-bottom: 12px; }
            .edit-file-input { margin-bottom: 12px; }
            .info-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px; }
            .info-row label { margin-bottom: 0; color: #666; font-weight: normal; }
            .info-row span { font-family: monospace; color: #333; }
            .file-list { margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px; max-height: 300px; overflow-y: auto; }
            .file-list-title { font-weight: 600; margin-bottom: 8px; color: #333; }
            .file-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: white; border-radius: 6px; margin-bottom: 6px; border: 1px solid #e0e0e0; }
            .file-item:hover { background: #f0f4ff; }
            .file-item-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
            .file-icon { font-size: 20px; }
            .file-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; }
            .file-size { color: #666; font-size: 12px; margin-left: 8px; }
            .file-download-btn { padding: 4px 12px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
            .file-download-btn:hover { background: #5a67d8; }
            .upload-section { display: flex; gap: 12px; flex-wrap: wrap; }
            .upload-btn { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
            .upload-btn:hover { background: #5a67d8; }
            .upload-btn.secondary { background: #6c757d; }
            .upload-btn.secondary:hover { background: #5a6268; }
            .file-count-badge { display: inline-block; padding: 2px 8px; background: #667eea; color: white; border-radius: 12px; font-size: 12px; margin-left: 8px; }
            .empty-list { text-align: center; padding: 20px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 网络剪切板</h1>
            
            <div class="card">
                <div class="tab-container">
                    <button class="tab active" onclick="switchTab('text')">文本</button>
                    <button class="tab" onclick="switchTab('file')">文件</button>
                </div>
                
                <div id="paste-hint" class="paste-hint">
                    💡 提示：按 Ctrl+V 可以直接粘贴文本或文件！
                </div>
                
                <div id="text-tab" class="tab-content active">
                    <div class="form-group">
                        <label>输入文本内容：</label>
                        <textarea id="text-content" placeholder="在此输入要保存的文本..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>保存时间：</label>
                        <select id="text-expire">
                            <option value="1">1 小时</option>
                            <option value="6">6 小时</option>
                            <option value="12">12 小时</option>
                            <option value="24" selected>24 小时</option>
                        </select>
                    </div>
                    <button class="btn" onclick="saveText()">保存文本</button>
                </div>
                
                <div id="file-tab" class="tab-content">
                    <div class="form-group">
                        <label>选择文件或文件夹：</label>
                        <div class="upload-section">
                            <input type="file" id="file-input" multiple style="display: none;">
                            <input type="file" id="folder-input" webkitdirectory multiple style="display: none;">
                            <button type="button" class="upload-btn" onclick="document.getElementById('file-input').click()">📁 选择文件</button>
                            <button type="button" class="upload-btn secondary" onclick="document.getElementById('folder-input').click()">📂 选择文件夹</button>
                        </div>
                    </div>
                    <div id="selected-files-list" class="file-list" style="display: none;">
                        <div class="file-list-title">已选择的文件 <span id="selected-file-count" class="file-count-badge">0</span></div>
                        <div id="selected-files-container"></div>
                    </div>
                    <div class="form-group">
                        <label>保存时间：</label>
                        <select id="file-expire">
                            <option value="1">1 小时</option>
                            <option value="6">6 小时</option>
                            <option value="12">12 小时</option>
                            <option value="24" selected>24 小时</option>
                        </select>
                    </div>
                    <button class="btn" onclick="saveFile()">保存文件</button>
                </div>
                
                <div id="save-result" class="result">
                    <h3>✅ 保存成功！</h3>
                    <div class="result-item">
                        <label>提取码：</label>
                        <span id="result-id"></span>
                        <button class="copy-btn" onclick="copyId()">复制</button>
                    </div>
                    <div class="result-item">
                        <label>过期时间：</label>
                        <span id="result-expire"></span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 16px; color: #333;">🔍 提取内容</h2>
                <div class="retrieve-input">
                    <input type="text" id="retrieve-id" placeholder="输入提取码...">
                    <button onclick="retrieveContent()">提取</button>
                </div>
                
                <div id="retrieved-content" class="retrieved-content">
                    <h3 id="retrieved-type" style="margin-bottom: 12px; color: #667eea;"></h3>
                    
                    <div class="info-row">
                        <label>创建时间：</label>
                        <span id="retrieved-created"></span>
                    </div>
                    <div class="info-row">
                        <label>更新时间：</label>
                        <span id="retrieved-updated"></span>
                    </div>
                    <div class="info-row">
                        <label>过期时间：</label>
                        <span id="retrieved-expires"></span>
                    </div>
                    
                    <div id="retrieved-text-container" style="display: none;">
                        <div class="retrieved-text" id="retrieved-text"></div>
                        <div class="action-buttons">
                            <button class="btn-secondary" onclick="copyText()">复制文本</button>
                            <button class="btn-secondary btn-warning" onclick="startEditText()">编辑内容</button>
                        </div>
                        
                        <div id="edit-text-mode" class="edit-mode">
                            <label>编辑文本：</label>
                            <textarea id="edit-textarea" class="edit-textarea"></textarea>
                            <div class="action-buttons">
                                <button class="btn-secondary btn-success" onclick="saveEditText()">保存修改</button>
                                <button class="btn-secondary" onclick="cancelEditText()">取消</button>
                            </div>
                        </div>
                    </div>
                    
                    <div id="retrieved-file-container" style="display: none;">
                        <div id="single-file-info" style="display: none;">
                            <p style="margin-bottom: 8px;"><strong>文件名：</strong><span id="retrieved-filename"></span></p>
                            <p style="margin-bottom: 8px;"><strong>文件大小：</strong><span id="retrieved-size"></span></p>
                            <div class="action-buttons">
                                <a class="download-btn" id="download-link" href="#" download>下载文件</a>
                                <button class="btn-secondary btn-warning" onclick="startEditFile()">更换文件</button>
                            </div>
                        </div>
                        <div id="multi-file-info" style="display: none;">
                            <p style="margin-bottom: 8px;"><strong>文件数量：</strong><span id="retrieved-file-count"></span> 个文件</p>
                            <p style="margin-bottom: 8px;"><strong>总大小：</strong><span id="retrieved-total-size"></span></p>
                            <div class="action-buttons">
                                <a class="download-btn" id="download-all-link" href="#" download>下载全部 (ZIP)</a>
                                <button class="btn-secondary btn-warning" onclick="startEditFile()">更换文件</button>
                            </div>
                            <div id="retrieved-files-list" class="file-list">
                                <div class="file-list-title">文件列表</div>
                                <div id="retrieved-files-container"></div>
                            </div>
                        </div>
                        
                        <div id="edit-file-mode" class="edit-mode">
                            <label>选择新文件：</label>
                            <div class="upload-section" style="margin-top: 8px;">
                                <input type="file" id="edit-file-input" multiple style="display: none;">
                                <input type="file" id="edit-folder-input" webkitdirectory multiple style="display: none;">
                                <button type="button" class="upload-btn" onclick="document.getElementById('edit-file-input').click()">📁 选择文件</button>
                                <button type="button" class="upload-btn secondary" onclick="document.getElementById('edit-folder-input').click()">📂 选择文件夹</button>
                            </div>
                            <div id="edit-selected-files-list" class="file-list" style="display: none; margin-top: 12px;">
                                <div class="file-list-title">已选择的文件 <span id="edit-selected-file-count" class="file-count-badge">0</span></div>
                                <div id="edit-selected-files-container"></div>
                            </div>
                            <div class="action-buttons" style="margin-top: 12px;">
                                <button class="btn-secondary btn-success" onclick="saveEditFile()">保存修改</button>
                                <button class="btn-secondary" onclick="cancelEditFile()">取消</button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="extend-section">
                        <label style="margin-bottom: 8px; display: block; color: #333;">⏰ 延长有效时间：</label>
                        <div class="extend-row">
                            <select id="extend-hours">
                                <option value="1">+ 1 小时</option>
                                <option value="6">+ 6 小时</option>
                                <option value="12">+ 12 小时</option>
                                <option value="24" selected>+ 24 小时</option>
                            </select>
                            <button class="btn-secondary" onclick="extendExpiration()">延长时间</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let currentRetrievedId = null;
            let currentRetrievedData = null;
            let selectedFiles = [];
            let editSelectedFiles = [];
            
            function switchTab(type) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(type + '-tab').classList.add('active');
            }
            
            function getFileIcon(filename) {
                const ext = filename.split('.').pop().toLowerCase();
                const icons = {
                    'pdf': '📄',
                    'doc': '📝', 'docx': '📝',
                    'xls': '📊', 'xlsx': '📊',
                    'ppt': '📽️', 'pptx': '📽️',
                    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'bmp': '🖼️', 'webp': '🖼️',
                    'zip': '📦', 'rar': '📦', '7z': '📦',
                    'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
                    'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
                    'txt': '📃', 'json': '📃', 'xml': '📃', 'html': '📃', 'css': '📃', 'js': '📃',
                    'py': '🐍', 'java': '☕', 'cpp': '⚡', 'c': '⚡', 'go': '🐹', 'rs': '🦀'
                };
                return icons[ext] || '📁';
            }
            
            function renderFileList(files, containerId, countId, listId) {
                const container = document.getElementById(containerId);
                const countSpan = document.getElementById(countId);
                const listDiv = document.getElementById(listId);
                
                if (files.length === 0) {
                    listDiv.style.display = 'none';
                    return;
                }
                
                countSpan.textContent = files.length;
                listDiv.style.display = 'block';
                
                let html = '';
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const icon = getFileIcon(file.name);
                    const size = formatSize(file.size);
                    const displayName = file.webkitRelativePath || file.name;
                    html += `
                        <div class="file-item">
                            <div class="file-item-info">
                                <span class="file-icon">${icon}</span>
                                <span class="file-name" title="${displayName}">${displayName}</span>
                                <span class="file-size">${size}</span>
                            </div>
                        </div>
                    `;
                }
                container.innerHTML = html;
            }
            
            function renderRetrievedFileList(files, itemId) {
                const container = document.getElementById('retrieved-files-container');
                
                if (!files || files.length === 0) {
                    container.innerHTML = '<div class="empty-list">暂无文件</div>';
                    return;
                }
                
                let html = '';
                for (let file of files) {
                    const displayName = file.original_path || file.filename;
                    const icon = getFileIcon(displayName);
                    const size = formatSize(file.file_size);
                    const downloadUrl = `/api/${itemId}/file/${file.id}/download`;
                    html += `
                        <div class="file-item">
                            <div class="file-item-info">
                                <span class="file-icon">${icon}</span>
                                <span class="file-name" title="${displayName}">${displayName}</span>
                                <span class="file-size">${size}</span>
                            </div>
                            <button class="file-download-btn" onclick="window.open('${downloadUrl}', '_blank')">下载</button>
                        </div>
                    `;
                }
                container.innerHTML = html;
            }
            
            document.addEventListener('DOMContentLoaded', function() {
                const fileInput = document.getElementById('file-input');
                const folderInput = document.getElementById('folder-input');
                const editFileInput = document.getElementById('edit-file-input');
                const editFolderInput = document.getElementById('edit-folder-input');
                
                function handleFileSelection(input, isEdit = false) {
                    const files = Array.from(input.files);
                    if (isEdit) {
                        editSelectedFiles = files;
                        renderFileList(files, 'edit-selected-files-container', 'edit-selected-file-count', 'edit-selected-files-list');
                    } else {
                        selectedFiles = files;
                        renderFileList(files, 'selected-files-container', 'selected-file-count', 'selected-files-list');
                    }
                }
                
                if (fileInput) {
                    fileInput.addEventListener('change', function() {
                        handleFileSelection(this, false);
                    });
                }
                
                if (folderInput) {
                    folderInput.addEventListener('change', function() {
                        handleFileSelection(this, false);
                    });
                }
                
                if (editFileInput) {
                    editFileInput.addEventListener('change', function() {
                        handleFileSelection(this, true);
                    });
                }
                
                if (editFolderInput) {
                    editFolderInput.addEventListener('change', function() {
                        handleFileSelection(this, true);
                    });
                }
            });
            
            document.addEventListener('paste', async function(e) {
                const pasteHint = document.getElementById('paste-hint');
                pasteHint.classList.add('active');
                setTimeout(() => pasteHint.classList.remove('active'), 1000);
                
                let pastedFiles = [];
                
                if (e.clipboardData.files && e.clipboardData.files.length > 0) {
                    pastedFiles = Array.from(e.clipboardData.files);
                }
                
                if (pastedFiles.length === 0 && e.clipboardData.items) {
                    for (let item of e.clipboardData.items) {
                        if (item.kind === 'file') {
                            const file = item.getAsFile();
                            if (file) {
                                pastedFiles.push(file);
                            }
                        }
                    }
                }
                
                if (pastedFiles.length > 0) {
                    e.preventDefault();
                    handlePastedFiles(pastedFiles);
                    return;
                }
                
                const activeElement = document.activeElement;
                const isFocusedOnInput = activeElement && (
                    activeElement.tagName === 'TEXTAREA' || 
                    (activeElement.tagName === 'INPUT' && (activeElement.type === 'text' || activeElement.type === ''))
                );
                
                if (isFocusedOnInput) {
                    return;
                }
                
                if (e.clipboardData.items) {
                    for (let item of e.clipboardData.items) {
                        if (item.type === 'text/plain') {
                            item.getAsString(function(text) {
                                if (text.trim()) {
                                    e.preventDefault();
                                    handlePastedText(text);
                                }
                            });
                            return;
                        }
                    }
                }
            });
            
            function handlePastedText(text) {
                switchTab('text');
                document.getElementById('text-content').value = text;
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.querySelectorAll('.tab')[1].classList.remove('active');
                document.getElementById('text-tab').classList.add('active');
                document.getElementById('file-tab').classList.remove('active');
            }
            
            function handlePastedFiles(files) {
                switchTab('file');
                selectedFiles = files;
                renderFileList(files, 'selected-files-container', 'selected-file-count', 'selected-files-list');
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.querySelectorAll('.tab')[0].classList.remove('active');
                document.getElementById('file-tab').classList.add('active');
                document.getElementById('text-tab').classList.remove('active');
            }
            
            async function saveText() {
                const content = document.getElementById('text-content').value;
                const expire = parseInt(document.getElementById('text-expire').value);
                
                if (!content.trim()) {
                    alert('请输入文本内容');
                    return;
                }
                
                try {
                    const response = await fetch('/api/text', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({content, expires_hours: expire})
                    });
                    const data = await response.json();
                    showResult(data);
                } catch (err) {
                    alert('保存失败：' + err.message);
                }
            }
            
            async function saveFile() {
                const expire = parseInt(document.getElementById('file-expire').value);
                
                if (selectedFiles.length === 0) {
                    alert('请选择文件');
                    return;
                }
                
                const formData = new FormData();
                const relativePaths = [];
                for (let file of selectedFiles) {
                    formData.append('files', file);
                    relativePaths.push(file.webkitRelativePath || '');
                }
                formData.append('expires_hours', expire);
                formData.append('relative_paths', JSON.stringify(relativePaths));
                
                try {
                    const response = await fetch('/api/file', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    showResult(data);
                } catch (err) {
                    alert('保存失败：' + err.message);
                }
            }
            
            function showResult(data) {
                document.getElementById('result-id').textContent = data.id;
                document.getElementById('result-expire').textContent = new Date(data.expires_at).toLocaleString('zh-CN');
                document.getElementById('save-result').classList.add('show');
            }
            
            function copyId() {
                const id = document.getElementById('result-id').textContent;
                navigator.clipboard.writeText(id).then(() => alert('已复制提取码'));
            }
            
            function copyText() {
                const text = document.getElementById('retrieved-text').textContent;
                navigator.clipboard.writeText(text).then(() => alert('已复制文本'));
            }
            
            async function retrieveContent() {
                const id = document.getElementById('retrieve-id').value.trim();
                if (!id) {
                    alert('请输入提取码');
                    return;
                }
                
                try {
                    const response = await fetch('/api/' + id);
                    if (!response.ok) {
                        throw new Error('内容不存在或已过期');
                    }
                    const data = await response.json();
                    currentRetrievedId = id;
                    currentRetrievedData = data;
                    showRetrieved(data, id);
                } catch (err) {
                    alert(err.message);
                }
            }
            
            function showRetrieved(data, id) {
                const container = document.getElementById('retrieved-content');
                const textContainer = document.getElementById('retrieved-text-container');
                const fileContainer = document.getElementById('retrieved-file-container');
                
                document.getElementById('retrieved-created').textContent = new Date(data.created_at).toLocaleString('zh-CN');
                document.getElementById('retrieved-updated').textContent = new Date(data.updated_at).toLocaleString('zh-CN');
                document.getElementById('retrieved-expires').textContent = new Date(data.expires_at).toLocaleString('zh-CN');
                
                if (data.type === 'text') {
                    document.getElementById('retrieved-type').textContent = '📝 文本内容';
                    document.getElementById('retrieved-text').textContent = data.content;
                    textContainer.style.display = 'block';
                    fileContainer.style.display = 'none';
                    document.getElementById('edit-text-mode').classList.remove('active');
                } else {
                    document.getElementById('retrieved-type').textContent = '📁 文件内容';
                    
                    const isMultiFile = data.file_count && data.file_count > 1;
                    
                    if (isMultiFile) {
                        document.getElementById('single-file-info').style.display = 'none';
                        document.getElementById('multi-file-info').style.display = 'block';
                        document.getElementById('retrieved-file-count').textContent = data.file_count;
                        document.getElementById('retrieved-total-size').textContent = formatSize(data.file_size);
                        document.getElementById('download-all-link').href = '/api/' + id + '/download';
                        document.getElementById('download-all-link').download = id + '.zip';
                        renderRetrievedFileList(data.files, id);
                    } else {
                        document.getElementById('single-file-info').style.display = 'block';
                        document.getElementById('multi-file-info').style.display = 'none';
                        document.getElementById('retrieved-filename').textContent = data.filename;
                        document.getElementById('retrieved-size').textContent = formatSize(data.file_size);
                        document.getElementById('download-link').href = '/api/' + id + '/download';
                        document.getElementById('download-link').download = data.filename;
                    }
                    
                    textContainer.style.display = 'none';
                    fileContainer.style.display = 'block';
                    document.getElementById('edit-file-mode').classList.remove('active');
                    editSelectedFiles = [];
                }
                container.classList.add('show');
            }
            
            function startEditText() {
                if (!currentRetrievedId) return;
                const text = document.getElementById('retrieved-text').textContent;
                document.getElementById('edit-textarea').value = text;
                document.getElementById('edit-text-mode').classList.add('active');
            }
            
            function cancelEditText() {
                document.getElementById('edit-text-mode').classList.remove('active');
            }
            
            async function saveEditText() {
                if (!currentRetrievedId) return;
                const content = document.getElementById('edit-textarea').value;
                
                if (!content.trim()) {
                    alert('文本内容不能为空');
                    return;
                }
                
                try {
                    const response = await fetch('/api/' + currentRetrievedId + '/text', {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({content})
                    });
                    
                    if (!response.ok) {
                        throw new Error('更新失败');
                    }
                    
                    const data = await response.json();
                    currentRetrievedData = data;
                    document.getElementById('retrieved-text').textContent = content;
                    document.getElementById('retrieved-updated').textContent = new Date(data.updated_at).toLocaleString('zh-CN');
                    document.getElementById('edit-text-mode').classList.remove('active');
                    alert('✅ 更新成功！');
                } catch (err) {
                    alert('更新失败：' + err.message);
                }
            }
            
            function startEditFile() {
                if (!currentRetrievedId) return;
                editSelectedFiles = [];
                document.getElementById('edit-selected-files-list').style.display = 'none';
                document.getElementById('edit-file-mode').classList.add('active');
            }
            
            function cancelEditFile() {
                document.getElementById('edit-file-mode').classList.remove('active');
                editSelectedFiles = [];
            }
            
            async function saveEditFile() {
                if (!currentRetrievedId) return;
                
                if (editSelectedFiles.length === 0) {
                    alert('请选择文件');
                    return;
                }
                
                const formData = new FormData();
                const relativePaths = [];
                for (let file of editSelectedFiles) {
                    formData.append('files', file);
                    relativePaths.push(file.webkitRelativePath || '');
                }
                formData.append('relative_paths', JSON.stringify(relativePaths));
                
                try {
                    const response = await fetch('/api/' + currentRetrievedId + '/file', {
                        method: 'PUT',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('更新失败');
                    }
                    
                    const data = await response.json();
                    currentRetrievedData = data;
                    
                    const isMultiFile = data.file_count && data.file_count > 1;
                    
                    if (isMultiFile) {
                        document.getElementById('single-file-info').style.display = 'none';
                        document.getElementById('multi-file-info').style.display = 'block';
                        document.getElementById('retrieved-file-count').textContent = data.file_count;
                        document.getElementById('retrieved-total-size').textContent = formatSize(data.file_size);
                        renderRetrievedFileList(data.files, currentRetrievedId);
                    } else {
                        document.getElementById('single-file-info').style.display = 'block';
                        document.getElementById('multi-file-info').style.display = 'none';
                        document.getElementById('retrieved-filename').textContent = data.filename;
                        document.getElementById('retrieved-size').textContent = formatSize(data.file_size);
                    }
                    
                    document.getElementById('retrieved-updated').textContent = new Date(data.updated_at).toLocaleString('zh-CN');
                    document.getElementById('edit-file-mode').classList.remove('active');
                    alert('✅ 文件更新成功！');
                } catch (err) {
                    alert('更新失败：' + err.message);
                }
            }
            
            async function extendExpiration() {
                if (!currentRetrievedId) return;
                const addHours = parseInt(document.getElementById('extend-hours').value);
                
                try {
                    const response = await fetch('/api/' + currentRetrievedId + '/extend', {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({add_hours: addHours})
                    });
                    
                    if (!response.ok) {
                        throw new Error('延长时间失败');
                    }
                    
                    const data = await response.json();
                    currentRetrievedData = data;
                    document.getElementById('retrieved-expires').textContent = new Date(data.expires_at).toLocaleString('zh-CN');
                    alert('✅ 已成功延长 ' + addHours + ' 小时！\\n新过期时间：' + new Date(data.expires_at).toLocaleString('zh-CN'));
                } catch (err) {
                    alert('延长时间失败：' + err.message);
                }
            }
            
            function formatSize(bytes) {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/text", response_model=ClipboardResponse)
async def save_text(item: ClipboardText):
    cleanup_expired()
    
    cid = generate_id()
    expires_at = get_expiration_time(item.expires_hours)
    created_at = datetime.now()
    
    with get_db() as db:
        db_item = ClipboardItem(
            id=cid,
            type="text",
            content=item.content,
            created_at=created_at,
            expires_at=expires_at
        )
        db.add(db_item)
        db.commit()
    
    return ClipboardResponse(
        id=cid,
        type="text",
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
        content=item.content
    )


@app.post("/api/file", response_model=ClipboardResponse)
async def save_file(
    files: list[UploadFile] = File(...),
    expires_hours: int = Form(24),
    relative_paths: Optional[str] = Form(None)
):
    cleanup_expired()
    
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")
    
    paths_list = []
    if relative_paths:
        try:
            paths_list = json.loads(relative_paths)
        except json.JSONDecodeError:
            paths_list = []
    
    while len(paths_list) < len(files):
        paths_list.append("")
    
    cid = generate_id()
    expires_at = get_expiration_time(expires_hours)
    created_at = datetime.now()
    
    total_size = 0
    first_filename = None
    file_records = []
    
    with get_db() as db:
        for idx, file in enumerate(files):
            stored_filename = generate_stored_filename()
            filepath = os.path.join(DATA_DIR, stored_filename)
            file_content = await file.read()
            
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(file_content)
            
            total_size += len(file_content)
            if first_filename is None:
                first_filename = file.filename
            
            original_path = paths_list[idx] if idx < len(paths_list) else ""
            if not original_path:
                original_path = file.filename
            
            file_record = ClipboardFile(
                item_id=cid,
                filename=file.filename or "unknown",
                original_path=original_path,
                file_size=len(file_content),
                stored_filename=stored_filename,
                created_at=created_at
            )
            file_records.append(file_record)
        
        db_item = ClipboardItem(
            id=cid,
            type="file",
            filename=first_filename,
            file_size=total_size,
            file_count=len(files),
            created_at=created_at,
            expires_at=expires_at
        )
        db.add(db_item)
        
        for fr in file_records:
            db.add(fr)
        
        db.commit()
        db.refresh(db_item)
        
        response_files = []
        for fr in file_records:
            response_files.append(ClipboardFileResponse(
                id=fr.id,
                filename=fr.filename,
                original_path=fr.original_path,
                file_size=fr.file_size,
                stored_filename=fr.stored_filename
            ))
    
    return ClipboardResponse(
        id=cid,
        type="file",
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
        filename=first_filename,
        file_size=total_size,
        file_count=len(files),
        files=response_files
    )


@app.get("/api/{cid}", response_model=ClipboardResponse)
async def get_content(cid: str):
    cleanup_expired()
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        item = db.execute(stmt).scalar_one_or_none()
        
        if item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        if item.type == "text":
            return ClipboardResponse(
                id=item.id,
                type="text",
                created_at=item.created_at,
                updated_at=item.updated_at,
                expires_at=item.expires_at,
                content=item.content
            )
        else:
            file_stmt = select(ClipboardFile).where(ClipboardFile.item_id == item.id)
            files = db.execute(file_stmt).scalars().all()
            
            response_files = []
            for f in files:
                response_files.append(ClipboardFileResponse(
                    id=f.id,
                    filename=f.filename,
                    original_path=f.original_path,
                    file_size=f.file_size,
                    stored_filename=f.stored_filename
                ))
            
            return ClipboardResponse(
                id=item.id,
                type=item.type,
                created_at=item.created_at,
                updated_at=item.updated_at,
                expires_at=item.expires_at,
                filename=item.filename,
                file_size=item.file_size,
                file_count=item.file_count,
                files=response_files if response_files else None
            )


@app.get("/api/{cid}/download")
async def download_file(cid: str):
    cleanup_expired()
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        item = db.execute(stmt).scalar_one_or_none()
        
        if item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        if item.type != "file":
            raise HTTPException(status_code=400, detail="这不是文件类型")
        
        file_stmt = select(ClipboardFile).where(ClipboardFile.item_id == item.id)
        files = db.execute(file_stmt).scalars().all()
        
        if not files:
            old_filepath = os.path.join(DATA_DIR, cid)
            if os.path.exists(old_filepath):
                return FileResponse(
                    path=old_filepath,
                    filename=item.filename or "download"
                )
            raise HTTPException(status_code=404, detail="文件已被删除")
        
        if len(files) == 1:
            file_record = files[0]
            filepath = os.path.join(DATA_DIR, file_record.stored_filename)
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail="文件已被删除")
            return FileResponse(
                path=filepath,
                filename=file_record.filename
            )
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_record in files:
                    filepath = os.path.join(DATA_DIR, file_record.stored_filename)
                    if os.path.exists(filepath):
                        arcname = file_record.original_path or file_record.filename
                        zipf.write(filepath, arcname)
            
            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={item.id}.zip"}
            )


@app.get("/api/{cid}/file/{file_id}/download")
async def download_single_file(cid: str, file_id: int):
    cleanup_expired()
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        item = db.execute(stmt).scalar_one_or_none()
        
        if item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        file_stmt = select(ClipboardFile).where(
            ClipboardFile.id == file_id,
            ClipboardFile.item_id == cid
        )
        file_record = db.execute(file_stmt).scalar_one_or_none()
        
        if file_record is None:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        filepath = os.path.join(DATA_DIR, file_record.stored_filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="文件已被删除")
        
        return FileResponse(
            path=filepath,
            filename=file_record.filename
        )


class UpdateTextRequest(BaseModel):
    content: str


@app.put("/api/{cid}/text", response_model=ClipboardResponse)
async def update_text(cid: str, item: UpdateTextRequest):
    cleanup_expired()
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        db_item = db.execute(stmt).scalar_one_or_none()
        
        if db_item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        if db_item.type != "text":
            raise HTTPException(status_code=400, detail="只能更新文本类型的内容")
        
        db_item.content = item.content
        db.commit()
        db.refresh(db_item)
        
        return ClipboardResponse(
            id=db_item.id,
            type=db_item.type,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            expires_at=db_item.expires_at,
            content=db_item.content
        )


@app.put("/api/{cid}/file", response_model=ClipboardResponse)
async def update_file(
    cid: str,
    files: list[UploadFile] = File(...),
    relative_paths: Optional[str] = Form(None)
):
    cleanup_expired()
    
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")
    
    paths_list = []
    if relative_paths:
        try:
            paths_list = json.loads(relative_paths)
        except json.JSONDecodeError:
            paths_list = []
    
    while len(paths_list) < len(files):
        paths_list.append("")
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        db_item = db.execute(stmt).scalar_one_or_none()
        
        if db_item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        if db_item.type != "file":
            raise HTTPException(status_code=400, detail="只能更新文件类型的内容")
        
        old_file_stmt = select(ClipboardFile).where(ClipboardFile.item_id == cid)
        old_files = db.execute(old_file_stmt).scalars().all()
        
        for old_file in old_files:
            filepath = os.path.join(DATA_DIR, old_file.stored_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        delete_old_stmt = delete(ClipboardFile).where(ClipboardFile.item_id == cid)
        db.execute(delete_old_stmt)
        
        total_size = 0
        first_filename = None
        new_file_records = []
        created_at = datetime.now()
        
        for idx, file in enumerate(files):
            stored_filename = generate_stored_filename()
            filepath = os.path.join(DATA_DIR, stored_filename)
            file_content = await file.read()
            
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(file_content)
            
            total_size += len(file_content)
            if first_filename is None:
                first_filename = file.filename
            
            original_path = paths_list[idx] if idx < len(paths_list) else ""
            if not original_path:
                original_path = file.filename
            
            file_record = ClipboardFile(
                item_id=cid,
                filename=file.filename or "unknown",
                original_path=original_path,
                file_size=len(file_content),
                stored_filename=stored_filename,
                created_at=created_at
            )
            new_file_records.append(file_record)
            db.add(file_record)
        
        db_item.filename = first_filename
        db_item.file_size = total_size
        db_item.file_count = len(files)
        
        db.commit()
        db.refresh(db_item)
        
        response_files = []
        for fr in new_file_records:
            db.refresh(fr)
            response_files.append(ClipboardFileResponse(
                id=fr.id,
                filename=fr.filename,
                original_path=fr.original_path,
                file_size=fr.file_size,
                stored_filename=fr.stored_filename
            ))
        
        return ClipboardResponse(
            id=db_item.id,
            type=db_item.type,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            expires_at=db_item.expires_at,
            filename=db_item.filename,
            file_size=db_item.file_size,
            file_count=db_item.file_count,
            files=response_files
        )


class ExtendExpirationRequest(BaseModel):
    add_hours: int


@app.put("/api/{cid}/extend", response_model=ClipboardResponse)
async def extend_expiration(cid: str, request: ExtendExpirationRequest):
    add_hours = min(request.add_hours, MAX_STORAGE_HOURS)
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        db_item = db.execute(stmt).scalar_one_or_none()
        
        if db_item is None:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        current_time = datetime.now()
        if db_item.expires_at < current_time:
            db_item.expires_at = current_time + timedelta(hours=add_hours)
        else:
            db_item.expires_at = db_item.expires_at + timedelta(hours=add_hours)
        
        db.commit()
        db.refresh(db_item)
        
        if db_item.type == "text":
            return ClipboardResponse(
                id=db_item.id,
                type=db_item.type,
                created_at=db_item.created_at,
                updated_at=db_item.updated_at,
                expires_at=db_item.expires_at,
                content=db_item.content
            )
        else:
            file_stmt = select(ClipboardFile).where(ClipboardFile.item_id == db_item.id)
            files = db.execute(file_stmt).scalars().all()
            
            response_files = []
            for f in files:
                response_files.append(ClipboardFileResponse(
                    id=f.id,
                    filename=f.filename,
                    original_path=f.original_path,
                    file_size=f.file_size,
                    stored_filename=f.stored_filename
                ))
            
            return ClipboardResponse(
                id=db_item.id,
                type=db_item.type,
                created_at=db_item.created_at,
                updated_at=db_item.updated_at,
                expires_at=db_item.expires_at,
                filename=db_item.filename,
                file_size=db_item.file_size,
                file_count=db_item.file_count,
                files=response_files if response_files else None
            )


@app.delete("/api/{cid}")
async def delete_content(cid: str):
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        item = db.execute(stmt).scalar_one_or_none()
        
        if item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        delete_stmt = delete(ClipboardItem).where(ClipboardItem.id == cid)
        db.execute(delete_stmt)
        db.commit()
        
        if item.type == "file":
            filepath = os.path.join(DATA_DIR, cid)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return {"message": "已删除"}


def find_available_port(start_port: int = 3333, max_attempts: int = 10) -> int:
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return start_port


if __name__ == "__main__":
    import uvicorn
    
    run_migrations()
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 3333))
    
    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"端口 {port} 已被占用，正在查找可用端口...")
            available_port = find_available_port(port + 1)
            print(f"使用端口 {available_port} 启动服务...")
            uvicorn.run(app, host=host, port=available_port)
        else:
            raise
