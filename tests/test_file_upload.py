import os
import tempfile
import shutil
import asyncio
import json
from pathlib import Path
from datetime import datetime
import pytest
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3333"


@pytest.fixture(scope="module")
def temp_test_dir():
    test_dir = tempfile.mkdtemp(prefix="clipboard_test_")
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def test_files(temp_test_dir):
    files_info = {}
    
    file1 = Path(temp_test_dir) / "file1.txt"
    file1.write_text("Hello, this is file 1 content.")
    files_info["file1.txt"] = {"path": str(file1), "content": "Hello, this is file 1 content."}
    
    file2 = Path(temp_test_dir) / "file2.txt"
    file2.write_text("This is file 2 with different content.")
    files_info["file2.txt"] = {"path": str(file2), "content": "This is file 2 with different content."}
    
    return files_info


@pytest.fixture(scope="module")
def test_folder(temp_test_dir):
    folder_path = Path(temp_test_dir) / "test_folder"
    folder_path.mkdir()
    
    subfolder = folder_path / "subfolder"
    subfolder.mkdir()
    
    deep_folder = subfolder / "deep"
    deep_folder.mkdir()
    
    file_a = folder_path / "a.txt"
    file_a.write_text("Content of a.txt in root folder")
    
    file_b = subfolder / "b.txt"
    file_b.write_text("Content of b.txt in subfolder")
    
    file_c = folder_path / "c.txt"
    file_c.write_text("Content of c.txt")
    
    file_d = deep_folder / "d.txt"
    file_d.write_text("Content of d.txt in deep folder")
    
    return {
        "root": str(folder_path),
        "files": {
            "test_folder/a.txt": str(file_a),
            "test_folder/subfolder/b.txt": str(file_b),
            "test_folder/c.txt": str(file_c),
            "test_folder/subfolder/deep/d.txt": str(file_d)
        }
    }


