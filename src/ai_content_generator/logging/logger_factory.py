"""Logger factory for creating logger instances."""

from typing import Any, Optional

from .logger_interface import BaseLogger, LogLevel
from .console_logger import ConsoleLogger
from .file_logger import FileLogger


class LoggerFactory:
    """
    Factory for creating logger instances.
    
    Supports creating different types of loggers with configuration.
    
    Example:
        ```python
        # Create console logger
        console_logger = LoggerFactory.create_logger(
            "console",
            min_level=LogLevel.INFO,
            colored=True
        )
        
        # Create file logger
        file_logger = LoggerFactory.create_logger(
            "file",
            filepath="logs/app.log",
            format="json"
        )
        
        # Create composite logger (logs to both)
        composite = LoggerFactory.create_composite_logger([
            console_logger,
            file_logger
        ])
        ```
    """
    
    @staticmethod
    def create_logger(logger_type: str, **kwargs: Any) -> BaseLogger:
        """
        Create a logger instance.
        
        Args:
            logger_type: Type of logger ("console", "file")
            **kwargs: Logger-specific configuration
        
        Returns:
            Logger instance
        
        Raises:
            ValueError: If logger type is not supported
        
        Example:
            ```python
            logger = LoggerFactory.create_logger(
                "console",
                min_level=LogLevel.DEBUG,
                colored=True
            )
            ```
        """
        logger_type = logger_type.lower()
        
        if logger_type == "console":
            return ConsoleLogger(**kwargs)
        
        elif logger_type == "file":
            if "filepath" not in kwargs:
                raise ValueError("filepath is required for file logger")
            return FileLogger(**kwargs)
        
        else:
            raise ValueError(
                f"Unsupported logger type: {logger_type}. "
                f"Supported types: console, file"
            )
    
    @staticmethod
    def create_console_logger(
        min_level: LogLevel = LogLevel.INFO,
        colored: bool = True,
        use_stderr_for_errors: bool = True,
    ) -> ConsoleLogger:
        """
        Create a console logger with common defaults.
        
        Args:
            min_level: Minimum log level
            colored: Whether to use colored output
            use_stderr_for_errors: Whether to use stderr for errors
        
        Returns:
            ConsoleLogger instance
        """
        return ConsoleLogger(
            min_level=min_level,
            colored=colored,
            use_stderr_for_errors=use_stderr_for_errors,
        )
    
    @staticmethod
    def create_file_logger(
        filepath: str,
        min_level: LogLevel = LogLevel.INFO,
        format: str = "json",
        rotation: str = "daily",
        max_bytes: Optional[int] = None,
    ) -> FileLogger:
        """
        Create a file logger with common defaults.
        
        Args:
            filepath: Path to log file
            min_level: Minimum log level
            format: Log format ("json" or "text")
            rotation: Rotation strategy ("daily", "size", or "none")
            max_bytes: Maximum file size for size-based rotation
        
        Returns:
            FileLogger instance
        """
        return FileLogger(
            filepath=filepath,
            min_level=min_level,
            format=format,
            rotation=rotation,
            max_bytes=max_bytes,
        )
    
    @staticmethod
    def create_composite_logger(loggers: list[BaseLogger]) -> "CompositeLogger":
        """
        Create a composite logger that logs to multiple loggers.
        
        Args:
            loggers: List of logger instances
        
        Returns:
            CompositeLogger instance
        """
        from .composite_logger import CompositeLogger
        return CompositeLogger(loggers)


def get_logger(
    name: str = "console",
    **kwargs: Any
) -> BaseLogger:
    """
    Convenience function to get a logger instance.
    
    Args:
        name: Logger type name
        **kwargs: Logger configuration
    
    Returns:
        Logger instance
    
    Example:
        ```python
        logger = get_logger("console", min_level=LogLevel.DEBUG)
        await logger.info("Application started")
        ```
    """
    return LoggerFactory.create_logger(name, **kwargs)

