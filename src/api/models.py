"""API request and response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """Request model for task submission."""

    task: str = Field(..., description="Task description for the agents")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    max_iterations: int = Field(default=10, description="Maximum iterations for agents")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    api_key: str = Field(..., description="API key for authentication")


class Message(BaseModel):
    """Message in the conversation."""

    role: str = Field(..., description="Message role (human/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskResponse(BaseModel):
    """Response model for task results."""

    success: bool = Field(..., description="Whether the task was successful")
    task_id: str = Field(..., description="Unique task ID")
    output: Optional[str] = Field(None, description="Final output from agents")
    error: Optional[str] = Field(None, description="Error message if failed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    messages: List[Message] = Field(default_factory=list, description="Conversation messages")
    iterations: int = Field(..., description="Number of iterations executed")
    memory_entries: List[str] = Field(default_factory=list, description="Created memory IDs")
    documents: Optional[Dict[str, Any]] = Field(None, description="Generated documents")
    execution_time: float = Field(..., description="Total execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(..., description="Status of dependent services")


class MemoryQuery(BaseModel):
    """Query for agent memories."""

    agent_name: str = Field(..., description="Agent name to query")
    thread_id: Optional[str] = Field(None, description="Filter by thread ID")
    limit: int = Field(default=10, description="Maximum results")
    api_key: str = Field(..., description="API key for authentication")


class MemoryResponse(BaseModel):
    """Response with agent memories."""

    agent_name: str = Field(..., description="Agent name")
    memories: List[Dict[str, Any]] = Field(..., description="Memory entries")
    count: int = Field(..., description="Total memories returned")