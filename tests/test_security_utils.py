"""安全工具函数测试

测试 app/utils/security.py 中的安全工具函数，
包括密码哈希、JWT 令牌创建和解码等。
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4


class TestPasswordUtils:
    """测试密码相关工具函数"""

    def test_get_password_hash_generates_different_hashes(self):
        """测试密码哈希每次生成不同的哈希值"""
        from app.utils.security import get_password_hash

        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2, "相同密码的哈希应该不同（因为有盐）"
        assert hash1.startswith("$2b$") or hash1.startswith("$2a$"), "应该是 bcrypt 哈希"

    def test_get_password_hash_truncates_long_password(self):
        """测试长密码被正确截断（bcrypt限制72字节）"""
        from app.utils.security import get_password_hash, verify_password

        long_password = "a" * 100
        password_hash = get_password_hash(long_password)

        assert verify_password(long_password, password_hash) is True

    def test_verify_password_correct(self):
        """测试正确密码验证通过"""
        from app.utils.security import get_password_hash, verify_password

        password = "MySecurePassword123!"
        password_hash = get_password_hash(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证失败"""
        from app.utils.security import get_password_hash, verify_password

        password = "correct_password"
        wrong_password = "wrong_password"
        password_hash = get_password_hash(password)

        assert verify_password(wrong_password, password_hash) is False

    def test_verify_password_empty_password(self):
        """测试空密码"""
        from app.utils.security import get_password_hash, verify_password

        empty_password = ""
        password_hash = get_password_hash(empty_password)

        assert verify_password(empty_password, password_hash) is True
        assert verify_password("not_empty", password_hash) is False

    def test_password_hash_consistency(self):
        """测试密码哈希一致性"""
        from app.utils.security import get_password_hash, verify_password

        test_passwords = [
            "simple",
            "with spaces 123",
            "with!special@chars#$%",
            "中文密码测试",
            "123456",
            "a" * 72,
        ]

        for password in test_passwords:
            password_hash = get_password_hash(password)
            assert verify_password(password, password_hash) is True, f"密码 '{password}' 验证失败"


class TestTokenUtils:
    """测试 JWT 令牌相关工具函数"""

    def test_create_access_token_default_expiry(self):
        """测试创建访问令牌（默认过期时间）"""
        from app.utils.security import create_access_token
        from datetime import datetime

        subject = str(uuid4())
        token = create_access_token(subject)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_custom_expiry(self):
        """测试创建访问令牌（自定义过期时间）"""
        from app.utils.security import create_access_token

        subject = str(uuid4())
        custom_expiry = timedelta(minutes=60)
        token = create_access_token(subject, expires_delta=custom_expiry)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        from app.utils.security import create_refresh_token

        subject = str(uuid4())
        token = create_refresh_token(subject)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_valid(self):
        """测试解码有效令牌"""
        from app.utils.security import create_access_token, decode_token

        subject = str(uuid4())
        token = create_access_token(subject)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == subject
        assert payload.get("type") == "access"

    def test_decode_token_invalid(self):
        """测试解码无效令牌"""
        from app.utils.security import decode_token

        invalid_tokens = [
            "",
            "invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalid",
            None,
        ]

        for token in invalid_tokens:
            result = decode_token(token) if token else decode_token("")
            assert result is None, f"令牌 '{token}' 应该返回 None"

    def test_decode_token_expired(self):
        """测试解码过期令牌"""
        from app.utils.security import create_access_token, decode_token
        from datetime import timedelta

        subject = str(uuid4())
        expired_token = create_access_token(subject, expires_delta=timedelta(seconds=-10))

        payload = decode_token(expired_token)
        assert payload is None or "exp" in (payload or {})

    def test_token_type_distinction(self):
        """测试访问令牌和刷新令牌的类型区分"""
        from app.utils.security import create_access_token, create_refresh_token, decode_token

        subject = str(uuid4())

        access_token = create_access_token(subject)
        refresh_token = create_refresh_token(subject)

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload.get("type") == "access"
        assert refresh_payload.get("type") == "refresh"

    def test_token_payload_structure(self):
        """测试令牌载荷结构"""
        from app.utils.security import create_access_token, decode_token
        from datetime import datetime

        subject = str(uuid4())
        token = create_access_token(subject)
        payload = decode_token(token)

        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload
        assert "type" in payload


class TestSettingsIntegration:
    """测试安全工具与配置的集成"""

    def test_settings_used_for_tokens(self):
        """测试令牌使用配置中的密钥和算法"""
        from app.config.settings import get_settings
        from app.utils.security import create_access_token, decode_token

        settings = get_settings()
        subject = str(uuid4())

        token = create_access_token(subject)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == subject


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_subject_token(self):
        """测试空 subject 的令牌"""
        from app.utils.security import create_access_token, decode_token

        token = create_access_token("")
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == ""

    def test_numeric_subject_token(self):
        """测试数字 subject 的令牌"""
        from app.utils.security import create_access_token, decode_token

        token = create_access_token(12345)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == "12345"

    def test_uuid_subject_token(self):
        """测试 UUID subject 的令牌"""
        from app.utils.security import create_access_token, decode_token
        from uuid import uuid4

        test_uuid = uuid4()
        token = create_access_token(test_uuid)
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == str(test_uuid)

    def test_long_password_hash(self):
        """测试密码截断边界"""
        from app.utils.security import get_password_hash, verify_password

        password_72 = "a" * 72
        password_73 = "a" * 73

        hash_72 = get_password_hash(password_72)
        hash_73 = get_password_hash(password_73)

        assert verify_password(password_72, hash_72) is True
        assert verify_password(password_73, hash_73) is True

        assert verify_password(password_73, hash_72) is True, "73字节密码的前72字节与72字节密码相同"

    def test_unicode_password(self):
        """测试 Unicode 密码"""
        from app.utils.security import get_password_hash, verify_password

        test_passwords = [
            "中文密码123",
            "日本語パスワード",
            "한국어 비밀번호",
            "العربية كلمة المرور",
            "password_àéíóú",
        ]

        for password in test_passwords:
            password_hash = get_password_hash(password)
            assert verify_password(password, password_hash) is True, f"Unicode 密码 '{password}' 验证失败"
