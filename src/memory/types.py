"""Memory types and data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryEntry(BaseModel):
    """Memory entry model."""

    id: str = Field(..., description="Unique identifier")
    type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    agent_id: str = Field(..., description="Agent that created this memory")
    thread_id: Optional[str] = Field(None, description="Thread/conversation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    relevance_score: float = Field(default=1.0, description="Relevance score")
    access_count: int = Field(default=0, description="Number of times accessed")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")

    class Config:
        """Model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class MemorySearchQuery(BaseModel):
    """Memory search query."""

    query: str = Field(..., description="Search query")
    memory_types: Optional[List[MemoryType]] = Field(None, description="Filter by memory types")
    agent_ids: Optional[List[str]] = Field(None, description="Filter by agent IDs")
    thread_id: Optional[str] = Field(None, description="Filter by thread ID")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    limit: int = Field(default=10, description="Maximum results")
    min_relevance: float = Field(default=0.0, description="Minimum relevance score")