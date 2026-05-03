#!/usr/bin/env python3
"""测试文件验证器"""

from file_validator import (
    validate_uploaded_file,
    is_text_file_by_extension,
    is_binary_content,
    get_supported_extensions,
    ALLOWED_TEXT_EXTENSIONS,
    BINARY_EXTENSIONS
)


def test_extension_check():
    print("=" * 50)
    print("测试扩展名检查")
    print("=" * 50)
    
    test_cases = [
        ("document.txt", True, "文本文件"),
        ("script.py", True, "Python 脚本"),
        ("styles.css", True, "CSS 文件"),
        ("data.json", True, "JSON 文件"),
        ("image.jpg", False, "JPEG 图片"),
        ("video.mp4", False, "MP4 视频"),
        ("archive.zip", False, "ZIP 压缩包"),
        ("document.pdf", False, "PDF 文件"),
        ("unknown.xyz", True, "未知扩展名（将检查内容）"),
        ("Makefile", True, "无扩展名的 Makefile"),
    ]
    
    for filename, expected_valid, description in test_cases:
        is_allowed, message = is_text_file_by_extension(filename)
        status = "✓" if is_allowed == expected_valid else "✗"
        print(f"{status} {description} ({filename}): {message}")
    
    print()


def test_binary_content_detection():
    print("=" * 50)
    print("测试二进制内容检测")
    print("=" * 50)
    
    test_cases = [
        (b"Hello, world!\nThis is a text file.", False, "纯文本"),
        (b"# Python script\nprint('Hello')", False, "Python 代码"),
        (b"\x00\x01\x02\x03\x04\x05", True, "包含空字节的二进制"),
        (
            bytes([255, 216, 255]) + b"JFIF" + bytes(range(256)),
            True,
            "类似 JPEG 头部的二进制"
        ),
        (
            b"<?xml version='1.0'?>\n<root>Text content</root>",
            False,
            "XML 文本"
        ),
    ]
    
    for content, expected_binary, description in test_cases:
        is_binary, message = is_binary_content(content)
        status = "✓" if is_binary == expected_binary else "✗"
        print(f"{status} {description}: is_binary={is_binary}, {message}")
    
    print()


def test_validate_uploaded_file():
    print("=" * 50)
    print("测试完整文件验证")
    print("=" * 50)
    
    test_cases = [
        ("test.txt", b"Hello, this is a test file.", True, "文本文件"),
        ("image.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF", False, "JPEG 二进制（扩展名检测）"),
        ("unknown.bin", b"\x00\x01\x02\x03", False, "二进制内容（内容检测）"),
        ("script.py", b"# -*- coding: utf-8 -*-\nprint('Hello')", True, "Python 脚本"),
        (
            "data.json",
            b'{"name": "test", "value": 123}',
            True,
            "JSON 文件"
        ),
    ]
    
    for filename, content, expected_valid, description in test_cases:
        is_valid, message = validate_uploaded_file(filename, content)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description} ({filename}): valid={is_valid}, {message}")
    
    print()


def test_supported_extensions():
    print("=" * 50)
    print("支持的文本文件扩展名")
    print("=" * 50)
    
    extensions = get_supported_extensions()
    print(f"共支持 {len(extensions)} 种文本文件扩展名：")
    print(", ".join(extensions[:30]) + "..." if len(extensions) > 30 else ", ".join(extensions))
    print()
    
    print(f"被拒绝的二进制扩展名（{len(BINARY_EXTENSIONS)} 种）：")
    print(", ".join(sorted(BINARY_EXTENSIONS)))
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("文件验证器测试套件")
    print("=" * 50)
    print()
    
    test_extension_check()
    test_binary_content_detection()
    test_validate_uploaded_file()
    test_supported_extensions()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)
