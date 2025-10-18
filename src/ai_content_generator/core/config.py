"""Configuration management with Pydantic validation."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from ai_content_generator.core.exceptions import ConfigurationError


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    name: str
    input_price_per_1m: float = Field(gt=0, description="Price per 1M input tokens in USD")
    output_price_per_1m: float = Field(gt=0, description="Price per 1M output tokens in USD")
    context_window: int = Field(gt=0, description="Maximum context window size")


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    api_key: Optional[str] = None
    timeout: int = Field(default=60, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    default_model: Optional[str] = None
    models: list[ModelConfig] = Field(default_factory=list)


class SessionConfig(BaseModel):
    """Default session configuration."""

    default_budget_usd: Optional[float] = Field(default=None, ge=0)
    default_provider: str = "openai"
    default_model: Optional[str] = None
    dry_run: bool = False
    alerts: list[float] = Field(
        default_factory=lambda: [0.5, 0.75, 0.9],
        description="Budget alert thresholds (0.0 to 1.0)",
    )

    @field_validator("alerts")
    @classmethod
    def validate_alerts(cls, v: list[float]) -> list[float]:
        """Validate alert thresholds."""
        for threshold in v:
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"Alert threshold must be between 0.0 and 1.0, got {threshold}")
        return sorted(v)  # Sort for efficiency


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    console_enabled: bool = True
    console_level: str = "INFO"
    console_colored: bool = True
    file_enabled: bool = True
    file_level: str = "DEBUG"
    file_path: str = "logs/ai_content_generator.log"
    file_rotation: str = "daily"  # daily, size, or none
    file_max_files: int = 7
    file_max_size_mb: int = 10

    @field_validator("level", "console_level", "file_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}, got {v}")
        return v_upper


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    ttl: int = Field(default=3600, gt=0, description="Time to live in seconds")
    max_size: int = Field(default=100, gt=0, description="Maximum cache entries")
    strategy: str = "lru"  # LRU eviction strategy

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate cache strategy."""
        valid_strategies = ["lru"]
        if v.lower() not in valid_strategies:
            raise ValueError(f"Cache strategy must be one of {valid_strategies}, got {v}")
        return v.lower()


class RetryConfig(BaseModel):
    """Retry configuration."""

    enabled: bool = True
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay: float = Field(default=1.0, gt=0)
    max_delay: float = Field(default=60.0, gt=0)
    exponential_base: float = Field(default=2.0, gt=1.0)
    jitter: bool = True
    retry_on: list[str] = Field(
        default_factory=lambda: ["rate_limit", "timeout", "connection_error", "server_error"]
    )


class Config(BaseModel):
    """Main configuration class."""

    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    session: SessionConfig = Field(default_factory=SessionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @classmethod
    def from_file(cls, filepath: str | Path) -> "Config":
        """
        Load configuration from a YAML file.

        Supports environment variable interpolation using ${VAR_NAME} syntax.

        Args:
            filepath: Path to YAML configuration file

        Returns:
            Config instance

        Raises:
            ConfigurationError: If file cannot be loaded or parsed

        Example:
            ```python
            config = Config.from_file("config/config.yaml")
            ```
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise ConfigurationError(
                f"Configuration file not found: {filepath}",
                context={"filepath": str(filepath)},
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Interpolate environment variables
            content = cls._interpolate_env_vars(content)

            # Parse YAML
            data = yaml.safe_load(content)

            if data is None:
                data = {}

            return cls(**data)

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration: {e}",
                context={"filepath": str(filepath)},
            ) from e
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                context={"filepath": str(filepath)},
            ) from e

    @classmethod
    def from_env(cls, env_file: Optional[str | Path] = None) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file to load first

        Returns:
            Config instance

        Example:
            ```python
            config = Config.from_env(".env")
            ```
        """
        # Load .env file if provided
        if env_file:
            load_dotenv(env_file)

        # Build configuration from environment variables
        providers_config: dict[str, Any] = {}

        # OpenAI provider
        if openai_key := os.getenv("OPENAI_API_KEY"):
            providers_config["openai"] = {
                "api_key": openai_key,
                "timeout": int(os.getenv("AI_CONTENT_GEN_TIMEOUT", "60")),
                "max_retries": int(os.getenv("AI_CONTENT_GEN_MAX_RETRIES", "3")),
            }

        # Anthropic provider
        if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
            providers_config["anthropic"] = {
                "api_key": anthropic_key,
                "timeout": int(os.getenv("AI_CONTENT_GEN_TIMEOUT", "60")),
                "max_retries": int(os.getenv("AI_CONTENT_GEN_MAX_RETRIES", "3")),
            }

        # Session configuration
        session_config = {
            "default_budget_usd": (
                float(budget) if (budget := os.getenv("AI_CONTENT_GEN_DEFAULT_BUDGET")) else None
            ),
            "default_provider": os.getenv("AI_CONTENT_GEN_DEFAULT_PROVIDER", "openai"),
            "default_model": os.getenv("AI_CONTENT_GEN_DEFAULT_MODEL"),
        }

        # Logging configuration
        logging_config = {
            "level": os.getenv("AI_CONTENT_GEN_LOG_LEVEL", "INFO"),
            "file_path": os.getenv("AI_CONTENT_GEN_LOG_FILE", "logs/ai_content_generator.log"),
        }

        # Cache configuration
        cache_config = {
            "enabled": os.getenv("AI_CONTENT_GEN_ENABLE_CACHE", "true").lower() == "true",
            "ttl": int(os.getenv("AI_CONTENT_GEN_CACHE_TTL", "3600")),
            "max_size": int(os.getenv("AI_CONTENT_GEN_CACHE_MAX_SIZE", "100")),
        }

        return cls(
            providers=providers_config,
            session=SessionConfig(**session_config),
            logging=LoggingConfig(**logging_config),
            cache=CacheConfig(**cache_config),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """
        Load configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance

        Example:
            ```python
            config = Config.from_dict({
                "session": {"default_budget_usd": 10.0},
                "logging": {"level": "DEBUG"}
            })
            ```
        """
        return cls(**data)

    @staticmethod
    def _interpolate_env_vars(content: str) -> str:
        """
        Interpolate environment variables in content.

        Replaces ${VAR_NAME} with the value of the environment variable.

        Args:
            content: String content with potential ${VAR_NAME} references

        Returns:
            Content with environment variables interpolated
        """
        import re

        def replace_env_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}", replace_env_var, content)

    def to_dict(self) -> dict[str, Any]:
        """
        Export configuration as a dictionary.

        Returns:
            Configuration dictionary

        Example:
            ```python
            config_dict = config.to_dict()
            ```
        """
        return self.model_dump()

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderConfig if found, None otherwise
        """
        return self.providers.get(provider_name)

    def __repr__(self) -> str:
        """String representation of the config."""
        provider_names = list(self.providers.keys())
        return f"Config(providers={provider_names})"

