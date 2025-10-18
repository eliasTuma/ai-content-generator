"""
Basic usage example for AI Content Generator.

This example demonstrates:
- Creating a provider instance
- Validating connection
- Listing available models
- Making a simple chat request
- Tracking tokens and cost
"""

import asyncio
import os
from ai_content_generator import OpenAIProvider, AnthropicProvider


async def openai_example():
    """Example using OpenAI provider."""
    print("=" * 60)
    print("OpenAI Provider Example")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set. Skipping OpenAI example.")
        return

    # Create provider instance
    provider = OpenAIProvider(api_key=api_key)

    # Validate connection
    print("\n1. Validating connection...")
    is_valid = await provider.validate_connection()
    print(f"   Connection valid: {is_valid}")

    if not is_valid:
        print("   Failed to connect to OpenAI")
        return

    # List available models
    print("\n2. Available models:")
    models = await provider.list_models()
    for model in models[:3]:  # Show first 3 models
        print(f"   - {model['name']}: ${model['input_price_per_1m']}/1M input tokens")

    # Get specific model info
    print("\n3. Model details (gpt-4o-mini):")
    model_info = await provider.get_model_info("gpt-4o-mini")
    print(f"   Context window: {model_info['context_window']:,} tokens")
    print(f"   Input price: ${model_info['input_price_per_1m']}/1M tokens")
    print(f"   Output price: ${model_info['output_price_per_1m']}/1M tokens")

    # Estimate cost
    prompt = "Write a short haiku about Python programming."
    print(f"\n4. Cost estimation for prompt: '{prompt}'")
    estimate = await provider.estimate_cost(prompt, model="gpt-4o-mini", max_tokens=100)
    print(f"   Input tokens: {estimate['input_tokens']}")
    print(f"   Estimated cost: ${estimate['total_cost']:.6f}")

    # Make a chat request
    print("\n5. Making chat request...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]

    response = await provider.chat(messages, model="gpt-4o-mini", max_tokens=100)

    print(f"\n   Response: {response['content']}")
    print(f"\n   Tokens used:")
    print(f"   - Input: {response['input_tokens']}")
    print(f"   - Output: {response['output_tokens']}")

    # Calculate actual cost
    cost = provider.calculate_cost(
        response['input_tokens'],
        response['output_tokens'],
        model="gpt-4o-mini"
    )
    print(f"\n   Actual cost: ${cost:.6f}")

    # Close the client
    await provider.__aexit__(None, None, None)
    print("\n✅ OpenAI example completed!")


async def anthropic_example():
    """Example using Anthropic provider."""
    print("\n" + "=" * 60)
    print("Anthropic Provider Example")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set. Skipping Anthropic example.")
        return

    # Create provider instance
    provider = AnthropicProvider(api_key=api_key)

    # Validate connection
    print("\n1. Validating connection...")
    is_valid = await provider.validate_connection()
    print(f"   Connection valid: {is_valid}")

    if not is_valid:
        print("   Failed to connect to Anthropic")
        return

    # List available models
    print("\n2. Available models:")
    models = await provider.list_models()
    for model in models[:3]:  # Show first 3 models
        print(f"   - {model['name']}: ${model['input_price_per_1m']}/1M input tokens")

    # Get specific model info
    print("\n3. Model details (claude-3-haiku-20240307):")
    model_info = await provider.get_model_info("claude-3-haiku-20240307")
    print(f"   Context window: {model_info['context_window']:,} tokens")
    print(f"   Input price: ${model_info['input_price_per_1m']}/1M tokens")
    print(f"   Output price: ${model_info['output_price_per_1m']}/1M tokens")

    # Estimate cost
    prompt = "Write a short haiku about Python programming."
    print(f"\n4. Cost estimation for prompt: '{prompt}'")
    estimate = await provider.estimate_cost(
        prompt, model="claude-3-haiku-20240307", max_tokens=100
    )
    print(f"   Input tokens: {estimate['input_tokens']}")
    print(f"   Estimated cost: ${estimate['total_cost']:.6f}")

    # Make a chat request
    print("\n5. Making chat request...")
    messages = [
        {"role": "user", "content": prompt}
    ]

    response = await provider.chat(
        messages, model="claude-3-haiku-20240307", max_tokens=100
    )

    print(f"\n   Response: {response['content']}")
    print(f"\n   Tokens used:")
    print(f"   - Input: {response['input_tokens']}")
    print(f"   - Output: {response['output_tokens']}")

    # Calculate actual cost
    cost = provider.calculate_cost(
        response['input_tokens'],
        response['output_tokens'],
        model="claude-3-haiku-20240307"
    )
    print(f"\n   Actual cost: ${cost:.6f}")

    # Close the client
    await provider.__aexit__(None, None, None)
    print("\n✅ Anthropic example completed!")


async def main():
    """Run all examples."""
    print("\n🚀 AI Content Generator - Basic Usage Examples\n")

    # Run OpenAI example
    await openai_example()

    # Run Anthropic example
    await anthropic_example()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

