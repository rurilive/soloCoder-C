"""文件处理工具测试

测试 app/utils/file_handler.py 中的文件上传和处理工具。
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO


class TestFileHandlerImports:
    """测试文件处理工具可导入"""

    def test_import_file_handler(self):
        """测试导入文件处理模块"""
        from app.utils.file_handler import (
            save_image,
            save_video,
            save_avatar,
            get_file_url,
            allowed_file,
            allowed_image_file,
            allowed_video_file,
            allowed_avatar_file,
            get_file_info,
        )

        assert save_image is not None
        assert save_video is not None
        assert save_avatar is not None
        assert get_file_url is not None
        assert allowed_file is not None
        assert allowed_image_file is not None
        assert allowed_video_file is not None
        assert allowed_avatar_file is not None
        assert get_file_info is not None


class TestAllowedFileFunctions:
    """测试文件类型验证函数"""

    def test_allowed_file(self):
        """测试通用文件允许函数"""
        from app.utils.file_handler import allowed_file

        allowed_extensions = {"jpg", "png", "gif"}

        assert allowed_file("test.jpg", allowed_extensions) is True
        assert allowed_file("test.JPG", allowed_extensions) is True
        assert allowed_file("test.PNG", allowed_extensions) is True
        assert allowed_file("test.png", allowed_extensions) is True

        assert allowed_file("test.txt", allowed_extensions) is False
        assert allowed_file("test.exe", allowed_extensions) is False
        assert allowed_file("test", allowed_extensions) is False

    def test_allowed_image_file(self):
        """测试图片文件允许函数"""
        from app.utils.file_handler import allowed_image_file

        valid_images = [
            "photo.jpg",
            "image.JPG",
            "picture.png",
            "photo.PNG",
            "animation.gif",
            "image.webp",
            "test.JPEG",
        ]

        invalid_files = [
            "document.txt",
            "video.mp4",
            "program.exe",
            "archive.zip",
        ]

        for filename in valid_images:
            assert allowed_image_file(filename) is True, f"{filename} 应该被允许"

        for filename in invalid_files:
            assert allowed_image_file(filename) is False, f"{filename} 不应该被允许"

    def test_allowed_video_file(self):
        """测试视频文件允许函数"""
        from app.utils.file_handler import allowed_video_file

        valid_videos = [
            "movie.mp4",
            "clip.MP4",
            "video.avi",
            "clip.AVI",
            "movie.mov",
            "video.mkv",
            "clip.webm",
        ]

        invalid_files = [
            "photo.jpg",
            "document.txt",
            "program.exe",
        ]

        for filename in valid_videos:
            assert allowed_video_file(filename) is True, f"{filename} 应该被允许"

        for filename in invalid_files:
            assert allowed_video_file(filename) is False, f"{filename} 不应该被允许"

    def test_allowed_avatar_file(self):
        """测试头像文件允许函数"""
        from app.utils.file_handler import allowed_avatar_file

        valid_avatars = [
            "avatar.jpg",
            "profile.JPG",
            "user.png",
            "icon.PNG",
            "user.webp",
        ]

        invalid_files = [
            "animation.gif",
            "video.mp4",
            "document.txt",
        ]

        for filename in valid_avatars:
            assert allowed_avatar_file(filename) is True, f"{filename} 应该被允许"

        for filename in invalid_files:
            assert allowed_avatar_file(filename) is False, f"{filename} 不应该被允许"

    def test_edge_cases_filenames(self):
        """测试边界情况文件名"""
        from app.utils.file_handler import allowed_file

        allowed_extensions = {"jpg"}

        edge_cases = [
            ("test..jpg", True),
            ("test.test.jpg", True),
            ("test. jpg", False),
            ("test.jpg.bak", False),
            ("", False),
            ("  ", False),
        ]

        for filename, expected in edge_cases:
            result = allowed_file(filename, allowed_extensions)
            assert result == expected, f"文件名 '{filename}' 应该返回 {expected}，实际返回 {result}"


class TestGetFileUrl:
    """测试文件 URL 生成函数"""

    def test_get_file_url_default(self):
        """测试默认文件 URL"""
        from app.utils.file_handler import get_file_url

        filename = "abc123.jpg"
        url = get_file_url(filename)

        assert filename in url
        assert "/files/" in url

    def test_get_file_url_image_type(self):
        """测试图片类型文件 URL"""
        from app.utils.file_handler import get_file_url

        filename = "abc123.jpg"
        url = get_file_url(filename, file_type="image")

        assert filename in url

    def test_get_file_url_video_type(self):
        """测试视频类型文件 URL"""
        from app.utils.file_handler import get_file_url

        filename = "abc123.mp4"
        url = get_file_url(filename, file_type="video")

        assert filename in url

    def test_get_file_url_avatar_type(self):
        """测试头像类型文件 URL"""
        from app.utils.file_handler import get_file_url

        filename = "abc123.png"
        url = get_file_url(filename, file_type="avatar")

        assert filename in url


class TestGetFileInfo:
    """测试文件信息获取函数"""

    def test_get_file_info_basic(self):
        """测试基本文件信息"""
        from app.utils.file_handler import get_file_info

        result = get_file_info("test.jpg", 1024)

        assert result["filename"] == "test.jpg"
        assert result["size"] == 1024

    def test_get_file_info_formatted_size(self):
        """测试格式化文件大小"""
        from app.utils.file_handler import get_file_info

        test_cases = [
            (500, "500.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 2.5, "2.5 MB"),
        ]

        for size_bytes, expected_formatted in test_cases:
            result = get_file_info("test.jpg", size_bytes)
            assert result["formatted_size"] == expected_formatted, f"大小 {size_bytes} 应该返回 '{expected_formatted}'"

    def test_get_file_info_with_url(self):
        """测试包含 URL 的文件信息"""
        from app.utils.file_handler import get_file_info

        result = get_file_info("test.jpg", 1024, include_url=True)

        assert "url" in result
        assert "test.jpg" in result["url"]


class TestFileHandlerEdgeCases:
    """测试文件处理边界情况"""

    def test_filename_extraction(self):
        """测试文件名提取"""
        from app.utils.file_handler import allowed_file

        # 测试带路径的文件名
        allowed_extensions = {"jpg"}
        assert allowed_file("/path/to/test.jpg", allowed_extensions) is True
        assert allowed_file("folder/another/test.JPG", allowed_extensions) is True

    def test_empty_filename(self):
        """测试空文件名"""
        from app.utils.file_handler import allowed_file, allowed_image_file

        assert allowed_file("", {"jpg"}) is False
        assert allowed_file(".jpg", {"jpg"}) is True
        assert allowed_image_file(".png") is True

    def test_get_file_info_size_zero(self):
        """测试零大小文件"""
        from app.utils.file_handler import get_file_info

        result = get_file_info("empty.txt", 0)

        assert result["size"] == 0
        assert result["formatted_size"] == "0.0 B"


class TestFileHandlerIntegration:
    """测试文件处理与配置集成"""

    def test_config_used_for_allowed_types(self):
        """测试配置用于允许的文件类型"""
        from app.config.settings import get_settings
        from app.utils.file_handler import allowed_image_file, allowed_video_file

        settings = get_settings()

        # 验证配置中的类型与函数行为一致
        for ext in settings.allowed_image_types:
            filename = f"test.{ext}"
            assert allowed_image_file(filename) is True, f"扩展名 {ext} 应该被允许"

        for ext in settings.allowed_video_types:
            filename = f"test.{ext}"
            assert allowed_video_file(filename) is True, f"扩展名 {ext} 应该被允许"

    def test_max_file_size_config(self):
        """测试最大文件大小配置"""
        from app.config.settings import get_settings

        settings = get_settings()

        assert settings.max_file_size > 0
        assert isinstance(settings.max_file_size, int)


class TestUploadDirectories:
    """测试上传目录配置"""

    def test_upload_directories_configured(self):
        """测试上传目录已配置"""
        from app.config.settings import get_settings

        settings = get_settings()

        assert settings.upload_dir is not None
        assert settings.upload_image_dir is not None
        assert settings.upload_video_dir is not None
        assert settings.upload_avatar_dir is not None

    def test_upload_directory_relationships(self):
        """测试上传目录关系"""
        from app.config.settings import get_settings

        settings = get_settings()

        # 验证子目录包含父目录路径
        upload_path = str(settings.upload_dir)
        image_path = str(settings.upload_image_dir)
        video_path = str(settings.upload_video_dir)
        avatar_path = str(settings.upload_avatar_dir)

        assert upload_path in image_path
        assert upload_path in video_path
        assert upload_path in avatar_path
