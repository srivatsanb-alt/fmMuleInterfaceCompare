#!/usr/bin/env python3
"""
Unit tests for DualAuthValidator

Tests both Bearer token authentication and Basic Authentication functionality.
"""

import pytest
import os
import tempfile
import jwt
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasicCredentials

# Import the classes to test
from utils.auth_utils import DualAuthValidator, AuthValidator


class TestDualAuthValidator:
    """Test cases for DualAuthValidator class"""

    @pytest.fixture
    def dual_auth_validator(self):
        """Create a DualAuthValidator instance for testing"""
        return DualAuthValidator('fm')

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request"""
        request = Mock()
        request.path_params = {}
        return request

    @pytest.fixture
    def temp_password_file(self):
        """Create a temporary password file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            # Test credentials: ati_static_files:atiStatic112
            # This is the Apache MD5 hash for 'atiStatic112'
            f.write("ati_static_files:$apr1$8mpu.uQg$ehzez8yUBB5milwD7YMKP0\n")
            f.write("test_user:$apr1$test.salt$testhash\n")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_validate_basic_auth_with_correct_credentials(self, temp_password_file):
        """Test Basic Authentication with correct credentials"""
        # Test with the specific credentials provided
        username = "ati_static_files"
        password = "atiStatic112"
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': temp_password_file}):
            result = await DualAuthValidator._validate_basic_auth(username, password)
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_basic_auth_with_incorrect_password(self, temp_password_file):
        """Test Basic Authentication with incorrect password"""
        username = "ati_static_files"
        password = "wrong_password"
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': temp_password_file}):
            result = await DualAuthValidator._validate_basic_auth(username, password)
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_basic_auth_with_nonexistent_user(self, temp_password_file):
        """Test Basic Authentication with non-existent user"""
        username = "nonexistent_user"
        password = "any_password"
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': temp_password_file}):
            result = await DualAuthValidator._validate_basic_auth(username, password)
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_basic_auth_with_missing_password_file(self):
        """Test Basic Authentication when password file doesn't exist"""
        username = "ati_static_files"
        password = "atiStatic112"
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': '/nonexistent/file'}):
            result = await DualAuthValidator._validate_basic_auth(username, password)
            assert result is False

    def test_check_password_apache_md5(self):
        """Test password checking with Apache MD5 format"""
        password = "atiStatic112"
        stored_hash = "$apr1$8mpu.uQg$ehzez8yUBB5milwD7YMKP0"
        
        result = DualAuthValidator._check_password(password, stored_hash)
        assert result is True

    def test_check_password_apache_md5_wrong_password(self):
        """Test password checking with wrong password"""
        password = "wrong_password"
        stored_hash = "$apr1$8mpu.uQg$ehzez8yUBB5milwD7YMKP0"
        
        result = DualAuthValidator._check_password(password, stored_hash)
        assert result is False

    def test_check_password_plain_text(self):
        """Test password checking with plain text"""
        password = "test123"
        stored_hash = "test123"
        
        result = DualAuthValidator._check_password(password, stored_hash)
        assert result is True

    @pytest.mark.asyncio
    async def test_bearer_token_authentication_success(self, dual_auth_validator, mock_request):
        """Test successful Bearer token authentication"""
        # Mock JWT token
        token = "valid.jwt.token"
        
        # Mock Bearer credentials
        bearer_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Mock the bearer_auth to return credentials
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.return_value = bearer_credentials
        
        # Mock AuthValidator methods
        with patch.object(AuthValidator, 'valid_token', return_value=True), \
             patch.object(AuthValidator, 'get_user_model', return_value={'sub': 'test_user', 'role': 'user'}), \
             patch.object(AuthValidator, 'user_has_access_to_api', return_value=True):
            
            result = await dual_auth_validator(mock_request)
            
            assert result is not None
            assert result['sub'] == 'test_user'
            assert result['role'] == 'user'

    @pytest.mark.asyncio
    async def test_bearer_token_authentication_failure(self, dual_auth_validator, mock_request):
        """Test failed Bearer token authentication"""
        # Mock Bearer credentials
        bearer_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )
        
        # Mock the bearer_auth to return credentials
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.return_value = bearer_credentials
        
        # Mock the basic_auth to fail (no credentials)
        dual_auth_validator.basic_auth = AsyncMock()
        dual_auth_validator.basic_auth.side_effect = HTTPException(status_code=401)
        
        # Mock AuthValidator methods to fail
        with patch.object(AuthValidator, 'valid_token', return_value=False):
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await dual_auth_validator(mock_request)
            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_basic_auth_authentication_success(self, dual_auth_validator, mock_request, temp_password_file):
        """Test successful Basic Authentication"""
        # Mock Basic credentials
        basic_credentials = HTTPBasicCredentials(
            username="ati_static_files",
            password="atiStatic112"
        )
        
        # Mock the bearer_auth to fail (no credentials)
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.side_effect = HTTPException(status_code=401)
        
        # Mock the basic_auth to return credentials
        dual_auth_validator.basic_auth = AsyncMock()
        dual_auth_validator.basic_auth.return_value = basic_credentials
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': temp_password_file}):
            result = await dual_auth_validator(mock_request)
            
            assert result is not None
            assert result['sub'] == 'ati_static_files'
            assert result['role'] == 'static_access'
            assert result['auth_method'] == 'basic'

    @pytest.mark.asyncio
    async def test_basic_auth_authentication_failure(self, dual_auth_validator, mock_request, temp_password_file):
        """Test failed Basic Authentication"""
        # Mock Basic credentials with wrong password
        basic_credentials = HTTPBasicCredentials(
            username="ati_static_files",
            password="wrong_password"
        )
        
        # Mock the bearer_auth to fail (no credentials)
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.side_effect = HTTPException(status_code=401)
        
        # Mock the basic_auth to return credentials
        dual_auth_validator.basic_auth = AsyncMock()
        dual_auth_validator.basic_auth.return_value = basic_credentials
        
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': temp_password_file}):
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await dual_auth_validator(mock_request)
            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_both_auth_methods_fail(self, dual_auth_validator, mock_request):
        """Test when both authentication methods fail"""
        # Mock both auth methods to fail
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.side_effect = HTTPException(status_code=401)
        
        dual_auth_validator.basic_auth = AsyncMock()
        dual_auth_validator.basic_auth.side_effect = HTTPException(status_code=401)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await dual_auth_validator(mock_request)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_credentials_provided(self, dual_auth_validator, mock_request):
        """Test when no credentials are provided"""
        # Mock both auth methods to return None (no credentials)
        dual_auth_validator.bearer_auth = AsyncMock()
        dual_auth_validator.bearer_auth.return_value = None
        
        dual_auth_validator.basic_auth = AsyncMock()
        dual_auth_validator.basic_auth.return_value = None
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await dual_auth_validator(mock_request)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_auto_error_false(self):
        """Test DualAuthValidator with auto_error=False"""
        validator = DualAuthValidator('fm', auto_error=False)
        
        # Mock both auth methods to fail
        validator.bearer_auth = AsyncMock()
        validator.bearer_auth.side_effect = HTTPException(status_code=401)
        
        validator.basic_auth = AsyncMock()
        validator.basic_auth.side_effect = HTTPException(status_code=401)
        
        # Should return None instead of raising exception
        result = await validator(Mock())
        assert result is None


