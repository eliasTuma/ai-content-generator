# AI Content Generator

A Python library for generating AI content with built-in cost tracking, budget management, and support for multiple LLM providers (OpenAI, Anthropic).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- **Multi-Provider Support**: OpenAI and Anthropic with unified interface
- **Budget Management**: Set spending limits and get alerts before exceeding them
- **Cost Tracking**: Real-time cost monitoring and detailed breakdowns
- **Token Monitoring**: Track input/output tokens across all requests
- **Session Management**: Organize requests into sessions with metadata
- **Batch Processing**: Process multiple items efficiently with budget checks
- **Async/Await**: Built on asyncio for high-performance concurrent operations
- **Addon System**: Extensible with cache, retry, dry-run, and custom addons
- **Type Safety**: Full type hints and mypy compatibility
- **Model Discovery**: Browse and compare models without instantiation

## Installation

### Basic Installation

```bash
pip install ai-content-generator
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/ai-academy/ai-content-generator.git
cd ai-content-generator

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Optional Dependencies

```bash
# For CLI tools (not yet implemented)
pip install ai-content-generator[cli]

# For documentation generation
pip install ai-content-generator[docs]
```

## Quick Start

### 1. Set Up API Keys

```bash
# Add to your .env file or export as environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Basic Usage

```python
import asyncio
from ai_content_generator import OpenAIProvider

async def main():
    # Create provider
    provider = OpenAIProvider(api_key="sk-...")
    
    # Make a request
    messages = [{"role": "user", "content": "Write a haiku about Python"}]
    response = await provider.chat(messages, model="gpt-4o-mini")
    
    print(response["content"])
    print(f"Cost: ${provider.calculate_cost(response['input_tokens'], response['output_tokens'], 'gpt-4o-mini'):.6f}")
    
    await provider.__aexit__(None, None, None)

asyncio.run(main())
```

### 3. Session with Budget Tracking

```python
import asyncio
from ai_content_generator import Config, SessionFactory

async def main():
    # Create configuration
    config = Config.from_dict({
        "providers": {
            "openai": {
                "api_key": "sk-...",
                "default_model": "gpt-4o-mini"
            }
        },
        "session": {
            "default_provider": "openai",
            "default_budget_usd": 1.0
        }
    })
    
    # Create session with budget
    factory = SessionFactory(config)
    async with factory.create_session(budget_usd=1.0) as session:
        # Make requests
        response = await session.chat("Explain async programming in one sentence")
        
        print(f"Response: {response['content']}")
        print(f"Cost: ${session.cost_usd:.6f}")
        print(f"Budget remaining: ${session.budget_remaining:.6f}")

asyncio.run(main())
```

## Core Concepts

### Providers

Providers are the interface to LLM APIs. Each provider implements the same interface for consistency.

**Available Providers:**
- `OpenAIProvider` - OpenAI GPT models
- `AnthropicProvider` - Anthropic Claude models

**Provider Features:**
- Connection validation
- Model listing and discovery
- Cost estimation
- Token counting
- Unified chat interface

### Sessions

Sessions organize related requests and provide budget tracking, cost monitoring, and metadata management.

**Key Features:**
- Budget enforcement with alerts
- Token and cost tracking
- Request history
- Batch processing
- Export to JSON/dict

### Configuration

Configuration can be loaded from YAML files, dictionaries, or environment variables.

```python
from ai_content_generator import Config

# From dictionary
config = Config.from_dict({...})

# From YAML file
config = Config.from_yaml("config.yaml")

# From environment variables
config = Config.from_env()
```

### Addons

Addons extend functionality without modifying core code. Available addons:

- **CacheAddon**: Cache responses to avoid duplicate API calls
- **RetryAddon**: Automatic retry with exponential backoff
- **DryRunAddon**: Simulate requests without calling APIs
- **ResponseValidatorAddon**: Validate responses against schemas

## Usage Examples

### Example 1: Provider Basics

```python
import asyncio
from ai_content_generator import OpenAIProvider

async def main():
    provider = OpenAIProvider(api_key="sk-...")
    
    # Validate connection
    is_valid = await provider.validate_connection()
    print(f"Connection valid: {is_valid}")
    
    # List available models
    models = await provider.list_models()
    for model in models[:3]:
        print(f"{model['name']}: ${model['input_price_per_1m']}/1M tokens")
    
    # Estimate cost before making request
    estimate = await provider.estimate_cost(
        "Write a blog post about AI",
        model="gpt-4o-mini",
        max_tokens=500
    )
    print(f"Estimated cost: ${estimate['total_cost']:.6f}")
    
    # Make request
    messages = [{"role": "user", "content": "Hello!"}]
    response = await provider.chat(messages, model="gpt-4o-mini")
    print(response["content"])
    
    await provider.__aexit__(None, None, None)

asyncio.run(main())
```

