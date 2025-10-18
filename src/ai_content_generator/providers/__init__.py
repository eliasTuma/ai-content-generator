"""Provider implementations and registry."""

from typing import Any, Optional

from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from ..core.provider import BaseProvider
from ..core.exceptions import ProviderError


# Provider registry mapping provider names to their classes
PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: str, **kwargs: Any) -> BaseProvider:
    """
    Factory function to get a provider instance by name.

    Args:
        name: Name of the provider (e.g., "openai", "anthropic")
        **kwargs: Provider-specific configuration (must include api_key)

    Returns:
        Provider instance

    Raises:
        ProviderError: If provider is not found or configuration is invalid

    Example:
        ```python
        provider = get_provider("openai", api_key="sk-...")
        response = await provider.chat(messages, model="gpt-4o-mini")
        ```
    """
    name_lower = name.lower()

    if name_lower not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ProviderError(
            message=f"Provider '{name}' not found",
            provider=name,
            context={"available_providers": available},
        )

    provider_class = PROVIDER_REGISTRY[name_lower]

    # Check if api_key is provided
    if "api_key" not in kwargs:
        raise ProviderError(
            message=f"API key is required for provider '{name}'",
            provider=name,
            context={"required_parameter": "api_key"},
        )

    try:
        return provider_class(**kwargs)
    except Exception as e:
        raise ProviderError(
            message=f"Failed to initialize provider '{name}': {str(e)}",
            provider=name,
            context={"error": str(e), "error_type": type(e).__name__},
        )


def list_providers() -> list[str]:
    """
    Get list of available provider names.

    Returns:
        List of provider names

    Example:
        ```python
        providers = list_providers()
        print(f"Available providers: {', '.join(providers)}")
        ```
    """
    return list(PROVIDER_REGISTRY.keys())


def register_provider(name: str, provider_class: type[BaseProvider]) -> None:
    """
    Register a custom provider.

    This allows users to add their own provider implementations.

    Args:
        name: Name to register the provider under
        provider_class: Provider class (must inherit from BaseProvider)

    Raises:
        ProviderError: If provider_class doesn't inherit from BaseProvider

    Example:
        ```python
        class MyCustomProvider(BaseProvider):
            # ... implementation ...
            pass

        register_provider("custom", MyCustomProvider)
        provider = get_provider("custom", api_key="...")
        ```
    """
    if not issubclass(provider_class, BaseProvider):
        raise ProviderError(
            message=f"Provider class must inherit from BaseProvider",
            provider=name,
            context={"provided_class": str(provider_class)},
        )

    PROVIDER_REGISTRY[name.lower()] = provider_class


def get_all_available_models() -> dict[str, list[dict[str, Any]]]:
    """
    Get all available models from all registered providers.

    Returns:
        Dictionary mapping provider names to their available models

    Example:
        ```python
        all_models = get_all_available_models()
        for provider_name, models in all_models.items():
            print(f"\n{provider_name.upper()} Models:")
            for model in models:
                print(f"  - {model['name']}: {model['description']}")
        ```
    """
    all_models = {}
    for provider_name, provider_class in PROVIDER_REGISTRY.items():
        # Check if provider has static get_available_models method
        if hasattr(provider_class, 'get_available_models'):
            all_models[provider_name] = provider_class.get_available_models()
    return all_models


def get_all_model_names() -> dict[str, list[str]]:
    """
    Get all model names from all registered providers.

    Returns:
        Dictionary mapping provider names to their model name lists

    Example:
        ```python
        all_names = get_all_model_names()
        print(f"OpenAI models: {all_names['openai']}")
        print(f"Anthropic models: {all_names['anthropic']}")
        ```
    """
    all_names = {}
    for provider_name, provider_class in PROVIDER_REGISTRY.items():
        # Check if provider has static get_model_names method
        if hasattr(provider_class, 'get_model_names'):
            all_names[provider_name] = provider_class.get_model_names()
    return all_names


__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "get_provider",
    "list_providers",
    "register_provider",
    "get_all_available_models",
    "get_all_model_names",
    "PROVIDER_REGISTRY",
]
