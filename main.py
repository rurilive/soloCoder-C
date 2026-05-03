from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from typing import Optional, List
from pydantic import BaseModel

from database import get_db, init_db, FileComparison
from diff_utils import compare_files, generate_html_diff

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
    try:
        content1 = (await file1.read()).decode("utf-8")
        content2 = (await file2.read()).decode("utf-8")
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
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="file"] { padding: 10px; width: 100%; box-sizing: border-box; }
            button { background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 15px; background: #fff; border-radius: 4px; }
            .stats { background: #e9ecef; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .stat-item { margin: 5px 0; }
        </style>
    </head>
    <body>
        <h1>📄 File Diff Comparison Tool</h1>
        
        <div class="container">
            <h2>Upload Two Files to Compare</h2>
            <form id="compareForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="file1">File 1:</label>
                    <input type="file" id="file1" name="file1" required>
                </div>
                <div class="form-group">
                    <label for="file2">File 2:</label>
                    <input type="file" id="file2" name="file2" required>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="save_to_db" name="save_to_db" checked>
                        Save comparison to database
                    </label>
                </div>
                <button type="submit">Compare Files</button>
            </form>
        </div>

        <div id="result" class="result" style="display: none;">
            <h2>Comparison Result</h2>
            <div id="stats" class="stats"></div>
            <h3>Diff View:</h3>
            <div id="diffView"></div>
        </div>

        <script>
            document.getElementById('compareForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData();
                formData.append('file1', document.getElementById('file1').files[0]);
                formData.append('file2', document.getElementById('file2').files[0]);
                
                const saveToDb = document.getElementById('save_to_db').checked;
                
                try {
                    const response = await fetch('/api/compare?save_to_db=' + saveToDb, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('result').style.display = 'block';
                        
                        const statsHtml = `
                            <div class="stat-item"><strong>File 1:</strong> ${result.file1.name} (${result.file1.lines} lines)</div>
                            <div class="stat-item"><strong>File 2:</strong> ${result.file2.name} (${result.file2.lines} lines)</div>
                            <div class="stat-item"><strong>Inserted lines:</strong> ${result.stats.inserted}</div>
                            <div class="stat-item"><strong>Deleted lines:</strong> ${result.stats.deleted}</div>
                            <div class="stat-item"><strong>Equal lines:</strong> ${result.stats.equal}</div>
                            <div class="stat-item"><strong>Similarity:</strong> ${result.stats.similarity}%</div>
                            ${result.comparison_id ? '<div class="stat-item"><strong>Comparison ID:</strong> ' + result.comparison_id + '</div>' : ''}
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
                    } else {
                        alert('Comparison failed: ' + result.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
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
