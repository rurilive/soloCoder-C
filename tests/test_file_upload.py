import os
import tempfile
import shutil
import asyncio
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
    
    file_a = folder_path / "a.txt"
    file_a.write_text("Content of a.txt in root folder")
    
    file_b = subfolder / "b.txt"
    file_b.write_text("Content of b.txt in subfolder")
    
    file_c = folder_path / "c.txt"
    file_c.write_text("Content of c.txt")
    
    return {
        "root": str(folder_path),
        "files": {
            "a.txt": str(file_a),
            "subfolder/b.txt": str(file_b),
            "c.txt": str(file_c)
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
