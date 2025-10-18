"""Validator manager for orchestrating multiple validators."""

from typing import Optional

from .base_validator import BaseValidator, ValidationResult
from ..core.provider import BaseProvider


class ValidationReport:
    """
    Comprehensive validation report from multiple validators.
    
    Attributes:
        is_valid: Whether all validations passed
        validators_run: Number of validators executed
        validators_passed: Number of validators that passed
        validators_failed: Number of validators that failed
        results: Dictionary mapping validator names to their results
    """
    
    def __init__(self):
        """Initialize empty validation report."""
        self.results: dict[str, ValidationResult] = {}
    
    @property
    def is_valid(self) -> bool:
        """Check if all validations passed."""
        return all(result.is_valid for result in self.results.values())
    
    @property
    def validators_run(self) -> int:
        """Get number of validators executed."""
        return len(self.results)
    
    @property
    def validators_passed(self) -> int:
        """Get number of validators that passed."""
        return sum(1 for result in self.results.values() if result.is_valid)
    
    @property
    def validators_failed(self) -> int:
        """Get number of validators that failed."""
        return sum(1 for result in self.results.values() if not result.is_valid)
    
    def add_result(self, validator_name: str, result: ValidationResult) -> None:
        """
        Add a validation result to the report.
        
        Args:
            validator_name: Name of the validator
            result: Validation result
        """
        self.results[validator_name] = result
    
    def get_failed_validations(self) -> dict[str, ValidationResult]:
        """
        Get all failed validation results.
        
        Returns:
            Dictionary of failed validations
        """
        return {
            name: result
            for name, result in self.results.items()
            if not result.is_valid
        }
    
    def get_warnings(self) -> dict[str, list[str]]:
        """
        Get all warnings from all validators.
        
        Returns:
            Dictionary mapping validator names to their warnings
        """
        return {
            name: result.warnings
            for name, result in self.results.items()
            if result.warnings
        }
    
    def __str__(self) -> str:
        """String representation of validation report."""
        status = "✓ ALL PASSED" if self.is_valid else "✗ SOME FAILED"
        summary = f"{status} ({self.validators_passed}/{self.validators_run} passed)"
        
        lines = [f"\n{'='*60}", f"Validation Report: {summary}", f"{'='*60}"]
        
        for name, result in self.results.items():
            lines.append(f"\n{name}:")
            lines.append(f"  {result}")
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)


class ValidatorManager:
    """
    Manager for orchestrating multiple validators.
    
    Example:
        ```python
        from ai_content_generator.providers import OpenAIProvider
        from ai_content_generator.validators import (
            ValidatorManager,
            APIKeyValidator,
            ConnectivityValidator,
            ModelValidator
        )
        
        provider = OpenAIProvider(api_key="sk-...")
        manager = ValidatorManager()
        
        # Add validators
        manager.add_validator(APIKeyValidator(api_key="sk-...", provider="openai"))
        manager.add_validator(ConnectivityValidator(provider))
        manager.add_validator(ModelValidator(provider, model="gpt-5-nano"))
        
        # Run all validations
        report = await manager.validate_all()
        
        if report.is_valid:
            print("All validations passed!")
        else:
            print(f"Validation failed: {report}")
        ```
    """
    
    def __init__(self):
        """Initialize validator manager."""
        self.validators: list[BaseValidator] = []
    
    def add_validator(self, validator: BaseValidator) -> None:
        """
        Register a validator.
        
        Args:
            validator: Validator instance to add
        """
        self.validators.append(validator)
    
    def clear_validators(self) -> None:
        """Remove all registered validators."""
        self.validators.clear()
    
    def get_validators(self) -> list[BaseValidator]:
        """
        Get list of registered validators.
        
        Returns:
            List of validator instances
        """
        return self.validators.copy()
    
    async def validate_all(self, stop_on_failure: bool = False) -> ValidationReport:
        """
        Run all registered validators.
        
        Args:
            stop_on_failure: If True, stop validation on first failure
        
        Returns:
            ValidationReport with results from all validators
        """
        report = ValidationReport()
        
        for validator in self.validators:
            validator_name = validator.get_validation_name()
            
            try:
                result = await validator.validate()
                report.add_result(validator_name, result)
                
                # Stop if requested and validation failed
                if stop_on_failure and not result.is_valid:
                    break
            
            except Exception as e:
                # Handle validator execution errors
                error_result = ValidationResult(
                    is_valid=False,
                    message=f"Validator execution failed",
                    errors=[f"Exception during validation: {str(e)}"],
                    context={
                        "error_type": type(e).__name__,
                        "validator": validator_name,
                    }
                )
                report.add_result(validator_name, error_result)
                
                if stop_on_failure:
                    break
        
        return report
    
    async def validate_provider(
        self,
        provider: BaseProvider,
        model: Optional[str] = None,
        check_connectivity: bool = True,
        check_model: bool = True,
    ) -> ValidationReport:
        """
        Run provider-specific validations.
        
        This is a convenience method that creates and runs common validators
        for a provider.
        
        Args:
            provider: Provider instance to validate
            model: Optional model name to validate
            check_connectivity: Whether to check connectivity
            check_model: Whether to check model availability (requires model parameter)
        
        Returns:
            ValidationReport with results
        """
        from .api_key_validator import APIKeyValidator
        from .connectivity_validator import ConnectivityValidator
        from .model_validator import ModelValidator
        
        # Create temporary manager
        temp_manager = ValidatorManager()
        
        # Add API key validator
        temp_manager.add_validator(
            APIKeyValidator(
                api_key=provider._api_key,
                provider=provider.provider_name
            )
        )
        
        # Add connectivity validator if requested
        if check_connectivity:
            temp_manager.add_validator(ConnectivityValidator(provider))
        
        # Add model validator if requested and model provided
        if check_model and model:
            temp_manager.add_validator(ModelValidator(provider, model))
        
        # Run validations
        return await temp_manager.validate_all()