### Example 2: Budget-Controlled Session

```python
import asyncio
from ai_content_generator import Config, SessionFactory

async def main():
    config = Config.from_dict({
        "providers": {
            "openai": {"api_key": "sk-...", "default_model": "gpt-4o-mini"}
        },
        "session": {
            "default_provider": "openai",
            "default_budget_usd": 0.50,
            "alerts": [0.5, 0.8, 0.9]  # Alert at 50%, 80%, 90%
        }
    })
    
    factory = SessionFactory(config)
    
    async with factory.create_session(budget_usd=0.50) as session:
        # Set up budget alerts
        session.alert_manager.add_alert(
            threshold=0.8,
            callback=lambda: print("⚠️ 80% of budget used!")
        )
        
        # Make requests
        for i in range(5):
            try:
                response = await session.chat(
                    f"Write fact #{i+1} about Python",
                    max_tokens=50
                )
                print(f"\n{i+1}. {response['content']}")
                print(f"   Cost: ${session.cost_usd:.6f} / ${session.budget_usd:.2f}")
            except BudgetExceededError:
                print(f"\n❌ Budget exceeded after {i} requests")
                break

asyncio.run(main())
```

### Example 3: Batch Processing

```python
import asyncio
from ai_content_generator import Config, SessionFactory

async def main():
    config = Config.from_dict({
        "providers": {
            "openai": {"api_key": "sk-...", "default_model": "gpt-4o-mini"}
        }
    })
    
    factory = SessionFactory(config)
    
    async with factory.create_session(budget_usd=1.0) as session:
        # Define items to process
        topics = ["Python", "JavaScript", "Rust", "Go", "TypeScript"]
        
        # Process function
        async def generate_description(topic: str) -> dict:
            response = await session.chat(
                f"Write a one-sentence description of {topic}",
                max_tokens=50
            )
            return {"topic": topic, "description": response["content"]}
        
        # Batch generate with budget checking
        results = await session.batch_generate(
            items=topics,
            process_func=generate_description,
            check_budget_per_item=True
        )
        
        # Display results
        for result in results:
            print(f"\n{result['topic']}:")
            print(f"  {result['description']}")
        
        print(f"\nTotal cost: ${session.cost_usd:.6f}")
        print(f"Average per item: ${session.cost_usd / len(results):.6f}")

asyncio.run(main())
```

### Example 4: Using Addons

```python
import asyncio
from ai_content_generator import OpenAIProvider
from ai_content_generator.addons import CacheAddon, RetryAddon, AddonManager, AddonContext
from ai_content_generator.utils import generate_request_id

async def main():
    # Create addons
    cache = CacheAddon(max_size=100, ttl_seconds=3600)
    retry = RetryAddon(max_retries=3, initial_delay=1.0)
    
    # Create addon manager
    manager = AddonManager()
    manager.add_addon(cache)
    manager.add_addon(retry)
    
    # Use with provider
    provider = OpenAIProvider(api_key="sk-...")
    
    prompt = "What is Python?"
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-4o-mini",
        provider="openai"
    )
    
    # First request - cache miss
    cached = await manager.execute_pre_request(prompt, context)
    if not cached:
        messages = [{"role": "user", "content": prompt}]
        response = await provider.chat(messages, model="gpt-4o-mini")
        await manager.execute_post_request(response, context)
        print(f"Response: {response['content']}")
    
    # Second request - cache hit
    context2 = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-4o-mini",
        provider="openai"
    )
    cached = await manager.execute_pre_request(prompt, context2)
    if cached:
        print(f"Cached response: {cached['content']}")
    
    # Show cache stats
    stats = cache.get_stats()
    print(f"\nCache hit rate: {stats['hit_rate']:.2%}")
    
    await provider.__aexit__(None, None, None)

asyncio.run(main())
```

### Example 5: Model Discovery