@pytest.mark.asyncio
async def test_multi_file_upload():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            
            await page.click('button.tab:has-text("文件")')
            
            file_input = page.locator('#file-input')
            
            test_dir = tempfile.mkdtemp()
            try:
                file1 = Path(test_dir) / "test1.txt"
                file1.write_text("Test file 1 content")
                file2 = Path(test_dir) / "test2.txt"
                file2.write_text("Test file 2 content")
                
                await file_input.set_input_files([str(file1), str(file2)])
                
                await page.select_option('#file-expire', '1')
                
                async with page.expect_response(
                    lambda resp: '/api/file' in resp.url and resp.request.method == 'POST'
                ) as response_info:
                    await page.click('button.btn:has-text("保存文件")')
                
                response = await response_info.value
                assert response.ok, f"Upload failed: {response.status}"
                
                data = await response.json()
                assert "id" in data
                assert data["type"] == "file"
                assert data["file_count"] == 2
                
                item_id = data["id"]
                
                await page.fill('#retrieve-id', item_id)
                
                async with page.expect_response(
                    lambda resp: f'/api/{item_id}' in resp.url
                ) as retrieve_info:
                    await page.click('button:has-text("提取")')
                
                retrieve_response = await retrieve_info.value
                assert retrieve_response.ok
                
                retrieve_data = await retrieve_response.json()
                assert retrieve_data["file_count"] == 2
                assert len(retrieve_data["files"]) == 2
                
                filenames = [f["filename"] for f in retrieve_data["files"]]
                assert "test1.txt" in filenames
                assert "test2.txt" in filenames
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_single_file_upload():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            
            await page.click('button.tab:has-text("文件")')
            
            file_input = page.locator('#file-input')
            
            test_dir = tempfile.mkdtemp()
            try:
                test_file = Path(test_dir) / "single_test.txt"
                test_file.write_text("Single file test content")
                
                await file_input.set_input_files(str(test_file))
                
                await page.select_option('#file-expire', '1')
                
                async with page.expect_response(
                    lambda resp: '/api/file' in resp.url and resp.request.method == 'POST'
                ) as response_info:
                    await page.click('button.btn:has-text("保存文件")')
                
                response = await response_info.value
                assert response.ok, f"Upload failed: {response.status}"
                
                data = await response.json()
                assert "id" in data
                assert data["type"] == "file"
                assert data["file_count"] == 1
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_text_save_and_retrieve():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            
            test_content = f"Test content at {datetime.now()}"
            await page.fill('#text-content', test_content)
            
            await page.select_option('#text-expire', '1')
            
            async with page.expect_response(
                lambda resp: '/api/text' in resp.url and resp.request.method == 'POST'
            ) as response_info:
                await page.click('button.btn:has-text("保存文本")')
            
            response = await response_info.value
            assert response.ok
            
            data = await response.json()
            assert "id" in data
            item_id = data["id"]
            
            await page.fill('#retrieve-id', item_id)
            
            async with page.expect_response(
                lambda resp: f'/api/{item_id}' in resp.url
            ) as retrieve_info:
                await page.click('button:has-text("提取")')
            
            retrieve_response = await retrieve_info.value
            assert retrieve_response.ok
            
            retrieve_data = await retrieve_response.json()
            assert retrieve_data["type"] == "text"
            assert retrieve_data["content"] == test_content
        
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_file_download():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True
        )
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            
            await page.click('button.tab:has-text("文件")')
            
            file_input = page.locator('#file-input')
            
            test_dir = tempfile.mkdtemp()
            try:
                test_file = Path(test_dir) / "download_test.txt"
                test_content = "Download test content"
                test_file.write_text(test_content)
                
                await file_input.set_input_files(str(test_file))
                
                async with page.expect_response(
                    lambda resp: '/api/file' in resp.url and resp.request.method == 'POST'
                ) as response_info:
                    await page.click('button.btn:has-text("保存文件")')
                
                response = await response_info.value
                data = await response.json()
                item_id = data["id"]
                
                await page.fill('#retrieve-id', item_id)
                await page.click('button:has-text("提取")')
                
                await page.wait_for_selector('#download-link', timeout=5000)
                
                async with page.expect_download() as download_info:
                    await page.click('#download-link')
                
                download = await download_info.value
                assert download.suggested_filename == "download_test.txt"
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_file_list_shows_relative_paths():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            
            test_dir = tempfile.mkdtemp()
            try:
                folder = Path(test_dir) / "myfolder"
                folder.mkdir()
                subfolder = folder / "sub"
                subfolder.mkdir()
                
                file1 = folder / "file1.txt"
                file1.write_text("File 1 content")
                
                file2 = subfolder / "file2.txt"
                file2.write_text("File 2 content")
                
                relative_paths = json.dumps([
                    "myfolder/file1.txt",
                    "myfolder/sub/file2.txt"
                ])
                
                upload_js = f"""
                (async () => {{
                    const formData = new FormData();
                    
                    const file1 = new File(['File 1 content'], 'file1.txt', {{ type: 'text/plain' }});
                    const file2 = new File(['File 2 content'], 'file2.txt', {{ type: 'text/plain' }});
                    
                    formData.append('files', file1);
                    formData.append('files', file2);
                    formData.append('expires_hours', '1');
                    formData.append('relative_paths', {json.dumps(relative_paths)});
                    
                    const response = await fetch('/api/file', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    return await response.json();
                }})();
                """
                
                result = await page.evaluate(upload_js)
                
                assert "id" in result, f"Upload failed: {result}"
                assert result["type"] == "file"
                assert result["file_count"] == 2
                
                item_id = result["id"]
                
                retrieve_js = f"""
                (async () => {{
                    const response = await fetch('/api/{item_id}');
                    return await response.json();
                }})();
                """
                
                retrieve_result = await page.evaluate(retrieve_js)
                
                assert retrieve_result["file_count"] == 2
                assert len(retrieve_result["files"]) == 2
                
                original_paths = [f["original_path"] for f in retrieve_result["files"]]
                assert "myfolder/file1.txt" in original_paths, f"Paths: {original_paths}"
                assert "myfolder/sub/file2.txt" in original_paths, f"Paths: {original_paths}"
                
                print(f"✓ 相对路径存储测试成功！存储的路径：{original_paths}")
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_recursive_folder_upload_simulation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        test_dir = tempfile.mkdtemp()
        try:
            folder = Path(test_dir) / "upload_folder"
            folder.mkdir()
            
            subfolder = folder / "sub"
            subfolder.mkdir()
            
            deep_folder = subfolder / "deep"
            deep_folder.mkdir()
            
            file1 = folder / "root_file.txt"
            file1.write_text("Root file content")
            
            file2 = subfolder / "sub_file.txt"
            file2.write_text("Subfolder file content")
            
            file3 = deep_folder / "deep_file.txt"
            file3.write_text("Deep folder file content")
            
            relative_paths = json.dumps([
                "upload_folder/root_file.txt",
                "upload_folder/sub/sub_file.txt",
                "upload_folder/sub/deep/deep_file.txt"
            ])
            
            upload_js = f"""
            (async () => {{
                const formData = new FormData();
                
                const file1 = new File(['Root file content'], 'root_file.txt', {{ type: 'text/plain' }});
                const file2 = new File(['Subfolder file content'], 'sub_file.txt', {{ type: 'text/plain' }});
                const file3 = new File(['Deep folder file content'], 'deep_file.txt', {{ type: 'text/plain' }});
                
                formData.append('files', file1);
                formData.append('files', file2);
                formData.append('files', file3);
                formData.append('expires_hours', '1');
                formData.append('relative_paths', {json.dumps(relative_paths)});
                
                const response = await fetch('/api/file', {{
                    method: 'POST',
                    body: formData
                }});
                
                return await response.json();
            }})();
            """
            
            await page.goto(BASE_URL)
            
            result = await page.evaluate(upload_js)
            
            assert "id" in result, f"Upload failed: {result}"
            assert result["type"] == "file"
            assert result["file_count"] == 3, f"Expected 3 files, got {result['file_count']}"
            
            item_id = result["id"]
            
            retrieve_js = f"""
            (async () => {{
                const response = await fetch('/api/{item_id}');
                return await response.json();
            }})();
            """
            
            retrieve_result = await page.evaluate(retrieve_js)
            
            assert retrieve_result["file_count"] == 3
            assert len(retrieve_result["files"]) == 3
            
            original_paths = [f["original_path"] for f in retrieve_result["files"]]
            
            assert "upload_folder/root_file.txt" in original_paths, f"Paths: {original_paths}"
            assert "upload_folder/sub/sub_file.txt" in original_paths, f"Paths: {original_paths}"
            assert "upload_folder/sub/deep/deep_file.txt" in original_paths, f"Paths: {original_paths}"
            
            print(f"✓ 文件夹递归上传测试成功！上传了 {len(original_paths)} 个文件：")
            for path in sorted(original_paths):
                print(f"  - {path}")
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
            await browser.close()
