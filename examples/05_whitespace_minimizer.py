"""
Example using whitespace minimizer addon.

This example demonstrates:
- Minimizing whitespace in prompts to reduce token usage
- Preserving code blocks while minimizing
- Tracking token savings statistics
- Using different configuration modes
"""

import asyncio
from ai_content_generator.addons import (
    WhitespaceMinimizerAddon,
    AddonManager,
    AddonContext,
)
from ai_content_generator.utils import generate_request_id


async def basic_minimization_example():
    """Example showing basic whitespace minimization."""
    print("=" * 60)
    print("Basic Whitespace Minimization Example")
    print("=" * 60)
    
    # Create minimizer addon
    minimizer = WhitespaceMinimizerAddon(
        minimize_spaces=True,
        minimize_tabs=True,
        minimize_newlines=True,
        preserve_code_blocks=True
    )
    
    # Create addon manager
    manager = AddonManager()
    manager.add_addon(minimizer)
    
    # Prompt with excessive whitespace
    prompt = """
    This    is    a    prompt    with    multiple    spaces.
    
    It    also    has    many    newlines.
    
    
    
    And    tabs:	here	and	there.
    
    The goal is to reduce token usage.
    """
    
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n1. Original prompt (first 100 chars):")
    print(f"   {prompt[:100]}...")
    print(f"   Length: {len(prompt)} characters")
    
    # Minimize the prompt
    minimized = await manager.execute_pre_request(prompt, context)
    
    if minimized:
        print("\n2. Minimized prompt (first 100 chars):")
        print(f"   {minimized[:100]}...")
        print(f"   Length: {len(minimized)} characters")
        print(f"   Characters saved: {context.custom.get('whitespace_minimizer_chars_saved', 0)}")
        print(f"   Estimated tokens saved: {context.custom.get('whitespace_minimizer_tokens_saved', 0)}")
    else:
        print("\n2. No minimization needed (prompt was already optimal)")
    
    print("\n✅ Basic minimization example completed!")


async def code_block_preservation_example():
    """Example showing code block preservation."""
    print("\n" + "=" * 60)
    print("Code Block Preservation Example")
    print("=" * 60)
    
    minimizer = WhitespaceMinimizerAddon(
        minimize_spaces=True,
        minimize_newlines=True,
        preserve_code_blocks=True
    )
    
    manager = AddonManager()
    manager.add_addon(minimizer)
    
    # Prompt with code block
    prompt = """
    Here is a Python function:
    
    ```python
    def    example():
        if    True:
            return    "Hello"
    ```
    
    Notice how spaces inside code are preserved.
    """
    
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n1. Original prompt:")
    print(prompt)
    
    minimized = await manager.execute_pre_request(prompt, context)
    
    if minimized:
        print("\n2. Minimized prompt:")
        print(minimized)
        print("\n3. Code block preserved:")
        if "```python" in minimized:
            print("   ✓ Code block markers preserved")
        if "    return" in minimized or "    if" in minimized:
            print("   ✓ Indentation inside code block preserved")
    
    print("\n✅ Code block preservation example completed!")


async def aggressive_mode_example():
    """Example showing aggressive minimization mode."""
    print("\n" + "=" * 60)
    print("Aggressive Mode Example")
    print("=" * 60)
    
    # Standard mode
    standard = WhitespaceMinimizerAddon(
        minimize_spaces=True,
        minimize_newlines=True,
        aggressive_mode=False,
        max_newlines=2
    )
    
    # Aggressive mode
    aggressive = WhitespaceMinimizerAddon(
        minimize_spaces=True,
        minimize_newlines=True,
        aggressive_mode=True
    )
    
    prompt = """
    
    
    Line    1    with    many    spaces
    
    
    
    Line    2    with    tabs:	here	and	there
    
    
    
    Line    3
    """
    
    print("\n1. Original prompt:")
    print(repr(prompt))
    
    # Test standard mode
    context1 = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    standard_result = await standard.pre_request(prompt, context1)
    
    print("\n2. Standard mode result:")
    print(repr(standard_result))
    print(f"   Length: {len(standard_result) if standard_result else len(prompt)}")
    
    # Test aggressive mode
    context2 = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    aggressive_result = await aggressive.pre_request(prompt, context2)
    
    print("\n3. Aggressive mode result:")
    print(repr(aggressive_result))
    print(f"   Length: {len(aggressive_result) if aggressive_result else len(prompt)}")
    print(f"   Characters saved: {len(prompt) - len(aggressive_result) if aggressive_result else 0}")
    
    print("\n✅ Aggressive mode example completed!")


