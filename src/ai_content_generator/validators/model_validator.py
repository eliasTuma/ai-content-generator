"""Model availability validator."""

from typing import Optional

from .base_validator import BaseValidator, ValidationResult
from ..core.provider import BaseProvider
from ..core.exceptions import ModelNotFoundError


class ModelValidator(BaseValidator):
    """
    Validator for checking model availability and configuration.
    
    This validator:
    - Checks if specified model exists for the provider
    - Verifies model is accessible with current API key
    - Validates model configuration parameters
    
    Example:
        ```python
        from ai_content_generator.providers import OpenAIProvider
        
        provider = OpenAIProvider(api_key="sk-...")
        validator = ModelValidator(provider, model="gpt-5-nano")
        result = await validator.validate()
        
        if result.is_valid:
            print(f"Model is available: {result.context['model_info']}")
        else:
            print(f"Model validation failed: {result.message}")
        ```
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        check_accessibility: bool = False
    ):
        """
        Initialize model validator.
        
        Args:
            provider: Provider instance to check
            model: Model name to validate
            check_accessibility: Whether to verify model is accessible (requires API call)
        """
        self.provider = provider
        self.model = model
        self.check_accessibility = check_accessibility
    
    def get_validation_name(self) -> str:
        """Get validator name."""
        return "Model Validator"
    
    def get_validation_description(self) -> str:
        """Get validator description."""
        return f"Validates model '{self.model}' availability for {self.provider.provider_name}"
    
    async def validate(self) -> ValidationResult:
        """
        Validate model availability.
        
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        context = {
            "provider": self.provider.provider_name,
            "model": self.model,
        }
        
        # Check if model exists in provider's supported models
        supported_models = self.provider.supported_models
        
        if self.model not in supported_models:
            errors.append(f"Model '{self.model}' is not supported by {self.provider.provider_name}")
            errors.append(f"Available models: {', '.join(supported_models[:5])}" + 
                         (f" and {len(supported_models) - 5} more" if len(supported_models) > 5 else ""))
            
            # Check for similar model names (typo detection)
            similar_models = [m for m in supported_models if self.model.lower() in m.lower()]
            if similar_models:
                warnings.append(f"Did you mean one of these? {', '.join(similar_models[:3])}")
            
            context["available_models"] = supported_models
            context["similar_models"] = similar_models
            
            return ValidationResult(
                is_valid=False,
                message=f"Model '{self.model}' not found",
                errors=errors,
                warnings=warnings,
                context=context,
            )
        
        # Get model information
        try:
            model_info = await self.provider.get_model_info(self.model)
            context["model_info"] = model_info
            
            # Check for model-specific warnings
            if "context_window" in model_info:
                context["context_window"] = model_info["context_window"]
            
            if "input_price_per_1m" in model_info and "output_price_per_1m" in model_info:
                context["pricing"] = {
                    "input": model_info["input_price_per_1m"],
                    "output": model_info["output_price_per_1m"],
                }
        
        except ModelNotFoundError as e:
            errors.append(f"Model info retrieval failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Failed to retrieve model information",
                errors=errors,
                context=context,
            )
        except Exception as e:
            warnings.append(f"Could not retrieve model details: {str(e)}")
        
        # Optional: Check if model is actually accessible via API
        if self.check_accessibility:
            try:
                # Try to list models from the API (if supported)
                available_models = await self.provider.list_models()
                model_names = [m["name"] for m in available_models]
                
                if self.model not in model_names:
                    warnings.append(
                        f"Model '{self.model}' is in our registry but not returned by the API. "
                        "It might be deprecated or require special access."
                    )
            except Exception as e:
                warnings.append(f"Could not verify model accessibility via API: {str(e)}")
        
        # Model is valid
        return ValidationResult(
            is_valid=True,
            message=f"Model '{self.model}' is available for {self.provider.provider_name}",
            warnings=warnings,
            context=context,
        )

