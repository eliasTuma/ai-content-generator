"""Console logger implementation."""

import sys
from datetime import datetime
from typing import Any

from .logger_interface import BaseLogger, LogLevel


class ConsoleLogger(BaseLogger):
    """
    Logger that outputs to console (stdout/stderr).
    
    Features:
    - Colored output for different log levels (optional)
    - Formatted messages with timestamp and level
    - Context data formatting
    - Configurable output stream
    
    Example:
        ```python
        logger = ConsoleLogger(min_level=LogLevel.INFO, colored=True)
        
        await logger.info("Processing started", user_id=123)
        await logger.warning("Rate limit approaching", usage=0.85)
        await logger.error("Request failed", error="Timeout")
        
        await logger.close()
        ```
    """
    
    # ANSI color codes for terminal output
    COLORS = {
        LogLevel.DEBUG: "\033[36m",      # Cyan
        LogLevel.INFO: "\033[32m",       # Green
        LogLevel.WARNING: "\033[33m",    # Yellow
        LogLevel.ERROR: "\033[31m",      # Red
        LogLevel.CRITICAL: "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def __init__(
        self,
        min_level: LogLevel = LogLevel.INFO,
        colored: bool = True,
        use_stderr_for_errors: bool = True,
    ):
        """
        Initialize console logger.
        
        Args:
            min_level: Minimum log level to record
            colored: Whether to use colored output
            use_stderr_for_errors: Whether to use stderr for ERROR and CRITICAL levels
        """
        super().__init__(min_level)
        self.colored = colored
        self.use_stderr_for_errors = use_stderr_for_errors
    
    def _format_message(
        self,
        level: LogLevel,
        message: str,
        **context: Any
    ) -> str:
        """
        Format a log message.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context data
        
        Returns:
            Formatted message string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format level with color if enabled
        if self.colored:
            color = self.COLORS.get(level, "")
            level_str = f"{color}{level.value:8}{self.RESET}"
        else:
            level_str = f"{level.value:8}"
        
        # Build base message
        parts = [f"[{timestamp}]", level_str, message]
        
        # Add context if provided
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            parts.append(f"({context_str})")
        
        return " ".join(parts)
    
    async def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Log a message to console.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context data
        """
        formatted_message = self._format_message(level, message, **context)
        
        # Choose output stream
        if self.use_stderr_for_errors and level in (LogLevel.ERROR, LogLevel.CRITICAL):
            output = sys.stderr
        else:
            output = sys.stdout
        
        # Write message
        print(formatted_message, file=output)
        
        # Flush to ensure immediate output
        output.flush()
    
    async def close(self) -> None:
        """
        Close the logger.
        
        For console logger, this just flushes the output streams.
        """
        sys.stdout.flush()
        sys.stderr.flush()

