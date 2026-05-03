from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from typing import Optional, List
from pydantic import BaseModel

from database import get_db, init_db, FileComparison
from diff_utils import compare_files, generate_html_diff
from file_validator import validate_uploaded_file

app = FastAPI(
    title="File Diff Comparison API",
    description="A file difference comparison tool with SQLite storage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComparisonResponse(BaseModel):
    id: int
    file1_name: str
    file2_name: str
    created_at: str
    stats: dict

    class Config:
        from_attributes = True


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/api/compare", response_model=dict)
async def compare_two_files(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    save_to_db: bool = True,
    db: Session = Depends(get_db)
):
    file1_bytes = await file1.read()
    file2_bytes = await file2.read()
    
    file1_valid, file1_msg = validate_uploaded_file(file1.filename or "file1", file1_bytes)
    file2_valid, file2_msg = validate_uploaded_file(file2.filename or "file2", file2_bytes)
    
    if not file1_valid:
        raise HTTPException(
            status_code=400,
            detail=f"File 1 validation failed: {file1_msg}"
        )
    
    if not file2_valid:
        raise HTTPException(
            status_code=400,
            detail=f"File 2 validation failed: {file2_msg}"
        )
    
    try:
        content1 = file1_bytes.decode("utf-8")
        content2 = file2_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Only UTF-8 encoded text files are supported"
        )

    result = compare_files(content1, content2)
    html_diff = generate_html_diff(content1, content2)

    if save_to_db:
        comparison = FileComparison(
            file1_name=file1.filename or "file1.txt",
            file2_name=file2.filename or "file2.txt",
            file1_content=content1,
            file2_content=content2,
            diff_result=json.dumps(result, ensure_ascii=False)
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        result_id = comparison.id
    else:
        result_id = None

    return {
        "success": True,
        "comparison_id": result_id,
        "file1": {"name": file1.filename, "lines": result['stats']['total_lines1']},
        "file2": {"name": file2.filename, "lines": result['stats']['total_lines2']},
        "stats": result['stats'],
        "diff": result['diff'],
        "html_diff": html_diff
    }


@app.post("/api/compare/text", response_model=dict)
async def compare_texts(
    text1: str,
    text2: str,
    name1: str = "text1.txt",
    name2: str = "text2.txt",
    save_to_db: bool = True,
    db: Session = Depends(get_db)
):
    result = compare_files(text1, text2)
    html_diff = generate_html_diff(text1, text2)

    if save_to_db:
        comparison = FileComparison(
            file1_name=name1,
            file2_name=name2,
            file1_content=text1,
            file2_content=text2,
            diff_result=json.dumps(result, ensure_ascii=False)
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        result_id = comparison.id
    else:
        result_id = None

    return {
        "success": True,
        "comparison_id": result_id,
        "file1": {"name": name1, "lines": result['stats']['total_lines1']},
        "file2": {"name": name2, "lines": result['stats']['total_lines2']},
        "stats": result['stats'],
        "diff": result['diff'],
        "html_diff": html_diff
    }


@app.get("/api/comparisons", response_model=List[ComparisonResponse])
async def get_comparisons(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    comparisons = db.query(FileComparison).offset(skip).limit(limit).all()
    results = []
    for comp in comparisons:
        diff_data = json.loads(comp.diff_result)
        results.append({
            "id": comp.id,
            "file1_name": comp.file1_name,
            "file2_name": comp.file2_name,
            "created_at": comp.created_at.isoformat() if comp.created_at else None,
            "stats": diff_data.get("stats", {})
        })
    return results


@app.get("/api/comparisons/{comparison_id}", response_model=dict)
async def get_comparison_detail(
    comparison_id: int,
    db: Session = Depends(get_db)
):
    comparison = db.query(FileComparison).filter(FileComparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    diff_data = json.loads(comparison.diff_result)
    html_diff = generate_html_diff(comparison.file1_content, comparison.file2_content)

    return {
        "success": True,
        "id": comparison.id,
        "file1_name": comparison.file1_name,
        "file2_name": comparison.file2_name,
        "file1_content": comparison.file1_content,
        "file2_content": comparison.file2_content,
        "created_at": comparison.created_at.isoformat() if comparison.created_at else None,
        "stats": diff_data.get("stats", {}),
        "diff": diff_data.get("diff", []),
        "html_diff": html_diff
    }


@app.delete("/api/comparisons/{comparison_id}")
async def delete_comparison(
    comparison_id: int,
    db: Session = Depends(get_db)
):
    comparison = db.query(FileComparison).filter(FileComparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    db.delete(comparison)
    db.commit()
    return {"success": True, "message": f"Comparison {comparison_id} deleted"}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>File Diff Comparison Tool</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .container { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .info-box { background: #e7f3ff; border-left: 4px solid #2196F3; padding: 12px 16px; margin: 15px 0; border-radius: 0 4px 4px 0; }
            .error-box { background: #ffebee; border-left: 4px solid #f44336; padding: 12px 16px; margin: 15px 0; border-radius: 0 4px 4px 0; display: none; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="file"] { padding: 10px; width: 100%; box-sizing: border-box; }
            button { background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .result { margin-top: 20px; padding: 15px; background: #fff; border-radius: 4px; }
            .stats { background: #e9ecef; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .stat-item { margin: 5px 0; }
            .file-label { display: flex; justify-content: space-between; align-items: center; }
            .file-status { font-size: 14px; font-weight: normal; }
            .file-valid { color: #4CAF50; }
            .file-invalid { color: #f44336; }
        </style>
    </head>
    <body>
        <h1>📄 File Diff Comparison Tool</h1>
        
        <div class="info-box">
            <strong>📝 提示：</strong>此工具仅支持对比文本文件。图片、音频、视频、压缩包等二进制文件将被拒绝。
            <br>支持的格式包括：.txt, .py, .js, .json, .html, .css, .md, .xml, .yaml, .sql 等文本格式。
        </div>

        <div class="container">
            <h2>上传两个文件进行对比</h2>
            <form id="compareForm" enctype="multipart/form-data">
                <div class="form-group">
                    <div class="file-label">
                        <label for="file1">文件 1：</label>
                        <span id="file1-status" class="file-status"></span>
                    </div>
                    <input type="file" id="file1" name="file1" required>
                </div>
                <div class="form-group">
                    <div class="file-label">
                        <label for="file2">文件 2：</label>
                        <span id="file2-status" class="file-status"></span>
                    </div>
                    <input type="file" id="file2" name="file2" required>
                </div>
                <div id="error-box" class="error-box"></div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="save_to_db" name="save_to_db" checked>
                        保存对比记录到数据库
                    </label>
                </div>
                <button type="submit" id="submit-btn">对比文件</button>
            </form>
        </div>

        <div id="result" class="result" style="display: none;">
            <h2>对比结果</h2>
            <div id="stats" class="stats"></div>
            <h3>差异视图：</h3>
            <div id="diffView"></div>
        </div>

        <script>
            const BINARY_EXTENSIONS = new Set([
                '.exe', '.dll', '.so', '.dylib', '.bin',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico',
                '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv', '.flv',
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.odt', '.ods', '.odp',
                '.class', '.jar', '.war', '.ear',
                '.iso', '.img', '.dmg',
                '.deb', '.rpm', '.msi'
            ]);

            const TEXT_EXTENSIONS = new Set([
                '.txt', '.text', '.log', '.csv', '.tsv',
                '.py', '.js', '.ts', '.jsx', '.tsx', '.json',
                '.java', '.kt', '.scala', '.groovy',
                '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
                '.cs', '.vb', '.fs',
                '.go', '.rs', '.swift',
                '.rb', '.php', '.perl', '.pl', '.pm',
                '.sh', '.bash', '.zsh', '.fish',
                '.sql', '.sqlite', '.mysql', '.pgsql',
                '.html', '.htm', '.css', '.scss', '.sass', '.less',
                '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
                '.md', '.markdown', '.rst',
                '.bat', '.cmd', '.ps1',
                '.lua', '.r', '.dart', '.kotlin',
                '.tf', '.hcl', '.dockerfile',
                '.env', '.gitignore'
            ]);

            function getFileExtension(filename) {
                const match = filename.match(/\.[^.]+$/);
                return match ? match[0].toLowerCase() : '';
            }

            function checkBinaryByExtension(filename) {
                const ext = getFileExtension(filename);
                if (BINARY_EXTENSIONS.has(ext)) {
                    return { isBinary: true, reason: `文件扩展名 ${ext} 是二进制文件格式` };
                }
                if (TEXT_EXTENSIONS.has(ext)) {
                    return { isBinary: false, reason: `文件扩展名 ${ext} 是文本文件格式` };
                }
                return { isBinary: null, reason: '未知扩展名，需要检查文件内容' };
            }

            function isBinaryContent(buffer) {
                const sampleSize = Math.min(8192, buffer.length);
                let controlChars = 0;
                
                for (let i = 0; i < sampleSize; i++) {
                    const byte = buffer[i];
                    if (byte === 0) {
                        return { isBinary: true, reason: '文件包含空字节 (null byte)，可能是二进制文件' };
                    }
                    if ((byte < 32 && byte !== 9 && byte !== 10 && byte !== 13) || byte === 127) {
                        controlChars++;
                    }
                }
                
                if (sampleSize > 0) {
                    const controlRatio = controlChars / sampleSize;
                    if (controlRatio > 0.3) {
                        return { isBinary: true, reason: `文件包含 ${(controlRatio * 100).toFixed(1)}% 的控制字符，可能是二进制文件` };
                    }
                }
                
                return { isBinary: false, reason: '文件内容看起来是文本' };
            }

            async function validateFile(fileInput, statusElement) {
                if (!fileInput.files || fileInput.files.length === 0) {
                    statusElement.textContent = '';
                    statusElement.className = 'file-status';
                    return { valid: false, reason: '未选择文件' };
                }

                const file = fileInput.files[0];
                const extCheck = checkBinaryByExtension(file.name);

                if (extCheck.isBinary === true) {
                    statusElement.textContent = '❌ ' + extCheck.reason;
                    statusElement.className = 'file-status file-invalid';
                    return { valid: false, reason: extCheck.reason };
                }

                if (extCheck.isBinary === false) {
                    statusElement.textContent = '✓ ' + extCheck.reason;
                    statusElement.className = 'file-status file-valid';
                    return { valid: true, reason: extCheck.reason };
                }

                statusElement.textContent = '⏳ 检查文件内容...';
                statusElement.className = 'file-status';

                const reader = new FileReader();
                
                return new Promise((resolve) => {
                    reader.onload = function(e) {
                        const buffer = new Uint8Array(e.target.result);
                        const contentCheck = isBinaryContent(buffer);

                        if (contentCheck.isBinary) {
                            statusElement.textContent = '❌ ' + contentCheck.reason;
                            statusElement.className = 'file-status file-invalid';
                            resolve({ valid: false, reason: contentCheck.reason });
                        } else {
                            statusElement.textContent = '✓ ' + contentCheck.reason;
                            statusElement.className = 'file-status file-valid';
                            resolve({ valid: true, reason: contentCheck.reason });
                        }
                    };
                    reader.onerror = function() {
                        statusElement.textContent = '❌ 无法读取文件';
                        statusElement.className = 'file-status file-invalid';
                        resolve({ valid: false, reason: '无法读取文件' });
                    };
                    reader.readAsArrayBuffer(file);
                });
            }

            const file1Input = document.getElementById('file1');
            const file2Input = document.getElementById('file2');
            const file1Status = document.getElementById('file1-status');
            const file2Status = document.getElementById('file2-status');
            const errorBox = document.getElementById('error-box');
            const submitBtn = document.getElementById('submit-btn');

            let file1Valid = false;
            let file2Valid = false;

            file1Input.addEventListener('change', async () => {
                const result = await validateFile(file1Input, file1Status);
                file1Valid = result.valid;
                updateSubmitButton();
            });

            file2Input.addEventListener('change', async () => {
                const result = await validateFile(file2Input, file2Status);
                file2Valid = result.valid;
                updateSubmitButton();
            });

            function updateSubmitButton() {
                submitBtn.disabled = !(file1Valid && file2Valid);
                if (!submitBtn.disabled) {
                    errorBox.style.display = 'none';
                }
            }

            document.getElementById('compareForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                if (!file1Valid || !file2Valid) {
                    errorBox.innerHTML = '<strong>❌ 错误：</strong>请选择有效的文本文件进行对比';
                    errorBox.style.display = 'block';
                    return;
                }

                const formData = new FormData();
                formData.append('file1', file1Input.files[0]);
                formData.append('file2', file2Input.files[0]);
                
                const saveToDb = document.getElementById('save_to_db').checked;
                
                submitBtn.disabled = true;
                submitBtn.textContent = '处理中...';
                errorBox.style.display = 'none';
                
                try {
                    const response = await fetch('/api/compare?save_to_db=' + saveToDb, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        document.getElementById('result').style.display = 'block';
                        
                        const statsHtml = `
                            <div class="stat-item"><strong>文件 1：</strong>${result.file1.name} (${result.file1.lines} 行)</div>
                            <div class="stat-item"><strong>文件 2：</strong>${result.file2.name} (${result.file2.lines} 行)</div>
                            <div class="stat-item"><strong>新增行数：</strong>${result.stats.inserted}</div>
                            <div class="stat-item"><strong>删除行数：</strong>${result.stats.deleted}</div>
                            <div class="stat-item"><strong>相同行数：</strong>${result.stats.equal}</div>
                            <div class="stat-item"><strong>相似度：</strong>${result.stats.similarity}%</div>
                            ${result.comparison_id ? '<div class="stat-item"><strong>对比记录 ID：</strong>' + result.comparison_id + '</div>' : ''}
                        `;
                        document.getElementById('stats').innerHTML = statsHtml;
                        
                        let diffHtml = '<pre style="white-space: pre-wrap; background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; font-size: 14px; line-height: 1.5;">';
                        result.diff.forEach(item => {
                            const lineNum1 = item.line_num1 ? item.line_num1.toString().padStart(4, ' ') : '    ';
                            const lineNum2 = item.line_num2 ? item.line_num2.toString().padStart(4, ' ') : '    ';
                            if (item.type === 'equal') {
                                diffHtml += `<span style="color: #ccc;">${lineNum1} ${lineNum2}   ${escapeHtml(item.content)}</span>\n`;
                            } else if (item.type === 'insert') {
                                diffHtml += `<span style="color: #a6e22e;">     ${lineNum2} + ${escapeHtml(item.content)}</span>\n`;
                            } else if (item.type === 'delete') {
                                diffHtml += `<span style="color: #f92672;">${lineNum1}      - ${escapeHtml(item.content)}</span>\n`;
                            }
                        });
                        diffHtml += '</pre>';
                        document.getElementById('diffView').innerHTML = diffHtml;
                        
                        document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
                    } else {
                        errorBox.innerHTML = '<strong>❌ 对比失败：</strong>' + (result.detail || '未知错误');
                        errorBox.style.display = 'block';
                    }
                } catch (error) {
                    errorBox.innerHTML = '<strong>❌ 错误：</strong>' + error.message;
                    errorBox.style.display = 'block';
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '对比文件';
                }
            });
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3333)
