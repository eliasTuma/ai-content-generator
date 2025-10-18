"""API key validator."""

import re
from typing import Optional

from .base_validator import BaseValidator, ValidationResult


class APIKeyValidator(BaseValidator):
    """
    Validator for checking API key presence and basic format.
    
    This validator checks:
    - API key is present (not None or empty)
    - API key has a reasonable format (provider-specific patterns)
    
    Example:
        ```python
        validator = APIKeyValidator(
            api_key="sk-...",
            provider="openai"
        )
        result = await validator.validate()
        if not result.is_valid:
            print(f"Invalid API key: {result.message}")
        ```
    """
    
    # Provider-specific API key patterns
    KEY_PATTERNS = {
        "openai": r"^sk-[A-Za-z0-9_-]{20,}$",
        "anthropic": r"^sk-ant-[A-Za-z0-9_-]{20,}$",
    }
    
    def __init__(self, api_key: Optional[str], provider: str):
        """
        Initialize API key validator.
        
        Args:
            api_key: API key to validate (can be None)
            provider: Provider name (e.g., "openai", "anthropic")
        """
        self.api_key = api_key
        self.provider = provider.lower()
    
    def get_validation_name(self) -> str:
        """Get validator name."""
        return "API Key Validator"
    
    def get_validation_description(self) -> str:
        """Get validator description."""
        return f"Validates {self.provider} API key presence and format"
    
    async def validate(self) -> ValidationResult:
        """
        Validate API key.
        
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        context = {"provider": self.provider}
        
        # Check if API key is present
        if not self.api_key:
            errors.append("API key is missing or empty")
            return ValidationResult(
                is_valid=False,
                message=f"API key validation failed for {self.provider}",
                errors=errors,
                context=context,
            )
        
        # Check API key length
        if len(self.api_key) < 10:
            errors.append("API key is too short (minimum 10 characters)")
        
        # Check provider-specific format
        if self.provider in self.KEY_PATTERNS:
            pattern = self.KEY_PATTERNS[self.provider]
            if not re.match(pattern, self.api_key):
                warnings.append(
                    f"API key format doesn't match expected pattern for {self.provider}. "
                    "This might still work if the provider changed their key format."
                )
                context["expected_pattern"] = pattern
        else:
            warnings.append(
                f"No validation pattern available for provider '{self.provider}'. "
                "Skipping format validation."
            )
        
        # Check for common mistakes
        if self.api_key.startswith("$") or "{" in self.api_key:
            errors.append(
                "API key appears to contain environment variable syntax. "
                "Make sure to resolve environment variables before validation."
            )
        
        if " " in self.api_key:
            errors.append("API key contains whitespace characters")
        
        # Determine overall validity
        is_valid = len(errors) == 0
        
        if is_valid:
            message = f"API key validation passed for {self.provider}"
        else:
            message = f"API key validation failed for {self.provider}"
        
        return ValidationResult(
            is_valid=is_valid,
            message=message,
            errors=errors,
            warnings=warnings,
            context=context,
        )