async def statistics_example():
    """Example showing statistics tracking."""
    print("\n" + "=" * 60)
    print("Statistics Tracking Example")
    print("=" * 60)
    
    minimizer = WhitespaceMinimizerAddon()
    manager = AddonManager()
    manager.add_addon(minimizer)
    
    # Process multiple prompts with varying whitespace
    prompts = [
        "Normal prompt without extra whitespace",
        "Prompt    with    many    spaces",
        "Prompt\n\n\nwith\n\n\nmany\n\n\nnewlines",
        "Prompt\twith\ttabs\tand    spaces",
        "Another    prompt    with    spaces"
    ]
    
    print("\n1. Processing multiple prompts...")
    
    for i, prompt in enumerate(prompts, 1):
        context = AddonContext(
            request_id=generate_request_id(),
            prompt=prompt,
            model="gpt-5-nano",
            provider="openai"
        )
        
        minimized = await manager.execute_pre_request(prompt, context)
        
        if minimized:
            chars_saved = context.custom.get('whitespace_minimizer_chars_saved', 0)
            tokens_saved = context.custom.get('whitespace_minimizer_tokens_saved', 0)
            print(f"   Prompt {i}: Saved {chars_saved} chars, ~{tokens_saved} tokens")
    
    # Show cumulative statistics
    print("\n2. Overall statistics:")
    stats = minimizer.get_stats()
    print(f"   Total requests processed: {stats['total_requests']}")
    print(f"   Total characters removed: {stats['total_chars_removed']}")
    print(f"   Total tokens saved (estimated): {stats['total_tokens_saved']}")
    print(f"   Average chars per request: {stats['average_chars_per_request']:.2f}")
    print(f"   Average tokens per request: {stats['average_tokens_per_request']:.2f}")
    
    print("\n✅ Statistics example completed!")


async def combined_addons_example():
    """Example combining whitespace minimizer with other addons."""
    print("\n" + "=" * 60)
    print("Combined Addons Example")
    print("=" * 60)
    
    from ai_content_generator.addons import CacheAddon, DryRunAddon
    
    # Create multiple addons
    minimizer = WhitespaceMinimizerAddon()
    cache = CacheAddon(max_size=10, ttl_seconds=3600)
    dry_run = DryRunAddon(mock_response="Mock response", estimate_tokens=True)
    
    # Create addon manager - order matters!
    manager = AddonManager()
    manager.add_addon(minimizer)  # First - minimize before caching
    manager.add_addon(cache)      # Second - cache minimized prompts
    manager.add_addon(dry_run)    # Third - intercept if enabled
    
    print("\n1. Registered addons:")
    for addon in manager.get_addons():
        print(f"   - {addon.get_name()}: {addon.get_description()}")
    
    prompt = "This    prompt    has    many    spaces"
    
    context = AddonContext(
        request_id=generate_request_id(),
        prompt=prompt,
        model="gpt-5-nano",
        provider="openai"
    )
    
    print("\n2. Processing request through addon pipeline:")
    print(f"   Original prompt: {prompt}")
    
    # Pre-request hooks (minimization happens here)
    result = await manager.execute_pre_request(prompt, context)
    
    if result:
        print(f"   Minimized prompt: {result}")
        print(f"   Characters saved: {context.custom.get('whitespace_minimizer_chars_saved', 0)}")
    
    print("\n✅ Combined addons example completed!")


async def main():
    """Run all whitespace minimizer examples."""
    print("\n🚀 AI Content Generator - Whitespace Minimizer Examples\n")
    
    await basic_minimization_example()
    await code_block_preservation_example()
    await aggressive_mode_example()
    await statistics_example()
    await combined_addons_example()
    
    print("\n" + "=" * 60)
    print("All whitespace minimizer examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

