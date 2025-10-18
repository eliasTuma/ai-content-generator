"""
AI Content Generator - Multi-provider LLM client with budget tracking and monitoring.

A Python library for generating AI content with built-in cost tracking, budget management,
and support for multiple LLM providers (OpenAI, Anthropic, etc.).
"""

__version__ = "0.1.0"
__author__ = "AI Academy"

from ai_content_generator.core.config import Config
from ai_content_generator.core.exceptions import (
    AIContentGeneratorError,
    APIKeyMissingError,
    BudgetExceededError,
    ConfigurationError,
    ProviderError,
    ValidationError,
)
from ai_content_generator.core.factory import SessionFactory
from ai_content_generator.core.session import LLMSession
from ai_content_generator.providers import (
    OpenAIProvider,
    AnthropicProvider,
    get_provider,
    list_providers,
)

__all__ = [
    "AIContentGeneratorError",
    "AnthropicProvider",
    "APIKeyMissingError",
    "BudgetExceededError",
    "Config",
    "ConfigurationError",
    "LLMSession",
    "OpenAIProvider",
    "ProviderError",
    "SessionFactory",
    "ValidationError",
    "__version__",
    "get_provider",
    "list_providers",
]

