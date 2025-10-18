"""Logger interface and base classes."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


class LogLevel(Enum):
    """Log level enumeration."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    def __str__(self) -> str:
        """String representation of log level."""
        return self.value
    
    @property
    def priority(self) -> int:
        """Get numeric priority for comparison."""
        priorities = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        return priorities[self]


class BaseLogger(ABC):
    """
    Abstract base class for loggers.
    
    All logger implementations must inherit from this class and implement
    the logging methods.
    
    Example:
        ```python
        class MyLogger(BaseLogger):
            def __init__(self, min_level: LogLevel = LogLevel.INFO):
                super().__init__(min_level)
            
            async def _log(self, level: LogLevel, message: str, **context: Any) -> None:
                # Implementation here
                print(f"[{level}] {message}")
        ```
    """
    
    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        """
        Initialize base logger.
        
        Args:
            min_level: Minimum log level to record
        """
        self.min_level = min_level
    
    def should_log(self, level: LogLevel) -> bool:
        """
        Check if a message at the given level should be logged.
        
        Args:
            level: Log level to check
        
        Returns:
            True if message should be logged
        """
        return level.priority >= self.min_level.priority
    
    @abstractmethod
    async def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Internal log method to be implemented by subclasses.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context data
        """
        pass
    
    async def debug(self, message: str, **context: Any) -> None:
        """
        Log a debug message.
        
        Args:
            message: Log message
            **context: Additional context data
        """
        if self.should_log(LogLevel.DEBUG):
            await self._log(LogLevel.DEBUG, message, **context)
    
    async def info(self, message: str, **context: Any) -> None:
        """
        Log an info message.
        
        Args:
            message: Log message
            **context: Additional context data
        """
        if self.should_log(LogLevel.INFO):
            await self._log(LogLevel.INFO, message, **context)
    
    async def warning(self, message: str, **context: Any) -> None:
        """
        Log a warning message.
        
        Args:
            message: Log message
            **context: Additional context data
        """
        if self.should_log(LogLevel.WARNING):
            await self._log(LogLevel.WARNING, message, **context)
    
    async def error(self, message: str, **context: Any) -> None:
        """
        Log an error message.
        
        Args:
            message: Log message
            **context: Additional context data
        """
        if self.should_log(LogLevel.ERROR):
            await self._log(LogLevel.ERROR, message, **context)
    
    async def critical(self, message: str, **context: Any) -> None:
        """
        Log a critical message.
        
        Args:
            message: Log message
            **context: Additional context data
        """
        if self.should_log(LogLevel.CRITICAL):
            await self._log(LogLevel.CRITICAL, message, **context)
    
    @abstractmethod
    async def close(self) -> None:
        """
        Cleanup resources (close files, flush buffers, etc.).
        
        This method should be called when the logger is no longer needed.
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

