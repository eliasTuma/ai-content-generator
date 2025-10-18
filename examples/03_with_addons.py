"""
Advanced example using addons.

This example demonstrates:
- Using cache addon to avoid duplicate requests
- Using retry addon for handling failures
- Using dry run addon for testing
- Combining multiple addons
"""

import asyncio
import os
from ai_content_generator.providers import OpenAIProvider
from ai_content_generator.addons import (
    CacheAddon,
    RetryAddon,
    DryRunAddon,
    AddonManager,
    AddonContext,
)
from ai_content_generator.utils import generate_request_id


async def cache_example():
    """Example using cache addon."""
    print("=" * 60)
    print("Cache Addon Example")
    print("=" * 60)
    
    # Create cache addon
    cache = CacheAddon(max_size=10, ttl_seconds=3600)
    
    # Create addon manager
    manager = AddonManager()
    manager.add_addon(cache)
    
    # Simulate requests
    prompt = "What is Python?"
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    # First request - cache miss
    print("\n1. First request (cache miss):")
    cached_response = await manager.execute_pre_request(prompt, context)
    print(f"   Cached response: {cached_response}")
    print(f"   Cache hit: {context.custom.get('cache_hit', False)}")
    
    # Simulate storing response
    mock_response = {"content": "Python is a programming language..."}
    await manager.execute_post_request(mock_response, context)
    
    # Second request - cache hit
    print("\n2. Second request (cache hit):")
    context2 = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    cached_response = await manager.execute_pre_request(prompt, context2)
    print(f"   Cached response: {cached_response[:50]}...")
    print(f"   Cache hit: {context2.custom.get('cache_hit', False)}")
    
    # Show cache stats
    print("\n3. Cache statistics:")
    stats = cache.get_stats()
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.2%}")
    print(f"   Cache size: {stats['cache_size']}/{stats['max_size']}")
    
    print("\n✅ Cache example completed!")


async def retry_example():
    """Example using retry addon."""
    print("\n" + "=" * 60)
    print("Retry Addon Example")
    print("=" * 60)
    
    # Create retry addon
    retry = RetryAddon(
        max_retries=3,
        initial_delay=0.1,
        exponential_base=2.0
    )
    
    # Create addon manager
    manager = AddonManager()
    manager.add_addon(retry)
    
    # Simulate error
    from ai_content_generator.core.exceptions import RateLimitError
    
    context = AddonContext(
        request_id=generate_request_id(),
        prompt="Test prompt",
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n1. Simulating rate limit error:")
    error = RateLimitError(
        message="Rate limit exceeded",
        provider="openai"
    )
    
    # First retry
    should_retry = await manager.execute_on_error(error, context)
    print(f"   Should retry: {should_retry}")
    print(f"   Retry count: {context.custom.get('retry_count', 0)}")
    print(f"   Retry delay: {context.custom.get('retry_delay', 0):.2f}s")
    
    # Second retry
    should_retry = await manager.execute_on_error(error, context)
    print(f"\n   Should retry: {should_retry}")
    print(f"   Retry count: {context.custom.get('retry_count', 0)}")
    
    # Show retry stats
    print("\n2. Retry statistics:")
    stats = retry.get_stats()
    print(f"   Total retries: {stats['total_retries']}")
    print(f"   Max retries: {stats['max_retries']}")
    
    print("\n✅ Retry example completed!")


async def dry_run_example():
    """Example using dry run addon."""
    print("\n" + "=" * 60)
    print("Dry Run Addon Example")
    print("=" * 60)
    
    # Create dry run addon
    dry_run = DryRunAddon(
        mock_response="This is a mock response for testing.",
        estimate_tokens=True,
        log_requests=True
    )
    
    # Create addon manager
    manager = AddonManager()
    manager.add_addon(dry_run)
    
    # Simulate request
    prompt = "Write a blog post about AI."
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n1. Intercepting request (dry run):")
    mock_response = await manager.execute_pre_request(prompt, context)
    print(f"   Mock response: {mock_response}")
    print(f"   Dry run: {context.custom.get('dry_run', False)}")
    print(f"   Estimated input tokens: {context.custom.get('estimated_input_tokens', 0)}")
    print(f"   Estimated output tokens: {context.custom.get('estimated_output_tokens', 0)}")
    
    # Show request log
    print("\n2. Request log:")
    logs = dry_run.get_request_log()
    for i, log in enumerate(logs, 1):
        print(f"   Request {i}:")
        print(f"     - ID: {log['request_id']}")
        print(f"     - Model: {log['model']}")
        print(f"     - Prompt: {log['prompt'][:50]}...")
    
    # Show stats
    print("\n3. Dry run statistics:")
    stats = dry_run.get_stats()
    print(f"   Total intercepted: {stats['total_intercepted']}")
    
    print("\n✅ Dry run example completed!")


async def combined_example():
    """Example combining multiple addons."""
    print("\n" + "=" * 60)
    print("Combined Addons Example")
    print("=" * 60)
    
    # Create addons
    cache = CacheAddon(max_size=10, ttl_seconds=3600)
    retry = RetryAddon(max_retries=3)
    
    # Create addon manager and add addons in order
    manager = AddonManager()
    manager.add_addon(cache)  # Check cache first
    manager.add_addon(retry)  # Then handle retries
    
    print("\n1. Registered addons:")
    for addon in manager.get_addons():
        print(f"   - {addon.get_name()}: {addon.get_description()}")
    
    # Simulate workflow
    prompt = "Explain machine learning."
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n2. Processing request through addon pipeline:")
    
    # Pre-request (check cache)
    cached = await manager.execute_pre_request(prompt, context)
    if cached:
        print(f"   ✓ Cache hit! Using cached response.")
    else:
        print(f"   ✗ Cache miss. Would make API call.")
        
        # Simulate successful response
        response = {"content": "Machine learning is..."}
        await manager.execute_post_request(response, context)
        print(f"   ✓ Response cached for future use.")
    
    print("\n✅ Combined example completed!")


async def main():
    """Run all addon examples."""
    print("\n🚀 AI Content Generator - Addon Examples\n")
    
    await cache_example()
    await retry_example()
    await dry_run_example()
    await combined_example()
    
    print("\n" + "=" * 60)
    print("All addon examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