class TestIntegration:
    """Integration tests for the dual authentication system"""

    @pytest.fixture
    def real_password_file(self):
        """Create a real password file with the test credentials"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("ati_static_files:$apr1$8mpu.uQg$ehzez8yUBB5milwD7YMKP0\n")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_real_credentials_validation(self, real_password_file):
        """Test with the real credentials provided by the user"""
        with patch.dict(os.environ, {'STATIC_AUTH_FILE': real_password_file}):
            # Test the exact credentials provided
            result = await DualAuthValidator._validate_basic_auth("ati_static_files", "atiStatic112")
            assert result is True, "Real credentials should validate successfully"
            
            # Test with wrong password
            result = await DualAuthValidator._validate_basic_auth("ati_static_files", "wrong_password")
            assert result is False, "Wrong password should fail validation"
            
            # Test with wrong username
            result = await DualAuthValidator._validate_basic_auth("wrong_user", "atiStatic112")
            assert result is False, "Wrong username should fail validation"

    def test_password_hash_verification(self):
        """Test that the password hash verification works correctly"""
        # Test the specific hash provided
        password = "atiStatic112"
        stored_hash = "$apr1$8mpu.uQg$ehzez8yUBB5milwD7YMKP0"
        
        result = DualAuthValidator._check_password(password, stored_hash)
        assert result is True, "Password hash verification should succeed"
        
        # Test with wrong password
        result = DualAuthValidator._check_password("wrong_password", stored_hash)
        assert result is False, "Wrong password should fail hash verification"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 