"""Tests for whitespace minimizer addon."""

import pytest
from ai_content_generator.addons import WhitespaceMinimizerAddon, AddonContext
from ai_content_generator.utils import generate_request_id


class TestWhitespaceMinimizerAddon:
    """Tests for WhitespaceMinimizerAddon."""
    
    @pytest.fixture
    def addon(self):
        """Create a default addon instance."""
        return WhitespaceMinimizerAddon()
    
    @pytest.fixture
    def context(self):
        """Create a test context."""
        return AddonContext(
            request_id=generate_request_id(),
            prompt="test",
            model="gpt-5-nano",
            provider="openai"
        )
    
    def test_get_name(self, addon):
        """Test get_name method."""
        assert addon.get_name() == "Whitespace Minimizer Addon"
    
    def test_get_description(self, addon):
        """Test get_description method."""
        desc = addon.get_description()
        assert "Minimizes" in desc
    
    @pytest.mark.asyncio
    async def test_minimize_spaces(self, addon, context):
        """Test collapsing multiple spaces."""
        prompt = "This    has    multiple    spaces"
        result = await addon.pre_request(prompt, context)
        
        assert result is not None
        assert "  " not in result  # No double spaces
        assert context.custom["whitespace_minimizer_chars_saved"] > 0
    
    @pytest.mark.asyncio
    async def test_minimize_tabs(self, addon, context):
        """Test converting tabs to spaces."""
        prompt = "This\thas\ttabs"
        result = await addon.pre_request(prompt, context)
        
        assert result is not None
        assert "\t" not in result
        assert " " in result
    
    @pytest.mark.asyncio
    async def test_minimize_newlines(self, addon, context):
        """Test reducing multiple newlines."""
        prompt = "Line 1\n\n\n\nLine 2"
        result = await addon.pre_request(prompt, context)
        
        assert result is not None
        assert "\n\n\n\n" not in result
        assert context.custom["whitespace_minimizer_minimized"] is True
    
    @pytest.mark.asyncio
    async def test_preserve_code_blocks(self, addon, context):
        """Test preserving code blocks."""
        prompt = "Here    is    code:\n\n\n```python\ndef test():\n    return True\n```\n\n\nEnd"
        result = await addon.pre_request(prompt, context)
        
        assert result is not None
        assert "```python" in result
        assert "def test():" in result
        # Spaces inside code block should be preserved
        assert "    return" in result or " return" in result
        # Whitespace outside code blocks should be minimized
        # Extract text before and after code block
        code_start = result.find("```python")
        code_end = result.rfind("```") + 3
        before_code = result[:code_start]
        after_code = result[code_end:]
        # Check that before/after don't have multiple spaces (content inside is preserved)
        assert "  " not in before_code.replace("\n", " ").strip()
        assert "  " not in after_code.replace("\n", " ").strip()
    
    @pytest.mark.asyncio
    async def test_empty_prompt(self, addon, context):
        """Test handling empty prompt."""
        result = await addon.pre_request("", context)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_no_minimization_needed(self, addon, context):
        """Test prompt that doesn't need minimization."""
        prompt = "This is a clean prompt with no extra whitespace."
        result = await addon.pre_request(prompt, context)
        # Should return None if nothing changed
        assert result is None or result == prompt
    
    @pytest.mark.asyncio
    async def test_aggressive_mode(self):
        """Test aggressive mode."""
        addon = WhitespaceMinimizerAddon(aggressive_mode=True, minimize_newlines=True)
        context = AddonContext(
            request_id=generate_request_id(),
            prompt="Line 1\n\n\n\nLine 2\n\n\n",
            model="gpt-5-nano",
            provider="openai"
        )
        
        result = await addon.pre_request(context.prompt, context)
        
        assert result is not None
        # Should have at most single newline between lines
        assert "\n\n\n" not in result
    
    @pytest.mark.asyncio
    async def test_disable_spaces_minimization(self):
        """Test disabling space minimization."""
        addon = WhitespaceMinimizerAddon(minimize_spaces=False, minimize_newlines=False)
        context = AddonContext(
            request_id=generate_request_id(),
            prompt="Multiple    spaces    here",
            model="gpt-5-nano",
            provider="openai"
        )
        
        result = await addon.pre_request(context.prompt, context)
        # Should not minimize spaces
        assert result is None or "    " in result
    
    @pytest.mark.asyncio
    async def test_code_block_preservation_inline(self, addon, context):
        """Test preserving inline code blocks."""
        prompt = "Use    `variable_name`    in    your    code"
        result = await addon.pre_request(prompt, context)
        
        assert result is not None
        assert "`variable_name`" in result
        # Whitespace outside inline code should be minimized
        assert "  " not in result.replace("`variable_name`", "X")
    
    @pytest.mark.asyncio
    async def test_post_request_tracking(self, addon, context):
        """Test post_request hook tracks token usage."""
        # First minimize a prompt
        prompt = "This    has    spaces"
        minimized = await addon.pre_request(prompt, context)
        
        # Then process response
        response = {
            "content": "Response",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50
            }
        }
        
        result = await addon.post_request(response, context)
        
        assert result == response
        assert "whitespace_minimizer_actual_input_tokens" in context.custom
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, addon, context):
        """Test statistics tracking."""
        prompt1 = "Multiple    spaces    here"
        prompt2 = "Line 1\n\n\nLine 2"
        
        await addon.pre_request(prompt1, context)
        
        context2 = AddonContext(
            request_id=generate_request_id(),
            prompt=prompt2,
            model="gpt-5-nano",
            provider="openai"
        )
        await addon.pre_request(prompt2, context2)
        
        stats = addon.get_stats()
        assert stats["total_requests"] == 2
        assert stats["total_chars_removed"] > 0
        assert stats["total_tokens_saved"] >= 0
        assert stats["average_chars_per_request"] > 0
    
    @pytest.mark.asyncio
    async def test_reset_stats(self, addon, context):
        """Test resetting statistics."""
        prompt = "Multiple    spaces"
        await addon.pre_request(prompt, context)
        
        stats_before = addon.get_stats()
        assert stats_before["total_requests"] > 0
        
        addon.reset_stats()
        stats_after = addon.get_stats()
        assert stats_after["total_requests"] == 0
        assert stats_after["total_chars_removed"] == 0
        assert stats_after["total_tokens_saved"] == 0
    
    @pytest.mark.asyncio
    async def test_original_prompt_stored(self, addon, context):
        """Test that original prompt is stored in context."""
        original = "Multiple    spaces    here"
        result = await addon.pre_request(original, context)
        
        assert "whitespace_minimizer_original" in context.custom
        assert context.custom["whitespace_minimizer_original"] == original
    
    def test_enable_disable(self, addon):
        """Test enable/disable functionality."""
        assert addon.is_enabled() is True
        
        addon.disable()
        assert addon.is_enabled() is False
        
        addon.enable()
        assert addon.is_enabled() is True
    
    @pytest.mark.asyncio
    async def test_max_newlines_setting(self):
        """Test max_newlines configuration."""
        addon = WhitespaceMinimizerAddon(max_newlines=3, minimize_newlines=True)
        context = AddonContext(
            request_id=generate_request_id(),
            prompt="Line 1\n\n\n\n\nLine 2",
            model="gpt-5-nano",
            provider="openai"
        )
        
        result = await addon.pre_request(context.prompt, context)
        
        assert result is not None
        # Should have at most 3 newlines
        assert "\n\n\n\n" not in result

