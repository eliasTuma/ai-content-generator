"""
Model discovery example.

This example demonstrates:
- Discovering available models without instantiation
- Listing models from all providers
- Comparing model pricing
- Finding the right model for your needs
"""

import asyncio
from ai_content_generator.providers import (
    OpenAIProvider,
    AnthropicProvider,
    get_all_available_models,
    get_all_model_names,
    list_providers,
)


def discover_models():
    """Discover available models across all providers."""
    print("=" * 60)
    print("Model Discovery")
    print("=" * 60)
    
    # List available providers
    print("\n1. Available providers:")
    providers = list_providers()
    for provider in providers:
        print(f"   - {provider}")
    
    # Get all model names
    print("\n2. Model names by provider:")
    all_names = get_all_model_names()
    for provider, models in all_names.items():
        print(f"\n   {provider.upper()} ({len(models)} models):")
        for model in models[:5]:  # Show first 5
            print(f"     - {model}")
        if len(models) > 5:
            print(f"     ... and {len(models) - 5} more")
    
    # Get detailed model information
    print("\n3. Detailed model information:")
    all_models = get_all_available_models()
    
    for provider, models in all_models.items():
        print(f"\n   {provider.upper()}:")
        for model in models[:3]:  # Show first 3 with details
            print(f"\n     {model['name']}:")
            print(f"       Description: {model['description']}")
            if 'context_window' in model:
                print(f"       Context: {model['context_window']:,} tokens")
            if 'input_price_per_1m' in model:
                print(f"       Input: ${model['input_price_per_1m']}/1M tokens")
            if 'output_price_per_1m' in model:
                print(f"       Output: ${model['output_price_per_1m']}/1M tokens")


def compare_pricing():
    """Compare pricing across models."""
    print("\n" + "=" * 60)
    print("Model Pricing Comparison")
    print("=" * 60)
    
    # Get OpenAI models
    openai_models = OpenAIProvider.get_available_models()
    
    # Filter models with pricing
    priced_models = [
        m for m in openai_models 
        if 'input_price_per_1m' in m and 'output_price_per_1m' in m
    ]
    
    # Sort by input price
    priced_models.sort(key=lambda x: x['input_price_per_1m'])
    
    print("\n1. OpenAI models sorted by input price (cheapest first):")
    print(f"\n   {'Model':<30} {'Input $/1M':<15} {'Output $/1M':<15}")
    print("   " + "-" * 60)
    
    for model in priced_models[:10]:  # Show top 10
        name = model['name']
        input_price = model['input_price_per_1m']
        output_price = model['output_price_per_1m']
        print(f"   {name:<30} ${input_price:<14.2f} ${output_price:<14.2f}")
    
    # Find cheapest and most expensive
    cheapest = priced_models[0]
    most_expensive = priced_models[-1]
    
    print(f"\n2. Price range:")
    print(f"   Cheapest: {cheapest['name']} (${cheapest['input_price_per_1m']}/1M input)")
    print(f"   Most expensive: {most_expensive['name']} (${most_expensive['input_price_per_1m']}/1M input)")
    
    # Calculate cost for sample workload
    print(f"\n3. Cost for 1M input + 100K output tokens:")
    for model in [cheapest, most_expensive]:
        input_cost = model['input_price_per_1m'] * 1.0  # 1M tokens
        output_cost = model['output_price_per_1m'] * 0.1  # 100K tokens
        total = input_cost + output_cost
        print(f"   {model['name']}: ${total:.4f}")


def find_models_by_criteria():
    """Find models matching specific criteria."""
    print("\n" + "=" * 60)
    print("Finding Models by Criteria")
    print("=" * 60)
    
    openai_models = OpenAIProvider.get_available_models()
    
    # Find models under $1/1M input tokens
    print("\n1. Budget-friendly models (< $1.00/1M input):")
    budget_models = [
        m for m in openai_models
        if 'input_price_per_1m' in m and m['input_price_per_1m'] < 1.0
    ]
    for model in budget_models[:5]:
        print(f"   - {model['name']}: ${model['input_price_per_1m']}/1M")
    
    # Find models with large context windows
    print("\n2. Large context models (> 200K tokens):")
    large_context = [
        m for m in openai_models
        if 'context_window' in m and m['context_window'] > 200000
    ]
    for model in large_context:
        print(f"   - {model['name']}: {model['context_window']:,} tokens")
    
    # Find GPT-5 family models
    print("\n3. GPT-5 family models:")
    gpt5_models = [
        m for m in openai_models
        if 'gpt-5' in m['name']
    ]
    for model in gpt5_models:
        print(f"   - {model['name']}: {model['description']}")


def model_recommendations():
    """Provide model recommendations for different use cases."""
    print("\n" + "=" * 60)
    print("Model Recommendations")
    print("=" * 60)
    
    recommendations = {
        "Budget-conscious": {
            "model": "gpt-5-nano",
            "reason": "Lowest cost per token, great for high-volume tasks"
        },
        "Balanced": {
            "model": "gpt-5-mini",
            "reason": "Good balance of cost and performance"
        },
        "High-quality": {
            "model": "gpt-5",
            "reason": "Best quality for complex tasks"
        },
        "Maximum capability": {
            "model": "gpt-5-pro",
            "reason": "Most powerful model for critical tasks"
        },
        "Long context": {
            "model": "gpt-4.1",
            "reason": "1M+ token context window"
        },
    }
    
    print("\n")
    for use_case, rec in recommendations.items():
        print(f"   {use_case}:")
        print(f"     Model: {rec['model']}")
        print(f"     Reason: {rec['reason']}")
        print()


def main():
    """Run all discovery examples."""
    print("\n🚀 AI Content Generator - Model Discovery\n")
    
    discover_models()
    compare_pricing()
    find_models_by_criteria()
    model_recommendations()
    
    print("=" * 60)
    print("Model discovery completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