```python
from ai_content_generator.providers import (
    OpenAIProvider,
    AnthropicProvider,
    get_all_available_models,
    list_providers
)

# List all providers
providers = list_providers()
print(f"Available providers: {', '.join(providers)}")

# Get all models
all_models = get_all_available_models()

for provider, models in all_models.items():
    print(f"\n{provider.upper()} Models:")
    for model in models[:3]:
        print(f"  {model['name']}")
        print(f"    Input: ${model['input_price_per_1m']}/1M tokens")
        print(f"    Output: ${model['output_price_per_1m']}/1M tokens")
        print(f"    Context: {model['context_window']:,} tokens")

# Find budget-friendly models
openai_models = OpenAIProvider.get_available_models()
budget_models = [m for m in openai_models if m['input_price_per_1m'] < 1.0]

print("\nBudget-friendly models (< $1/1M):")
for model in budget_models:
    print(f"  {model['name']}: ${model['input_price_per_1m']}/1M")
```

### Example 6: Multiple Providers

```python
import asyncio
from ai_content_generator import Config, SessionFactory

async def main():
    config = Config.from_dict({
        "providers": {
            "openai": {
                "api_key": "sk-...",
                "default_model": "gpt-4o-mini"
            },
            "anthropic": {
                "api_key": "sk-ant-...",
                "default_model": "claude-3-haiku-20240307"
            }
        }
    })
    
    factory = SessionFactory(config)
    
    # Use OpenAI
    async with factory.create_session(provider="openai") as session:
        response = await session.chat("Hello from OpenAI!")
        print(f"OpenAI: {response['content']}")
        print(f"Cost: ${session.cost_usd:.6f}")
    
    # Use Anthropic
    async with factory.create_session(provider="anthropic") as session:
        response = await session.chat("Hello from Anthropic!")
        print(f"\nAnthropic: {response['content']}")
        print(f"Cost: ${session.cost_usd:.6f}")

asyncio.run(main())
```

## Configuration

### YAML Configuration

Create a `config.yaml` file (see `config/config.yaml.example`):

```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    timeout: 60
    max_retries: 3
    default_model: gpt-4o-mini

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    timeout: 60
    max_retries: 3
    default_model: claude-3-haiku-20240307

session:
  default_budget_usd: 10.0
  default_provider: openai
  dry_run: false
  alerts:
    - 0.5   # Alert at 50%
    - 0.8   # Alert at 80%
    - 0.9   # Alert at 90%

logging:
  level: INFO
  console:
    enabled: true
    colored: true
  file:
    enabled: true
    path: logs/ai_content_generator.log

cache:
  enabled: true
  ttl: 3600
  max_size: 100

retry:
  enabled: true
  max_attempts: 3
  initial_delay: 1.0
  exponential_base: 2.0
```

### Load Configuration

```python
from ai_content_generator import Config

# From YAML file
config = Config.from_yaml("config.yaml")

# From dictionary
config = Config.from_dict({
    "providers": {
        "openai": {"api_key": "sk-..."}
    }
})

# From environment variables
config = Config.from_env()
```

## API Reference

### Providers

#### OpenAIProvider

```python
from ai_content_generator import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",
    timeout=60,
    max_retries=3
)

# Validate connection
is_valid = await provider.validate_connection()

# List models
models = await provider.list_models()

# Get model info
info = await provider.get_model_info("gpt-4o-mini")

# Estimate cost
estimate = await provider.estimate_cost(prompt, model="gpt-4o-mini", max_tokens=100)

# Chat
response = await provider.chat(messages, model="gpt-4o-mini", max_tokens=100)

# Calculate cost
cost = provider.calculate_cost(input_tokens, output_tokens, model="gpt-4o-mini")
```

#### AnthropicProvider

```python
from ai_content_generator import AnthropicProvider

provider = AnthropicProvider(
    api_key="sk-ant-...",
    timeout=60,
    max_retries=3
)

# Same interface as OpenAIProvider
response = await provider.chat(messages, model="claude-3-haiku-20240307")
```

### Sessions

#### LLMSession

```python
from ai_content_generator import LLMSession

async with LLMSession(provider, model="gpt-4o-mini", budget_usd=1.0) as session:
    # Chat
    response = await session.chat("Hello", max_tokens=50)
    
    # Batch generate
    results = await session.batch_generate(items, process_func)
    
    # Properties
    print(session.cost_usd)
    print(session.tokens_used)
    print(session.budget_remaining)
    print(session.request_count)
    
    # Export
    data = session.export_to_dict()
    await session.save_to_file("session.json")
```

### Configuration

#### Config

```python
from ai_content_generator import Config

# Load configuration
config = Config.from_yaml("config.yaml")
config = Config.from_dict({...})
config = Config.from_env()

# Access settings
provider_config = config.get_provider_config("openai")
session_config = config.get_session_config()
```

### Exceptions

