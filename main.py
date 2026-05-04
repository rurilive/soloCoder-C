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
    expires_at = Column(DateTime, nullable=False)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


class ClipboardText(BaseModel):
    content: str
    expires_hours: int = 24


class ClipboardResponse(BaseModel):
    id: str
    type: str
    created_at: datetime
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
                    <div id="retrieved-text-container" style="display: none;">
                        <div class="retrieved-text" id="retrieved-text"></div>
                        <button class="copy-btn" onclick="copyText()">复制文本</button>
                    </div>
                    <div id="retrieved-file-container" style="display: none;">
                        <p style="margin-bottom: 8px;"><strong>文件名：</strong><span id="retrieved-filename"></span></p>
                        <p style="margin-bottom: 8px;"><strong>文件大小：</strong><span id="retrieved-size"></span></p>
                        <a class="download-btn" id="download-link" href="#" download>下载文件</a>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function switchTab(type) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById(type + '-tab').classList.add('active');
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
                    showRetrieved(data, id);
                } catch (err) {
                    alert(err.message);
                }
            }
            
            function showRetrieved(data, id) {
                const container = document.getElementById('retrieved-content');
                const textContainer = document.getElementById('retrieved-text-container');
                const fileContainer = document.getElementById('retrieved-file-container');
                
                if (data.type === 'text') {
                    document.getElementById('retrieved-type').textContent = '📝 文本内容';
                    document.getElementById('retrieved-text').textContent = data.content;
                    textContainer.style.display = 'block';
                    fileContainer.style.display = 'none';
                } else {
                    document.getElementById('retrieved-type').textContent = '📁 文件内容';
                    document.getElementById('retrieved-filename').textContent = data.filename;
                    document.getElementById('retrieved-size').textContent = formatSize(data.file_size);
                    document.getElementById('download-link').href = '/api/' + id + '/download';
                    document.getElementById('download-link').download = data.filename;
                    textContainer.style.display = 'none';
                    fileContainer.style.display = 'block';
                }
                container.classList.add('show');
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
                expires_at=item.expires_at,
                content=item.content
            )
        else:
            return ClipboardResponse(
                id=item.id,
                type="file",
                created_at=item.created_at,
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
    
    init_db()
    
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
