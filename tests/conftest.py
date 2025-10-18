"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_prompt() -> str:
    """Sample prompt for testing."""
    return "Write a short introduction to Python programming."


@pytest.fixture
def sample_messages() -> list[dict[str, str]]:
    """Sample messages for testing chat completion."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]


@pytest.fixture
def mock_openai_response() -> dict[str, any]:
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4-turbo-preview",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def mock_anthropic_response() -> dict[str, any]:
    """Mock Anthropic API response."""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "This is a test response."}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }


@pytest.fixture
def temp_log_file(tmp_path):
    """Temporary log file for testing."""
    return str(tmp_path / "test.log")


@pytest.fixture
def sample_config() -> dict:
    """Sample configuration for testing."""
    return {
        "providers": {
            "openai": {
                "api_key": "sk-test-key",
                "timeout": 30,
                "max_retries": 3,
            },
            "anthropic": {
                "api_key": "sk-ant-test-key",
                "timeout": 30,
                "max_retries": 3,
            },
        },
        "session": {
            "default_budget_usd": 1.0,
            "default_model": "gpt-5-nano",
        },
        "logging": {
            "level": "INFO",
            "file": "logs/test.log",
        },
    }
