"""Tests for validators."""

import pytest
from ai_content_generator.validators import (
    APIKeyValidator,
    ValidationResult,
)


class TestAPIKeyValidator:
    """Tests for APIKeyValidator."""
    
    @pytest.mark.asyncio
    async def test_valid_openai_key(self):
        """Test validation of valid OpenAI key."""
        validator = APIKeyValidator(
            api_key="sk-1234567890abcdefghij",
            provider="openai"
        )
        
        result = await validator.validate()
        
        # May have warnings about format, but should not have errors
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_missing_key(self):
        """Test validation of missing key."""
        validator = APIKeyValidator(
            api_key=None,
            provider="openai"
        )
        
        result = await validator.validate()
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "missing" in result.errors[0].lower()
    
    @pytest.mark.asyncio
    async def test_empty_key(self):
        """Test validation of empty key."""
        validator = APIKeyValidator(
            api_key="",
            provider="openai"
        )
        
        result = await validator.validate()
        
        assert result.is_valid is False
    
    @pytest.mark.asyncio
    async def test_short_key(self):
        """Test validation of too short key."""
        validator = APIKeyValidator(
            api_key="sk-123",
            provider="openai"
        )
        
        result = await validator.validate()
        
        assert result.is_valid is False
        assert any("too short" in error.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_key_with_whitespace(self):
        """Test validation of key with whitespace."""
        validator = APIKeyValidator(
            api_key="sk-1234567890 abcdefghij",
            provider="openai"
        )
        
        result = await validator.validate()
        
        assert result.is_valid is False
        assert any("whitespace" in error.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_key_with_env_var_syntax(self):
        """Test validation of key with environment variable syntax."""
        validator = APIKeyValidator(
            api_key="${OPENAI_API_KEY}",
            provider="openai"
        )
        
        result = await validator.validate()
        
        assert result.is_valid is False
        assert any("environment variable" in error.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_anthropic_key_format(self):
        """Test validation of Anthropic key format."""
        validator = APIKeyValidator(
            api_key="sk-ant-1234567890abcdefghij",
            provider="anthropic"
        )
        
        result = await validator.validate()
        
        # Should pass or have only warnings
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_unknown_provider(self):
        """Test validation with unknown provider."""
        validator = APIKeyValidator(
            api_key="test-key-1234567890",
            provider="unknown"
        )
        
        result = await validator.validate()
        
        # Should have warning about no pattern
        assert len(result.warnings) > 0

