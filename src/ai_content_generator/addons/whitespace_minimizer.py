"""Whitespace minimizer addon for reducing token usage."""

import re
from typing import Any, Optional, Tuple


from .base_addon import BaseAddon, AddonContext


class WhitespaceMinimizerAddon(BaseAddon):
    """
    Addon for minimizing whitespace in prompts to reduce token usage.
    
    Features:
    - Collapses multiple spaces into single space
    - Converts tabs to spaces
    - Reduces multiple newlines
    - Optionally preserves code blocks
    - Tracks token savings statistics
    
    Example:
        ```python
        minimizer = WhitespaceMinimizerAddon(
            minimize_spaces=True,
            minimize_tabs=True,
            minimize_newlines=True,
            preserve_code_blocks=True,
            aggressive_mode=False
        )
        
        # Use in session
        session.add_addon(minimizer)
        
        # Check stats
        stats = minimizer.get_stats()
        print(f"Tokens saved: {stats['total_tokens_saved']}")
        ```
    """
    
    def __init__(
        self,
        minimize_spaces: bool = True,
        minimize_tabs: bool = True,
        minimize_newlines: bool = True,
        preserve_code_blocks: bool = True,
        aggressive_mode: bool = False,
        max_newlines: int = 2,
    ):
        """
        Initialize whitespace minimizer addon.
        
        Args:
            minimize_spaces: Whether to collapse multiple spaces
            minimize_tabs: Whether to convert tabs to spaces
            minimize_newlines: Whether to reduce multiple newlines
            preserve_code_blocks: Whether to skip minimization inside code blocks
            aggressive_mode: Maximum compression (single newlines only)
            max_newlines: Maximum consecutive newlines to preserve (ignored if aggressive_mode=True)
        """
        super().__init__()
        self.minimize_spaces = minimize_spaces
        self.minimize_tabs = minimize_tabs
        self.minimize_newlines = minimize_newlines
        self.preserve_code_blocks = preserve_code_blocks
        self.aggressive_mode = aggressive_mode
        self.max_newlines = max_newlines if not aggressive_mode else 1
        
        # Statistics tracking
        self._total_requests = 0
        self._total_chars_removed = 0
        self._total_token_savings = 0
        
    def get_name(self) -> str:
        """Get addon name."""
        return "Whitespace Minimizer Addon"
    
    def get_description(self) -> str:
        """Get addon description."""
        features = []
        if self.minimize_spaces:
            features.append("spaces")
        if self.minimize_tabs:
            features.append("tabs")
        if self.minimize_newlines:
            features.append("newlines")
        
        desc = f"Minimizes {'/'.join(features)}"
        if self.preserve_code_blocks:
            desc += " (preserves code blocks)"
        if self.aggressive_mode:
            desc += " (aggressive)"
        
        return desc
    
    def _detect_code_blocks(self, text: str) -> list[Tuple[int, int]]:
        """
        Detect code block boundaries in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (start, end) tuples for code block ranges
        """
        code_ranges = []
        
        # Common code block patterns: triple backticks, indented blocks, etc.
        patterns = [
            # Markdown code blocks: ```language\n...\n```
            (r'```[\w]*\n.*?\n```', re.DOTALL),
            # Single backticks for inline code
            (r'`[^`\n]+`', re.DOTALL),
            # Python-style docstrings: """...""" or '''...'''
            (r'""".*?"""', re.DOTALL),
            (r"'''.*?'''", re.DOTALL),
        ]
        
        for pattern, flags in patterns:
            for match in re.finditer(pattern, text, flags):
                code_ranges.append((match.start(), match.end()))
        
        # Sort by start position
        code_ranges.sort(key=lambda x: x[0])
        
        # Merge overlapping ranges
        merged = []
        for start, end in code_ranges:
            if merged and start <= merged[-1][1]:
                # Merge with previous range
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged
    
    def _is_in_code_block(self, position: int, code_ranges: list[Tuple[int, int]]) -> bool:
        """
        Check if a position is inside a code block.
        
        Args:
            position: Character position
            code_ranges: List of code block ranges
            
        Returns:
            True if position is in a code block
        """
        for start, end in code_ranges:
            if start <= position < end:
                return True
        return False
    
    def _minimize_whitespace(
        self,
        text: str,
        code_ranges: Optional[list[Tuple[int, int]]] = None
    ) -> str:
        """
        Minimize whitespace in text while preserving code blocks.
        
        Args:
            text: Text to minimize
            code_ranges: Optional list of code block ranges to preserve
            
        Returns:
            Minimized text
        """
        if code_ranges is None:
            code_ranges = []
        
        # Convert to list of characters for processing
        chars = list(text)
        result_chars = []
        i = 0
        
        while i < len(chars):
            char = chars[i]
            in_code = self._is_in_code_block(i, code_ranges)
            
            if in_code:
                # Preserve characters inside code blocks
                result_chars.append(char)
                i += 1
            else:
                # Process whitespace
                if char == ' ' and self.minimize_spaces:
                    # Collapse multiple spaces
                    result_chars.append(' ')
                    while i + 1 < len(chars) and chars[i + 1] == ' ':
                        i += 1
                    i += 1
                    
                elif char == '\t' and self.minimize_tabs:
                    # Convert tab to space
                    result_chars.append(' ')
                    i += 1
                    
                elif char == '\n' and self.minimize_newlines:
                    # Handle newlines
                    result_chars.append('\n')
                    newline_count = 1
                    while i + 1 < len(chars) and chars[i + 1] == '\n':
                        newline_count += 1
                        i += 1
                    
                    # Add additional newlines up to max_newlines
                    additional = min(newline_count - 1, self.max_newlines - 1)
                    result_chars.extend(['\n'] * additional)
                    
                    i += 1
                else:
                    # Regular character, preserve as-is
                    result_chars.append(char)
                    i += 1
        
        result = ''.join(result_chars)
        
        # Strip leading/trailing whitespace from lines
        if self.minimize_spaces or self.minimize_newlines:
            lines = result.split('\n')
            stripped_lines = [line.rstrip() if self.minimize_spaces else line for line in lines]
            result = '\n'.join(stripped_lines)
        
        # Strip leading and trailing newlines if aggressive mode
        if self.aggressive_mode and self.minimize_newlines:
            result = result.strip('\n')
        
        return result
    
    def _estimate_token_savings(self, original: str, minimized: str) -> int:
        """
        Estimate token savings from minimization.
        
        Args:
            original: Original text
            minimized: Minimized text
            
        Returns:
            Estimated tokens saved (roughly, 1 token ≈ 4 characters)
        """
        chars_saved = len(original) - len(minimized)
        # Rough estimation: 1 token ≈ 4 characters
        tokens_saved = chars_saved // 4
        return max(0, tokens_saved)
    
    async def pre_request(
        self,
        prompt: str,
        context: AddonContext
    ) -> Optional[str]:
        """
        Minimize whitespace in prompt before request.
        
        Args:
            prompt: The prompt
            context: Addon context
            
        Returns:
            Minimized prompt (None means continue with original)
        """
        if not prompt:
            return None
        
        # Store original prompt in context
        original_prompt = prompt
        context.custom["whitespace_minimizer_original"] = original_prompt
        
        # Detect code blocks if preservation is enabled
        code_ranges = []
        if self.preserve_code_blocks:
            code_ranges = self._detect_code_blocks(original_prompt)
        
        # Minimize whitespace
        minimized_prompt = self._minimize_whitespace(original_prompt, code_ranges)
        
        # If nothing changed, return None to avoid unnecessary modifications
        if minimized_prompt == original_prompt:
            return None
        
        # Update statistics
        self._total_requests += 1
        chars_removed = len(original_prompt) - len(minimized_prompt)
        tokens_saved = self._estimate_token_savings(original_prompt, minimized_prompt)
        
        self._total_chars_removed += chars_removed
        self._total_token_savings += tokens_saved
        
        # Store stats in context
        context.custom["whitespace_minimizer_chars_saved"] = chars_removed
        context.custom["whitespace_minimizer_tokens_saved"] = tokens_saved
        context.custom["whitespace_minimizer_minimized"] = True
        
        return minimized_prompt
    
    async def post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        Optional: Track actual token usage from response.
        
        Args:
            response: Response from provider
            context: Addon context
            
        Returns:
            Original response
        """
        # Extract actual token usage if available
        if "usage" in response:
            usage = response["usage"]
            actual_input_tokens = usage.get("input_tokens", 0)
            
            # Store for comparison with estimates
            context.custom["whitespace_minimizer_actual_input_tokens"] = actual_input_tokens
            
            if "whitespace_minimizer_original" in context.custom:
                # Could estimate what tokens would have been without minimization
                # This is approximate since we don't have the exact tokenizer
                pass
        
        return response
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._total_requests = 0
        self._total_chars_removed = 0
        self._total_token_savings = 0
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get minimization statistics.
        
        Returns:
            Dictionary with stats including:
            - total_requests: Number of requests processed
            - total_chars_removed: Total characters removed
            - total_tokens_saved: Estimated total tokens saved
            - average_chars_per_request: Average chars removed per request
            - average_tokens_per_request: Average tokens saved per request
        """
        avg_chars = (
            self._total_chars_removed / self._total_requests
            if self._total_requests > 0
            else 0
        )
        avg_tokens = (
            self._total_token_savings / self._total_requests
            if self._total_requests > 0
            else 0
        )
        
        return {
            "total_requests": self._total_requests,
            "total_chars_removed": self._total_chars_removed,
            "total_tokens_saved": self._total_token_savings,
            "average_chars_per_request": avg_chars,
            "average_tokens_per_request": avg_tokens,
        }

