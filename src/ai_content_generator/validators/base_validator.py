"""Base validator interface and validation result."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """
    Result of a validation operation.
    
    Attributes:
        is_valid: Whether validation passed
        message: Main validation message
        errors: List of error messages (if any)
        warnings: List of warning messages (if any)
        context: Additional context data
    """
    is_valid: bool
    message: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of validation result."""
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        parts = [f"{status}: {self.message}"]
        
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        
        if self.warnings:
            parts.append(f"Warnings: {', '.join(self.warnings)}")
        
        return " | ".join(parts)


class BaseValidator(ABC):
    """
    Abstract base class for validators.
    
    All validators must inherit from this class and implement the validate method.
    
    Example:
        ```python
        class MyValidator(BaseValidator):
            async def validate(self) -> ValidationResult:
                # Validation logic here
                return ValidationResult(
                    is_valid=True,
                    message="Validation passed"
                )
        ```
    """
    
    @abstractmethod
    async def validate(self) -> ValidationResult:
        """
        Perform validation.
        
        Returns:
            ValidationResult with validation outcome
        """
        pass
    
    @abstractmethod
    def get_validation_name(self) -> str:
        """
        Get the name of this validator.
        
        Returns:
            Validator name
        """
        pass
    
    @abstractmethod
    def get_validation_description(self) -> str:
        """
        Get a description of what this validator checks.
        
        Returns:
            Validator description
        """
        pass

