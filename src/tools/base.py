"""Base tool interface and types."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool = Field(..., description="Whether the tool execution was successful")
    output: Any = Field(..., description="Tool output data")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")


class BaseTool(ABC):
    """Base class for all agent tools."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        pass

    def validate_input(self, **kwargs: Any) -> bool:
        """Validate input parameters."""
        # Override in subclasses for custom validation
        return True