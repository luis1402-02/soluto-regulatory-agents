"""Base memory interface and implementation."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from ..utils import get_logger
from .types import MemoryEntry, MemorySearchQuery, MemoryType

logger = get_logger(__name__)


class MemoryStore(ABC):
    """Abstract base class for memory storage."""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        pass

    @abstractmethod
    async def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass

    @abstractmethod
    async def search(self, query: MemorySearchQuery) -> List[MemoryEntry]:
        """Search memory entries."""
        pass

    @abstractmethod
    async def update(self, memory_id: str, entry: MemoryEntry) -> bool:
        """Update a memory entry."""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired memories."""
        pass


class Memory:
    """Memory management system for agents."""

    def __init__(self, store: MemoryStore, default_ttl: int = 3600):
        """Initialize memory system."""
        self.store = store
        self.default_ttl = default_ttl

    async def remember(
        self,
        content: str,
        agent_id: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        thread_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        ttl: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Store a new memory."""
        memory_id = str(uuid4())
        ttl = ttl or self.default_ttl

        entry = MemoryEntry(
            id=memory_id,
            type=memory_type,
            content=content,
            agent_id=agent_id,
            thread_id=thread_id,
            tags=tags or [],
            metadata=metadata or {},
            expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None,
        )

        await self.store.store(entry)
        logger.info(
            "memory_stored",
            memory_id=memory_id,
            agent_id=agent_id,
            type=memory_type.value,
        )

        return memory_id

    async def recall(self, memory_id: str) -> Optional[MemoryEntry]:
        """Recall a specific memory."""
        entry = await self.store.retrieve(memory_id)
        
        if entry:
            # Update access metadata
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            await self.store.update(memory_id, entry)
            
            logger.debug(
                "memory_recalled",
                memory_id=memory_id,
                access_count=entry.access_count,
            )

        return entry

    async def search_memories(
        self,
        query: str,
        agent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Search through memories."""
        search_query = MemorySearchQuery(
            query=query,
            agent_ids=[agent_id] if agent_id else None,
            thread_id=thread_id,
            memory_types=memory_types,
            limit=limit,
        )

        results = await self.store.search(search_query)
        
        logger.debug(
            "memory_search",
            query=query,
            results_count=len(results),
        )

        return results

    async def forget(self, memory_id: str) -> bool:
        """Delete a memory."""
        success = await self.store.delete(memory_id)
        
        if success:
            logger.info("memory_deleted", memory_id=memory_id)
        
        return success

    async def consolidate_memories(
        self,
        agent_id: str,
        thread_id: Optional[str] = None,
    ) -> Optional[str]:
        """Consolidate short-term memories into long-term."""
        # Search for recent short-term memories
        search_query = MemorySearchQuery(
            query="",
            agent_ids=[agent_id],
            thread_id=thread_id,
            memory_types=[MemoryType.SHORT_TERM],
            start_date=datetime.utcnow() - timedelta(hours=1),
            limit=100,
        )

        memories = await self.store.search(search_query)
        
        if not memories:
            return None

        # Consolidate memories into a summary
        consolidated_content = "\n\n".join([
            f"[{m.timestamp.isoformat()}] {m.content}"
            for m in sorted(memories, key=lambda x: x.timestamp)
        ])

        # Store as long-term memory
        memory_id = await self.remember(
            content=f"Consolidated memories:\n{consolidated_content}",
            agent_id=agent_id,
            memory_type=MemoryType.LONG_TERM,
            thread_id=thread_id,
            tags=["consolidated"],
            ttl=0,  # No expiration
        )

        # Mark original memories for deletion
        for memory in memories:
            memory.metadata["consolidated"] = True
            memory.metadata["consolidated_into"] = memory_id
            await self.store.update(memory.id, memory)

        logger.info(
            "memories_consolidated",
            agent_id=agent_id,
            count=len(memories),
            consolidated_id=memory_id,
        )

        return memory_id