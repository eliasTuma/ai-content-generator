"""Composite logger for logging to multiple destinations."""

from typing import Any

from .logger_interface import BaseLogger, LogLevel


class CompositeLogger(BaseLogger):
    """
    Logger that forwards log messages to multiple loggers.
    
    This allows logging to multiple destinations simultaneously (e.g., console and file).
    Individual logger failures are handled gracefully.
    
    Example:
        ```python
        from ai_content_generator.logging import (
            ConsoleLogger,
            FileLogger,
            CompositeLogger,
            LogLevel
        )
        
        console = ConsoleLogger(min_level=LogLevel.INFO)
        file = FileLogger(filepath="logs/app.log", min_level=LogLevel.DEBUG)
        
        # Create composite logger
        logger = CompositeLogger([console, file])
        
        # Logs to both console and file
        await logger.info("Application started")
        await logger.debug("Debug info")  # Only to file (console min is INFO)
        
        await logger.close()
        ```
    """
    
    def __init__(self, loggers: list[BaseLogger]):
        """
        Initialize composite logger.
        
        Args:
            loggers: List of logger instances to forward to
        """
        # Use the minimum level among all loggers
        min_level = min((logger.min_level for logger in loggers), key=lambda x: x.priority)
        super().__init__(min_level)
        self.loggers = loggers
    
    def add_logger(self, logger: BaseLogger) -> None:
        """
        Add a logger to the composite.
        
        Args:
            logger: Logger instance to add
        """
        self.loggers.append(logger)
        
        # Update min_level if new logger has lower threshold
        if logger.min_level.priority < self.min_level.priority:
            self.min_level = logger.min_level
    
    def remove_logger(self, logger: BaseLogger) -> None:
        """
        Remove a logger from the composite.
        
        Args:
            logger: Logger instance to remove
        """
        if logger in self.loggers:
            self.loggers.remove(logger)
    
    async def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Forward log message to all loggers.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context data
        """
        errors = []
        
        for logger in self.loggers:
            try:
                # Each logger checks its own min_level
                if logger.should_log(level):
                    await logger._log(level, message, **context)
            except Exception as e:
                # Collect errors but don't stop logging to other loggers
                errors.append(f"{type(logger).__name__}: {str(e)}")
        
        # If all loggers failed, we might want to know
        if errors and len(errors) == len(self.loggers):
            # All loggers failed - print to stderr as last resort
            import sys
            print(f"CompositeLogger: All loggers failed: {', '.join(errors)}", file=sys.stderr)
    
    async def close(self) -> None:
        """
        Close all loggers.
        
        Attempts to close all loggers even if some fail.
        """
        errors = []
        
        for logger in self.loggers:
            try:
                await logger.close()
            except Exception as e:
                errors.append(f"{type(logger).__name__}: {str(e)}")
        
        if errors:
            import sys
            print(f"CompositeLogger: Some loggers failed to close: {', '.join(errors)}", file=sys.stderr)

