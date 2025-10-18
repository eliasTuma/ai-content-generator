"""File logger implementation with async support."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles

from .logger_interface import BaseLogger, LogLevel


class FileLogger(BaseLogger):
    """
    Logger that writes to files with rotation support.
    
    Features:
    - Async file operations using aiofiles
    - JSON or text format
    - Daily rotation
    - Automatic directory creation
    - Buffer flushing
    
    Example:
        ```python
        logger = FileLogger(
            filepath="logs/app.log",
            min_level=LogLevel.INFO,
            format="json"
        )
        
        await logger.info("Application started", version="1.0.0")
        await logger.error("Failed to process", error="Timeout")
        
        await logger.close()
        ```
    """
    
    def __init__(
        self,
        filepath: str,
        min_level: LogLevel = LogLevel.INFO,
        format: str = "json",
        rotation: str = "daily",
        max_bytes: Optional[int] = None,
    ):
        """
        Initialize file logger.
        
        Args:
            filepath: Path to log file
            min_level: Minimum log level to record
            format: Log format ("json" or "text")
            rotation: Rotation strategy ("daily", "size", or "none")
            max_bytes: Maximum file size for size-based rotation
        """
        super().__init__(min_level)
        self.filepath = Path(filepath)
        self.format = format.lower()
        self.rotation = rotation
        self.max_bytes = max_bytes
        self._file_handle: Optional[Any] = None
        self._current_date: Optional[str] = None
        
        # Ensure log directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_rotated_filepath(self) -> Path:
        """
        Get the filepath with rotation applied.
        
        Returns:
            Path object for the current log file
        """
        if self.rotation == "daily":
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Add date to filename
            stem = self.filepath.stem
            suffix = self.filepath.suffix
            parent = self.filepath.parent
            
            return parent / f"{stem}_{date_str}{suffix}"
        
        return self.filepath
    
    def _should_rotate(self) -> bool:
        """
        Check if log file should be rotated.
        
        Returns:
            True if rotation is needed
        """
        if self.rotation == "daily":
            current_date = datetime.now().strftime("%Y-%m-%d")
            if self._current_date and self._current_date != current_date:
                return True
            self._current_date = current_date
        
        elif self.rotation == "size" and self.max_bytes:
            filepath = self._get_rotated_filepath()
            if filepath.exists() and filepath.stat().st_size >= self.max_bytes:
                return True
        
        return False
    
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
        timestamp = datetime.now().isoformat()
        
        if self.format == "json":
            log_entry = {
                "timestamp": timestamp,
                "level": level.value,
                "message": message,
            }
            if context:
                log_entry["context"] = context
            
            return json.dumps(log_entry)
        
        else:  # text format
            parts = [f"[{timestamp}]", f"{level.value:8}", message]
            
            if context:
                context_str = " | ".join(f"{k}={v}" for k, v in context.items())
                parts.append(f"({context_str})")
            
            return " ".join(parts)
    
    async def _ensure_file_open(self) -> None:
        """Ensure log file is open for writing."""
        if self._file_handle is None or self._should_rotate():
            # Close existing handle if rotating
            if self._file_handle is not None:
                await self._file_handle.close()
            
            # Open new file
            filepath = self._get_rotated_filepath()
            self._file_handle = await aiofiles.open(filepath, mode="a", encoding="utf-8")
    
    async def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Log a message to file.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context data
        """
        await self._ensure_file_open()
        
        formatted_message = self._format_message(level, message, **context)
        
        if self._file_handle:
            await self._file_handle.write(formatted_message + "\n")
            await self._file_handle.flush()
    
    async def close(self) -> None:
        """
        Close the logger and flush any pending writes.
        """
        if self._file_handle is not None:
            await self._file_handle.flush()
            await self._file_handle.close()
            self._file_handle = None

