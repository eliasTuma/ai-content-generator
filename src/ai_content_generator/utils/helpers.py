"""Helper utility functions."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles


async def load_file(filepath: str) -> str:
    """
    Load file contents asynchronously.
    
    Args:
        filepath: Path to file
    
    Returns:
        File contents as string
    
    Raises:
        FileNotFoundError: If file doesn't exist
    
    Example:
        ```python
        content = await load_file("data.txt")
        ```
    """
    async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
        return await f.read()


async def save_file(filepath: str, content: str) -> None:
    """
    Save content to file asynchronously.
    
    Creates parent directories if they don't exist.
    
    Args:
        filepath: Path to file
        content: Content to write
    
    Example:
        ```python
        await save_file("output.txt", "Hello, World!")
        ```
    """
    # Ensure parent directory exists
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(filepath, mode="w", encoding="utf-8") as f:
        await f.write(content)


def generate_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        Unique request ID string
    
    Example:
        ```python
        request_id = generate_request_id()
        # "req-550e8400-e29b-41d4-a716-446655440000"
        ```
    """
    return f"req-{uuid.uuid4()}"


def format_datetime(dt: Optional[datetime] = None, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime object (None for current time)
        format: Format string
    
    Returns:
        Formatted datetime string
    
    Example:
        ```python
        timestamp = format_datetime()
        # "2025-01-18 14:30:45"
        ```
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format)


def safe_json_loads(text: str) -> Optional[dict]:
    """
    Safely parse JSON string.
    
    Args:
        text: JSON string
    
    Returns:
        Parsed dictionary or None if invalid
    
    Example:
        ```python
        data = safe_json_loads('{"key": "value"}')
        if data:
            print(data["key"])
        ```
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated
    
    Returns:
        Truncated text
    
    Example:
        ```python
        short = truncate_text("This is a very long text", max_length=10)
        # "This is a..."
        ```
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_cost(cost_usd: float, decimals: int = 4) -> str:
    """
    Format cost for display.
    
    Args:
        cost_usd: Cost in USD
        decimals: Number of decimal places
    
    Returns:
        Formatted cost string
    
    Example:
        ```python
        formatted = format_cost(0.001234)
        # "$0.0012"
        ```
    """
    return f"${cost_usd:.{decimals}f}"


def format_tokens(tokens: int) -> str:
    """
    Format token count for display.
    
    Args:
        tokens: Token count
    
    Returns:
        Formatted token string
    
    Example:
        ```python
        formatted = format_tokens(1500)
        # "1,500 tokens"
        
        formatted = format_tokens(1500000)
        # "1.50M tokens"
        ```
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M tokens"
    elif tokens >= 1_000:
        return f"{tokens:,} tokens"
    else:
        return f"{tokens} tokens"


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage safely.
    
    Args:
        part: Part value
        total: Total value
    
    Returns:
        Percentage (0.0 if total is 0)
    
    Example:
        ```python
        pct = calculate_percentage(25, 100)
        # 25.0
        ```
    """
    if total == 0:
        return 0.0
    return (part / total) * 100


def merge_dicts(*dicts: dict) -> dict:
    """
    Merge multiple dictionaries.
    
    Later dictionaries override earlier ones.
    
    Args:
        *dicts: Dictionaries to merge
    
    Returns:
        Merged dictionary
    
    Example:
        ```python
        merged = merge_dicts(
            {"a": 1, "b": 2},
            {"b": 3, "c": 4}
        )
        # {"a": 1, "b": 3, "c": 4}
        ```
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    
    Example:
        ```python
        logs_dir = ensure_directory("logs")
        ```
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size_mb(filepath: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        filepath: Path to file
    
    Returns:
        File size in MB
    
    Example:
        ```python
        size = get_file_size_mb("large_file.json")
        # 2.5
        ```
    """
    return Path(filepath).stat().st_size / (1024 * 1024)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    
    Example:
        ```python
        safe = sanitize_filename("my/file:name*.txt")
        # "my_file_name_.txt"
        ```
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename

