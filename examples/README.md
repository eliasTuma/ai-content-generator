# AI Content Generator - Examples

This directory contains example scripts demonstrating how to use the AI Content Generator library.

## Prerequisites

1. Install the package:
```bash
pip install -e .
```

2. Set up your API keys:
```bash
# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Examples

### 01_basic_usage.py

Demonstrates basic provider usage including:
- Creating provider instances
- Validating connections
- Listing available models
- Getting model information
- Estimating costs
- Making chat requests
- Calculating actual costs

**Run:**
```bash
python examples/01_basic_usage.py
```

**Features:**
- Works with both OpenAI and Anthropic providers
- Shows token counting and cost tracking
- Demonstrates proper resource cleanup

### 02_session_usage.py

Demonstrates session management including:
- Using SessionFactory to create sessions
- Budget tracking and enforcement
- Budget alerts at thresholds
- Context manager usage
- Batch generation operations
- Session data export

**Run:**
```bash
python examples/02_session_usage.py
```

**Features:**
- Budget management with alerts
- Batch processing with budget checks
- Session statistics and metrics
- Automatic resource cleanup

## Example Output

### Basic Usage Example
```
🚀 AI Content Generator - Basic Usage Examples

============================================================
OpenAI Provider Example
============================================================

1. Validating connection...
   Connection valid: True

2. Available models:
   - gpt-4: $30.0/1M input tokens
   - gpt-4-32k: $60.0/1M input tokens
   - gpt-4-turbo: $10.0/1M input tokens

3. Model details (gpt-4o-mini):
   Context window: 128,000 tokens
   Input price: $0.15/1M tokens
   Output price: $0.6/1M tokens

4. Cost estimation for prompt: 'Write a short haiku about Python programming.'
   Input tokens: 10
   Estimated cost: $0.000062

5. Making chat request...

   Response: Code flows like water,
   Elegant and simple,
   Python's zen unfolds.

   Tokens used:
   - Input: 27
   - Output: 19

   Actual cost: $0.000015

✅ OpenAI example completed!
```

### Session Usage Example
```
🚀 AI Content Generator - Session Usage Examples

============================================================
Session with Budget Tracking Example
============================================================

1. Available providers:
   openai

2. Creating session with $0.10 budget...
   Session created: session_20251018_143022_abc123
   Budget: $0.10
   Model: gpt-4o-mini

3. Making first request...
   Response: Python is a high-level, interpreted programming language...
   Cost: $0.000012
   Budget remaining: $0.099988

4. Making second request...
   Response: Async programming allows concurrent execution...
   Cost: $0.000024
   Budget remaining: $0.099976

5. Session statistics:
   Total requests: 2
   Total tokens: 156
   Total cost: $0.000024
   Budget used: 0.0%

✅ Session example completed!
```

## Notes

- Examples use the cheapest models by default (gpt-4o-mini, claude-3-haiku)
- Real API calls are made, so costs will be incurred
- Budget limits are set low to prevent excessive spending
- All examples use async/await pattern
- Proper error handling is demonstrated

## Next Steps

After running these examples, explore:
- Creating custom configurations
- Implementing custom validators
- Building addons for caching and retry logic
- Integrating with your application

## Troubleshooting

**Issue**: `OPENAI_API_KEY not set`
- **Solution**: Set the environment variable or create a `.env` file

**Issue**: `Connection valid: False`
- **Solution**: Check your API key is correct and has sufficient credits

**Issue**: `ModuleNotFoundError: No module named 'ai_content_generator'`
- **Solution**: Install the package with `pip install -e .`

**Issue**: Budget exceeded
- **Solution**: Increase the budget_usd parameter or use cheaper models

## Support

For more information, see:
- Main README: `../README.md`
- API Documentation: `../docs/API.md`
- Architecture: `../docs/ARCHITECTURE.md`

