"""Factory for creating sessions and managing providers."""

from typing import Any, Optional

from ai_content_generator.core.config import Config
from ai_content_generator.core.exceptions import APIKeyMissingError, ConfigurationError
from ai_content_generator.core.provider import BaseProvider
from ai_content_generator.core.session import LLMSession


class SessionFactory:
    """
    Factory for creating LLM sessions with proper provider configuration.

    Manages provider instances and creates configured sessions.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        """
        Initialize the session factory.

        Args:
            config: Configuration object (if None, loads from environment)

        Example:
            ```python
            from ai_content_generator.core.config import Config

            config = Config.from_env()
            factory = SessionFactory(config)
            ```
        """
        self.config = config or Config.from_env()
        self._provider_cache: dict[str, BaseProvider] = {}

    def get_provider(self, name: str, **override_kwargs: Any) -> BaseProvider:
        """
        Get or create a provider instance.

        Args:
            name: Provider name (e.g., "openai", "anthropic")
            **override_kwargs: Override configuration parameters

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider is not configured
            APIKeyMissingError: If API key is missing

        Example:
            ```python
            provider = factory.get_provider("openai")
            ```
        """
        # Check if provider is already cached
        cache_key = f"{name}_{hash(frozenset(override_kwargs.items()))}"
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

        # Get provider configuration
        provider_config = self.config.get_provider_config(name)
        if provider_config is None:
            raise ConfigurationError(
                f"Provider '{name}' is not configured",
                context={"provider": name, "available_providers": list(self.config.providers.keys())},
            )

        # Check for API key
        api_key = override_kwargs.get("api_key") or provider_config.api_key
        if not api_key:
            raise APIKeyMissingError(provider=name)

        # Merge configuration with overrides
        provider_kwargs = {
            "api_key": api_key,
            "timeout": override_kwargs.get("timeout", provider_config.timeout),
            "max_retries": override_kwargs.get("max_retries", provider_config.max_retries),
        }

        # Import and instantiate provider
        # Note: Provider implementations will be added in the next phase
        provider_class = self._get_provider_class(name)
        provider = provider_class(**provider_kwargs)

        # Cache the provider
        self._provider_cache[cache_key] = provider

        return provider

    def _get_provider_class(self, name: str) -> type[BaseProvider]:
        """
        Get provider class by name.

        Args:
            name: Provider name

        Returns:
            Provider class

        Raises:
            ConfigurationError: If provider is not found
        """
        # Import providers dynamically to avoid circular imports
        # This will be properly implemented when provider classes are added
        try:
            if name == "openai":
                from ai_content_generator.providers.openai_provider import OpenAIProvider
                return OpenAIProvider
            elif name == "anthropic":
                from ai_content_generator.providers.anthropic_provider import AnthropicProvider
                return AnthropicProvider
            else:
                raise ConfigurationError(
                    f"Unknown provider: {name}",
                    context={"provider": name, "supported_providers": ["openai", "anthropic"]},
                )
        except ImportError as e:
            raise ConfigurationError(
                f"Provider '{name}' is not implemented yet",
                context={"provider": name, "error": str(e)},
            ) from e

    def create_session(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        budget_usd: Optional[float] = None,
        dry_run: Optional[bool] = None,
        metadata: Optional[dict[str, Any]] = None,
        **provider_kwargs: Any,
    ) -> LLMSession:
        """
        Create a new LLM session.

        Args:
            provider: Provider name (uses default from config if not specified)
            model: Model name (uses default from config if not specified)
            budget_usd: Budget limit in USD (uses default from config if not specified)
            dry_run: Dry run mode (uses default from config if not specified)
            metadata: Optional session metadata
            **provider_kwargs: Additional provider configuration

        Returns:
            LLMSession instance

        Raises:
            ConfigurationError: If configuration is invalid
            APIKeyMissingError: If API key is missing

        Example:
            ```python
            # Use defaults from config
            session = factory.create_session()

            # Override specific settings
            session = factory.create_session(
                provider="openai",
                model="gpt-4",
                budget_usd=5.0
            )

            # Use as context manager
            async with factory.create_session() as session:
                response = await session.chat("Hello!")
            ```
        """
        # Use defaults from config if not specified
        provider_name = provider or self.config.session.default_provider
        model_name = model or self.config.session.default_model

        # If model is still None, try to get default from provider config
        if model_name is None:
            provider_config = self.config.get_provider_config(provider_name)
            if provider_config and provider_config.default_model:
                model_name = provider_config.default_model

        if model_name is None:
            raise ConfigurationError(
                "No model specified and no default model configured",
                context={"provider": provider_name},
            )

        # Get budget from config if not specified
        if budget_usd is None:
            budget_usd = self.config.session.default_budget_usd

        # Get dry_run from config if not specified
        if dry_run is None:
            dry_run = self.config.session.dry_run

        # Get provider instance
        provider_instance = self.get_provider(provider_name, **provider_kwargs)

        # Create session
        session = LLMSession(
            provider=provider_instance,
            model=model_name,
            budget_usd=budget_usd,
            dry_run=dry_run,
            metadata=metadata,
        )

        # Set up default alerts from config
        for threshold in self.config.session.alerts:
            session.set_alert(
                threshold=threshold,
                callback=self._default_alert_callback,
            )

        return session

    @staticmethod
    def _default_alert_callback(current_cost: float, budget: float) -> None:
        """
        Default alert callback that prints to console.

        Args:
            current_cost: Current spending
            budget: Budget limit
        """
        percentage = (current_cost / budget) * 100
        print(
            f"⚠️  Budget Alert: ${current_cost:.4f} / ${budget:.2f} ({percentage:.1f}%) used"
        )

    def list_available_providers(self) -> list[str]:
        """
        List configured providers.

        Returns:
            List of provider names

        Example:
            ```python
            providers = factory.list_available_providers()
            print(f"Available providers: {providers}")
            ```
        """
        return list(self.config.providers.keys())

    def clear_cache(self) -> None:
        """
        Clear the provider cache.

        Useful for testing or when you need to recreate providers
        with different configurations.
        """
        self._provider_cache.clear()

    def __repr__(self) -> str:
        """String representation of the factory."""
        providers = self.list_available_providers()
        return f"SessionFactory(providers={providers})"

