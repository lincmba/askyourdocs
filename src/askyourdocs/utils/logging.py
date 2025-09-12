"""
Logging configuration and utilities for AskYourDocs.

Provides structured logging with file rotation, different log levels,
and Rich console integration.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Global logger registry
_loggers: dict[str, logging.Logger] = {}
_configured = False

console = Console()


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Setup application-wide logging configuration."""
    global _configured

    if _configured:
        return

    # Determine log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with Rich
    console_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=verbose,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(log_level)

    # Console formatter
    console_format = "%(message)s"
    if verbose:
        console_format = "%(name)s: %(message)s"

    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        try:
            log_path = Path(log_file).expanduser()
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)

            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to setup file logging: {e}[/yellow]"
            )

    # Suppress noisy third-party loggers
    noisy_loggers = [
        "chromadb",
        "httpx",
        "urllib3",
        "transformers",
        "sentence_transformers",
        "huggingface_hub",
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger

    return _loggers[name]


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """Log performance metrics."""
    logger = get_logger("performance")

    extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"{operation} completed in {duration:.2f}s {extra_info}".strip())


def log_error_with_context(
    logger: logging.Logger, error: Exception, context: dict
) -> None:
    """Log error with additional context information."""
    context_str = " ".join([f"{k}={v}" for k, v in context.items()])
    logger.error(f"{error} | Context: {context_str}", exc_info=True)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)

    def log_info(self, message: str, **kwargs) -> None:
        """Log info message with optional context."""
        if kwargs:
            context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {context}"
        self.logger.info(message)

    def log_error(
        self, message: str, error: Optional[Exception] = None, **kwargs
    ) -> None:
        """Log error message with optional context."""
        if kwargs:
            context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {context}"

        if error:
            self.logger.error(message, exc_info=error)
        else:
            self.logger.error(message)

    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional context."""
        if kwargs:
            context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {context}"
        self.logger.warning(message)

    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional context."""
        if kwargs:
            context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {context}"
        self.logger.debug(message)