```python
from ai_content_generator import (
    AIContentGeneratorError,      # Base exception
    APIKeyMissingError,            # API key not provided
    BudgetExceededError,           # Budget limit exceeded
    ConfigurationError,            # Invalid configuration
    ProviderError,                 # Provider-specific error
    ValidationError                # Validation failed
)
```

## Advanced Features

### Custom Addons

Create custom addons by extending `BaseAddon`:

```python
from ai_content_generator.addons import BaseAddon, AddonContext

class CustomAddon(BaseAddon):
    def get_name(self) -> str:
        return "custom"
    
    def get_description(self) -> str:
        return "My custom addon"
    
    async def pre_request(self, prompt: str, context: AddonContext) -> str | None:
        # Modify prompt or return cached response
        print(f"Processing: {prompt}")
        return None  # Continue to API
    
    async def post_request(self, response: dict, context: AddonContext) -> dict:
        # Modify response
        response["custom_field"] = "added by addon"
        return response
```

### Cost Optimization

```python
# Use cheaper models for simple tasks
simple_response = await session.chat(
    "What is 2+2?",
    model="gpt-4o-mini",  # Cheaper model
    max_tokens=10
)

# Use expensive models for complex tasks
complex_response = await session.chat(
    "Write a detailed analysis...",
    model="gpt-4",  # More capable model
    max_tokens=1000
)

# Estimate before requesting
estimate = await provider.estimate_cost(prompt, model="gpt-4", max_tokens=1000)
if estimate["total_cost"] < 0.10:
    response = await provider.chat(messages, model="gpt-4")
```

### Monitoring and Alerts

```python
# Add custom alert callbacks
session.alert_manager.add_alert(
    threshold=0.5,
    callback=lambda: print("50% budget used")
)

session.alert_manager.add_alert(
    threshold=0.9,
    callback=lambda: send_email("Budget warning!")
)

# Check budget before expensive operations
if session.budget_remaining and session.budget_remaining < 0.10:
    print("Low budget, switching to cheaper model")
    response = await session.chat(prompt, model="gpt-4o-mini")
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/ai-academy/ai-content-generator.git
cd ai-content-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ai_content_generator --cov-report=html

# Run specific test file
pytest tests/unit/test_providers.py

# Run integration tests (requires API keys)
pytest tests/integration/ -m integration
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

### Project Structure

```
ai-content-generator/
├── src/
│   └── ai_content_generator/
│       ├── core/              # Core functionality
│       │   ├── config.py      # Configuration management
│       │   ├── exceptions.py  # Custom exceptions
│       │   ├── factory.py     # Session factory
│       │   ├── provider.py    # Base provider
│       │   └── session.py     # Session management
│       ├── providers/         # LLM providers
│       │   ├── openai_provider.py
│       │   └── anthropic_provider.py
│       ├── monitoring/        # Cost & token tracking
│       │   ├── alerts.py
│       │   ├── cost_tracker.py
│       │   └── token_monitor.py
│       ├── addons/           # Extensible addons
│       │   ├── cache.py
│       │   ├── retry.py
│       │   └── dry_run.py
│       ├── logging/          # Logging system
│       ├── validators/       # Input validation
│       └── utils/            # Utility functions
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── examples/                # Usage examples
├── config/                  # Configuration templates
└── docs/                    # Documentation
```

## Examples

See the `examples/` directory for complete working examples:

- `01_basic_usage.py` - Provider basics and simple requests
- `02_session_usage.py` - Sessions with budget tracking
- `03_with_addons.py` - Using cache, retry, and dry-run addons
- `04_model_discovery.py` - Discovering and comparing models

Run examples:

```bash
# Set API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run example
python examples/01_basic_usage.py
```

## Roadmap

- [ ] Streaming support for real-time responses
- [ ] Function calling / tool use
- [ ] More providers (Google, Cohere, etc.)
- [ ] CLI tool for quick interactions
- [ ] Web UI for session management
- [ ] Database logging for analytics
- [ ] Advanced caching strategies
- [ ] Prompt templates and chains
- [ ] Response validation schemas
- [ ] Multi-model orchestration

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`pytest && black . && ruff check .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [GitHub Docs](https://github.com/ai-academy/ai-content-generator/docs)
- **Issues**: [GitHub Issues](https://github.com/ai-academy/ai-content-generator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ai-academy/ai-content-generator/discussions)

## Acknowledgments

- Built with [OpenAI](https://openai.com/) and [Anthropic](https://anthropic.com/) APIs
- Inspired by the need for cost-effective AI content generation in education
- Thanks to all contributors and users

---

**Made with ❤️ by AI Academy**
