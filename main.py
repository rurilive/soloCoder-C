import os
import uuid
import aiofiles
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    expires_at = Column(DateTime, nullable=False)


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


class ClipboardResponse(BaseModel):
    id: str
    type: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    content: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None


storage: Dict[str, Dict[str, Any]] = {}


def generate_id() -> str:
    return str(uuid.uuid4())[:8]


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
                filepath = os.path.join(DATA_DIR, item.id)
                if os.path.exists(filepath):
                    os.remove(filepath)
        
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
                        <label>选择文件：</label>
                        <input type="file" id="file-input">
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
                        <p style="margin-bottom: 8px;"><strong>文件名：</strong><span id="retrieved-filename"></span></p>
                        <p style="margin-bottom: 8px;"><strong>文件大小：</strong><span id="retrieved-size"></span></p>
                        <div class="action-buttons">
                            <a class="download-btn" id="download-link" href="#" download>下载文件</a>
                            <button class="btn-secondary btn-warning" onclick="startEditFile()">更换文件</button>
                        </div>
                        
                        <div id="edit-file-mode" class="edit-mode">
                            <label>选择新文件：</label>
                            <input type="file" id="edit-file-input" class="edit-file-input">
                            <div class="action-buttons">
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
            
            function switchTab(type) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(type + '-tab').classList.add('active');
            }
            
            document.addEventListener('paste', async function(e) {
                const pasteHint = document.getElementById('paste-hint');
                pasteHint.classList.add('active');
                setTimeout(() => pasteHint.classList.remove('active'), 1000);
                
                // 检查是否有文件被粘贴
                let hasFile = false;
                let fileToPaste = null;
                
                // 方式1: 检查 clipboardData.files
                if (e.clipboardData.files && e.clipboardData.files.length > 0) {
                    hasFile = true;
                    fileToPaste = e.clipboardData.files[0];
                }
                
                // 方式2: 检查 items 中的 file 类型
                if (!hasFile && e.clipboardData.items) {
                    for (let item of e.clipboardData.items) {
                        if (item.kind === 'file') {
                            hasFile = true;
                            fileToPaste = item.getAsFile();
                            break;
                        }
                    }
                }
                
                if (hasFile && fileToPaste) {
                    // 粘贴的是文件，阻止默认行为并处理
                    e.preventDefault();
                    handlePastedFile(fileToPaste);
                    return;
                }
                
                // 粘贴的是文本
                // 检查焦点是否在文本输入框中
                const activeElement = document.activeElement;
                const isFocusedOnInput = activeElement && (
                    activeElement.tagName === 'TEXTAREA' || 
                    (activeElement.tagName === 'INPUT' && (activeElement.type === 'text' || activeElement.type === ''))
                );
                
                if (isFocusedOnInput) {
                    // 焦点在输入框中，不阻止默认行为，让浏览器正常处理粘贴
                    return;
                }
                
                // 焦点不在输入框中，检查是否有文本内容
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
            
            function handlePastedFile(file) {
                switchTab('file');
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('file-input').files = dataTransfer.files;
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
                const fileInput = document.getElementById('file-input');
                const expire = parseInt(document.getElementById('file-expire').value);
                
                if (!fileInput.files.length) {
                    alert('请选择文件');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('expires_hours', expire);
                
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
                    document.getElementById('retrieved-filename').textContent = data.filename;
                    document.getElementById('retrieved-size').textContent = formatSize(data.file_size);
                    document.getElementById('download-link').href = '/api/' + id + '/download';
                    document.getElementById('download-link').download = data.filename;
                    textContainer.style.display = 'none';
                    fileContainer.style.display = 'block';
                    document.getElementById('edit-file-mode').classList.remove('active');
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
                document.getElementById('edit-file-input').value = '';
                document.getElementById('edit-file-mode').classList.add('active');
            }
            
            function cancelEditFile() {
                document.getElementById('edit-file-mode').classList.remove('active');
            }
            
            async function saveEditFile() {
                if (!currentRetrievedId) return;
                const fileInput = document.getElementById('edit-file-input');
                
                if (!fileInput.files.length) {
                    alert('请选择文件');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
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
                    document.getElementById('retrieved-filename').textContent = data.filename;
                    document.getElementById('retrieved-size').textContent = formatSize(data.file_size);
                    document.getElementById('retrieved-updated').textContent = new Date(data.updated_at).toLocaleString('zh-CN');
                    document.getElementById('download-link').href = '/api/' + currentRetrievedId + '/download';
                    document.getElementById('download-link').download = data.filename;
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
async def save_file(file: UploadFile = File(...), expires_hours: int = Form(24)):
    cleanup_expired()
    
    cid = generate_id()
    expires_at = get_expiration_time(expires_hours)
    created_at = datetime.now()
    
    filepath = os.path.join(DATA_DIR, cid)
    file_content = await file.read()
    
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_content)
    
    with get_db() as db:
        db_item = ClipboardItem(
            id=cid,
            type="file",
            filename=file.filename,
            file_size=len(file_content),
            created_at=created_at,
            expires_at=expires_at
        )
        db.add(db_item)
        db.commit()
    
    return ClipboardResponse(
        id=cid,
        type="file",
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
        filename=file.filename,
        file_size=len(file_content)
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
            return ClipboardResponse(
                id=item.id,
                type="file",
                created_at=item.created_at,
                updated_at=item.updated_at,
                expires_at=item.expires_at,
                filename=item.filename,
                file_size=item.file_size
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
        
        filepath = os.path.join(DATA_DIR, cid)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="文件已被删除")
        
        return FileResponse(
            path=filepath,
            filename=item.filename
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
async def update_file(cid: str, file: UploadFile = File(...)):
    cleanup_expired()
    
    with get_db() as db:
        stmt = select(ClipboardItem).where(ClipboardItem.id == cid)
        db_item = db.execute(stmt).scalar_one_or_none()
        
        if db_item is None:
            raise HTTPException(status_code=404, detail="内容不存在或已过期")
        
        if db_item.type != "file":
            raise HTTPException(status_code=400, detail="只能更新文件类型的内容")
        
        filepath = os.path.join(DATA_DIR, cid)
        file_content = await file.read()
        
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(file_content)
        
        db_item.filename = file.filename
        db_item.file_size = len(file_content)
        db.commit()
        db.refresh(db_item)
        
        return ClipboardResponse(
            id=db_item.id,
            type=db_item.type,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            expires_at=db_item.expires_at,
            filename=db_item.filename,
            file_size=db_item.file_size
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
            return ClipboardResponse(
                id=db_item.id,
                type=db_item.type,
                created_at=db_item.created_at,
                updated_at=db_item.updated_at,
                expires_at=db_item.expires_at,
                filename=db_item.filename,
                file_size=db_item.file_size
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
