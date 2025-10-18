"""Connectivity validator."""

from typing import Optional

from .base_validator import BaseValidator, ValidationResult
from ..core.provider import BaseProvider


class ConnectivityValidator(BaseValidator):
    """
    Validator for checking provider connectivity and API key validity.
    
    This validator:
    - Tests connection to the provider API
    - Verifies the API key works by making a minimal request
    - Checks network connectivity
    
    Example:
        ```python
        from ai_content_generator.providers import OpenAIProvider
        
        provider = OpenAIProvider(api_key="sk-...")
        validator = ConnectivityValidator(provider)
        result = await validator.validate()
        
        if result.is_valid:
            print("Connection successful!")
        else:
            print(f"Connection failed: {result.message}")
        ```
    """
    
    def __init__(self, provider: BaseProvider, timeout: Optional[int] = None):
        """
        Initialize connectivity validator.
        
        Args:
            provider: Provider instance to test
            timeout: Optional timeout in seconds (uses provider default if not specified)
        """
        self.provider = provider
        self.timeout = timeout
    
    def get_validation_name(self) -> str:
        """Get validator name."""
        return "Connectivity Validator"
    
    def get_validation_description(self) -> str:
        """Get validator description."""
        return f"Validates connection to {self.provider.provider_name} API"
    
    async def validate(self) -> ValidationResult:
        """
        Validate provider connectivity.
        
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        context = {
            "provider": self.provider.provider_name,
            "timeout": self.timeout or "default",
        }
        
        try:
            # Attempt to validate connection
            is_connected = await self.provider.validate_connection()
            
            if is_connected:
                return ValidationResult(
                    is_valid=True,
                    message=f"Successfully connected to {self.provider.provider_name}",
                    context=context,
                )
            else:
                errors.append("Connection validation returned False")
                return ValidationResult(
                    is_valid=False,
                    message=f"Failed to connect to {self.provider.provider_name}",
                    errors=errors,
                    context=context,
                )
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            errors.append(f"{error_type}: {error_msg}")
            
            # Provide helpful context based on error type
            if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                errors.append("API key appears to be invalid or expired")
            elif "timeout" in error_msg.lower():
                errors.append("Connection timed out - check network connectivity")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                errors.append("Network error - check internet connection and firewall settings")
            elif "rate limit" in error_msg.lower():
                warnings.append("Rate limit reached - API key is valid but quota exceeded")
            
            context["error_type"] = error_type
            context["error_details"] = error_msg
            
            return ValidationResult(
                is_valid=False,
                message=f"Connection to {self.provider.provider_name} failed",
                errors=errors,
                warnings=warnings,
                context=context,
            )

