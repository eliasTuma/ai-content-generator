"""Response validator addon for validating API responses."""

from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, ValidationError

from .base_addon import BaseAddon, AddonContext
from ..core.exceptions import ValidationError as CustomValidationError


class ValidationMode(Enum):
    """Validation mode for response validation."""
    
    STRICT = "strict"  # Raise exception on validation failure
    WARN = "warn"      # Log warning but continue
    AUTO_RETRY = "auto_retry"  # Retry request on validation failure


class ResponseValidatorAddon(BaseAddon):
    """
    Addon for validating API responses against a schema.
    
    Features:
    - Pydantic schema validation
    - Custom validation functions
    - Multiple validation modes (strict, warn, auto-retry)
    - Validation statistics
    
    Example:
        ```python
        from pydantic import BaseModel
        
        class MyResponseSchema(BaseModel):
            content: str
            model: str
            input_tokens: int
            output_tokens: int
        
        validator = ResponseValidatorAddon(
            schema=MyResponseSchema,
            mode=ValidationMode.STRICT
        )
        
        # Or use custom validator
        def my_validator(response: dict) -> bool:
            return "content" in response and len(response["content"]) > 0
        
        validator = ResponseValidatorAddon(
            validator_func=my_validator,
            mode=ValidationMode.WARN
        )
        ```
    """
    
    def __init__(
        self,
        schema: Optional[type[BaseModel]] = None,
        validator_func: Optional[Callable[[dict], bool]] = None,
        mode: ValidationMode = ValidationMode.STRICT,
        max_retries: int = 2,
    ):
        """
        Initialize response validator addon.
        
        Args:
            schema: Pydantic model for validation
            validator_func: Custom validation function
            mode: Validation mode
            max_retries: Max retries for AUTO_RETRY mode
        """
        super().__init__()
        
        if schema is None and validator_func is None:
            raise ValueError("Either schema or validator_func must be provided")
        
        self.schema = schema
        self.validator_func = validator_func
        self.mode = mode
        self.max_retries = max_retries
        self._validation_failures = 0
        self._validation_successes = 0
    
    def get_name(self) -> str:
        """Get addon name."""
        return "Response Validator Addon"
    
    def get_description(self) -> str:
        """Get addon description."""
        return f"Validates responses (mode: {self.mode.value})"
    
    def _validate_with_schema(self, response: dict) -> tuple[bool, Optional[str]]:
        """
        Validate response using Pydantic schema.
        
        Args:
            response: Response to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.schema is None:
            return True, None
        
        try:
            self.schema(**response)
            return True, None
        except ValidationError as e:
            return False, str(e)
    
    def _validate_with_func(self, response: dict) -> tuple[bool, Optional[str]]:
        """
        Validate response using custom function.
        
        Args:
            response: Response to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.validator_func is None:
            return True, None
        
        try:
            is_valid = self.validator_func(response)
            if not is_valid:
                return False, "Custom validation function returned False"
            return True, None
        except Exception as e:
            return False, f"Validation function raised exception: {str(e)}"
    
    async def post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        Validate response after successful request.
        
        Args:
            response: Response from provider
            context: Addon context
        
        Returns:
            Original response if valid
        
        Raises:
            CustomValidationError: If validation fails in STRICT mode
        """
        # Validate with schema
        is_valid_schema, schema_error = self._validate_with_schema(response)
        
        # Validate with custom function
        is_valid_func, func_error = self._validate_with_func(response)
        
        # Combine results
        is_valid = is_valid_schema and is_valid_func
        error_message = schema_error or func_error
        
        if is_valid:
            self._validation_successes += 1
            return response
        
        # Validation failed
        self._validation_failures += 1
        
        # Store validation info in context
        context.custom["validation_failed"] = True
        context.custom["validation_error"] = error_message
        
        # Handle based on mode
        if self.mode == ValidationMode.STRICT:
            raise CustomValidationError(
                message=f"Response validation failed: {error_message}",
                context={
                    "response": response,
                    "validation_error": error_message,
                }
            )
        
        elif self.mode == ValidationMode.WARN:
            # Just log warning and continue
            import sys
            print(
                f"WARNING: Response validation failed: {error_message}",
                file=sys.stderr
            )
            return response
        
        elif self.mode == ValidationMode.AUTO_RETRY:
            # Check retry count
            retry_count = context.custom.get("validation_retry_count", 0)
            
            if retry_count < self.max_retries:
                context.custom["validation_retry_count"] = retry_count + 1
                # Signal that retry is needed by raising an error
                raise CustomValidationError(
                    message=f"Response validation failed, retrying: {error_message}",
                    context={
                        "response": response,
                        "validation_error": error_message,
                        "retry_count": retry_count + 1,
                    }
                )
            else:
                # Max retries exceeded, raise error
                raise CustomValidationError(
                    message=f"Response validation failed after {retry_count} retries: {error_message}",
                    context={
                        "response": response,
                        "validation_error": error_message,
                        "max_retries_exceeded": True,
                    }
                )
        
        return response
    
    def get_stats(self) -> dict:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with validation stats
        """
        total = self._validation_successes + self._validation_failures
        success_rate = self._validation_successes / total if total > 0 else 0.0
        
        return {
            "validation_successes": self._validation_successes,
            "validation_failures": self._validation_failures,
            "total_validations": total,
            "success_rate": success_rate,
        }
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._validation_successes = 0
        self._validation_failures = 0

