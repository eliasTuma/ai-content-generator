"""
Session usage example for AI Content Generator.

This example demonstrates:
- Using SessionFactory to create sessions
- Budget tracking and alerts
- Context manager usage
- Session export
"""

import asyncio
import os
from ai_content_generator import Config, SessionFactory


async def session_example():
    """Example using LLMSession with budget tracking."""
    print("=" * 60)
    print("Session with Budget Tracking Example")
    print("=" * 60)

    # Check for API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not set. Please set it to run this example.")
        return

    # Create configuration
    config = Config.from_dict({
        "providers": {
            "openai": {
                "api_key": openai_key,
                "timeout": 60,
                "max_retries": 3,
                "default_model": "gpt-4o-mini"
            }
        },
        "session": {
            "default_provider": "openai",
            "default_model": "gpt-4o-mini",
            "default_budget_usd": 0.10,  # $0.10 budget
            "dry_run": False,
            "alerts": [0.5, 0.8, 0.9]  # Alert at 50%, 80%, 90%
        }
    })

    # Create session factory
    factory = SessionFactory(config)

    print("\n1. Available providers:")
    providers = factory.list_available_providers()
    print(f"   {', '.join(providers)}")

    # Create session with budget
    print("\n2. Creating session with $0.10 budget...")
    async with factory.create_session(
        provider="openai",
        model="gpt-4o-mini",
        budget_usd=0.10,
        metadata={"purpose": "example", "user": "demo"}
    ) as session:

        print(f"   Session created: {session.session_id}")
        print(f"   Budget: ${session.budget_usd:.2f}")
        print(f"   Model: {session.model}")

        # Make first request
        print("\n3. Making first request...")
        response1 = await session.chat(
            "Write a one-sentence description of Python.",
            max_tokens=50
        )
        print(f"   Response: {response1['content']}")
        print(f"   Cost: ${session.cost_usd:.6f}")
        print(f"   Budget remaining: ${session.budget_remaining:.6f}")

        # Make second request
        print("\n4. Making second request...")
        response2 = await session.chat(
            "What is async programming in one sentence?",
            max_tokens=50
        )
        print(f"   Response: {response2['content']}")
        print(f"   Cost: ${session.cost_usd:.6f}")
        print(f"   Budget remaining: ${session.budget_remaining:.6f}")

        # Show session statistics
        print("\n5. Session statistics:")
        print(f"   Total requests: {session.request_count}")
        print(f"   Total tokens: {session.tokens_used}")
        print(f"   Total cost: ${session.cost_usd:.6f}")
        print(f"   Budget used: {(session.cost_usd / session.budget_usd * 100):.1f}%")

        # Export session data
        print("\n6. Exporting session data...")
        session_data = session.export_to_dict()
        print(f"   Session ID: {session_data['session_id']}")
        print(f"   Duration: {session_data['duration_seconds']:.2f}s")
        print(f"   Requests: {len(session_data['requests'])}")

    print("\n✅ Session example completed!")


async def batch_example():
    """Example using batch generation."""
    print("\n" + "=" * 60)
    print("Batch Generation Example")
    print("=" * 60)

    # Check for API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not set. Skipping batch example.")
        return

    # Create simple config
    config = Config.from_dict({
        "providers": {
            "openai": {
                "api_key": openai_key,
                "default_model": "gpt-4o-mini"
            }
        },
        "session": {
            "default_provider": "openai",
            "default_budget_usd": 0.50
        }
    })

    factory = SessionFactory(config)

    # Create session
    async with factory.create_session(budget_usd=0.50) as session:

        # Define batch items
        topics = [
            "Python",
            "JavaScript",
            "Rust"
        ]

        print(f"\n1. Generating descriptions for {len(topics)} topics...")
        print(f"   Budget: ${session.budget_usd:.2f}")

        # Generate descriptions in batch
        async def generate_description(topic: str) -> dict:
            """Generate description for a topic."""
            response = await session.chat(
                f"Write a one-sentence description of {topic} programming language.",
                max_tokens=50
            )
            return {
                "topic": topic,
                "description": response["content"]
            }

        # Use batch_generate
        results = await session.batch_generate(
            items=topics,
            process_func=generate_description,
            check_budget_per_item=True
        )

        # Display results
        print("\n2. Results:")
        for result in results:
            print(f"\n   {result['topic']}:")
            print(f"   {result['description']}")

        # Show final statistics
        print("\n3. Batch statistics:")
        print(f"   Items processed: {len(results)}")
        print(f"   Total cost: ${session.cost_usd:.6f}")
        print(f"   Average cost per item: ${session.cost_usd / len(results):.6f}")
        print(f"   Budget remaining: ${session.budget_remaining:.6f}")

    print("\n✅ Batch example completed!")


async def main():
    """Run all examples."""
    print("\n🚀 AI Content Generator - Session Usage Examples\n")

    # Run session example
    await session_example()

    # Run batch example
    await batch_example()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

