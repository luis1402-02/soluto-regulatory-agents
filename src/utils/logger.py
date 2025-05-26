"""Logging configuration and utilities."""

import logging
import sys
from typing import Any, Dict

import structlog
from rich.console import Console
from rich.logging import RichHandler

from ..config import get_settings

console = Console()


def setup_logging() -> None:
    """Setup logging configuration."""
    settings = get_settings()

    # Configure standard logging
    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_level=True,
            )
        ],
    )

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)


class AgentLogger:
    """Specialized logger for agent activities."""

    def __init__(self, agent_name: str):
        """Initialize agent logger."""
        self.logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name

    def log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log agent action."""
        self.logger.info(
            "agent_action",
            agent=self.agent_name,
            action=action,
            **details,
        )

    def log_thought(self, thought: str) -> None:
        """Log agent thought process."""
        self.logger.debug(
            "agent_thought",
            agent=self.agent_name,
            thought=thought,
        )

    def log_tool_use(self, tool: str, input_data: Any, output: Any) -> None:
        """Log tool usage."""
        self.logger.info(
            "tool_use",
            agent=self.agent_name,
            tool=tool,
            input=input_data,
            output=output,
        )

    def log_error(self, error: str, exception: Exception | None = None) -> None:
        """Log agent error."""
        self.logger.error(
            "agent_error",
            agent=self.agent_name,
            error=error,
            exc_info=exception,
        )