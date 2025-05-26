"""Redis-based memory store implementation."""

import json
from datetime import datetime
from typing import List, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None

from ..config import get_settings
from ..utils import get_logger
from .base import MemoryStore
from .types import MemoryEntry, MemorySearchQuery

logger = get_logger(__name__)


class RedisMemoryStore(MemoryStore):
    """Redis-based memory storage implementation."""

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize Redis memory store."""
        self.redis = redis_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")
            
        if not self._initialized:
            if not self.redis:
                settings = get_settings()
                self.redis = await redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
            self._initialized = True
            logger.info("Redis memory store initialized")

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._initialized = False

    def _get_key(self, memory_id: str) -> str:
        """Get Redis key for memory entry."""
        return f"memory:{memory_id}"

    def _get_index_key(self, index_type: str, value: str) -> str:
        """Get Redis key for index."""
        return f"memory_index:{index_type}:{value}"

    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry in Redis."""
        await self.initialize()

        key = self._get_key(entry.id)
        data = entry.model_dump_json()

        # Store main entry
        await self.redis.set(key, data)

        # Set expiration if specified
        if entry.expires_at:
            ttl = int((entry.expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self.redis.expire(key, ttl)

        # Create indexes
        await self._create_indexes(entry)

        return entry.id

    async def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from Redis."""
        await self.initialize()

        key = self._get_key(memory_id)
        data = await self.redis.get(key)

        if not data:
            return None

        return MemoryEntry.model_validate_json(data)

    async def search(self, query: MemorySearchQuery) -> List[MemoryEntry]:
        """Search memory entries in Redis."""
        await self.initialize()

        # Get candidate memory IDs from indexes
        candidate_ids = await self._get_candidate_ids(query)

        if not candidate_ids:
            return []

        # Retrieve and filter memories
        memories = []
        for memory_id in candidate_ids:
            entry = await self.retrieve(memory_id)
            if entry and self._matches_query(entry, query):
                memories.append(entry)

        # Sort by relevance and timestamp
        memories.sort(
            key=lambda m: (m.relevance_score, m.timestamp),
            reverse=True,
        )

        # Apply limit
        return memories[: query.limit]

    async def update(self, memory_id: str, entry: MemoryEntry) -> bool:
        """Update a memory entry in Redis."""
        await self.initialize()

        # Check if exists
        if not await self.redis.exists(self._get_key(memory_id)):
            return False

        # Remove old indexes
        old_entry = await self.retrieve(memory_id)
        if old_entry:
            await self._remove_indexes(old_entry)

        # Store updated entry
        await self.store(entry)
        return True

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry from Redis."""
        await self.initialize()

        # Retrieve entry for index cleanup
        entry = await self.retrieve(memory_id)
        if not entry:
            return False

        # Remove indexes
        await self._remove_indexes(entry)

        # Delete main entry
        key = self._get_key(memory_id)
        result = await self.redis.delete(key)

        return result > 0

    async def cleanup_expired(self) -> int:
        """Clean up expired memories."""
        await self.initialize()

        # Redis automatically removes expired keys
        # This method is for manual cleanup if needed
        count = 0
        
        # Scan for memory keys
        async for key in self.redis.scan_iter(match="memory:*"):
            # Check if key has no TTL (meaning it should have expired)
            ttl = await self.redis.ttl(key)
            if ttl == -2:  # Key doesn't exist
                count += 1

        logger.info("cleaned_up_memories", count=count)
        return count

    async def _create_indexes(self, entry: MemoryEntry) -> None:
        """Create indexes for memory entry."""
        # Index by agent
        agent_key = self._get_index_key("agent", entry.agent_id)
        await self.redis.sadd(agent_key, entry.id)

        # Index by type
        type_key = self._get_index_key("type", entry.type.value)
        await self.redis.sadd(type_key, entry.id)

        # Index by thread
        if entry.thread_id:
            thread_key = self._get_index_key("thread", entry.thread_id)
            await self.redis.sadd(thread_key, entry.id)

        # Index by tags
        for tag in entry.tags:
            tag_key = self._get_index_key("tag", tag)
            await self.redis.sadd(tag_key, entry.id)

    async def _remove_indexes(self, entry: MemoryEntry) -> None:
        """Remove indexes for memory entry."""
        # Remove from agent index
        agent_key = self._get_index_key("agent", entry.agent_id)
        await self.redis.srem(agent_key, entry.id)

        # Remove from type index
        type_key = self._get_index_key("type", entry.type.value)
        await self.redis.srem(type_key, entry.id)

        # Remove from thread index
        if entry.thread_id:
            thread_key = self._get_index_key("thread", entry.thread_id)
            await self.redis.srem(thread_key, entry.id)

        # Remove from tag indexes
        for tag in entry.tags:
            tag_key = self._get_index_key("tag", tag)
            await self.redis.srem(tag_key, entry.id)

    async def _get_candidate_ids(self, query: MemorySearchQuery) -> List[str]:
        """Get candidate memory IDs from indexes."""
        sets_to_intersect = []

        # Filter by agent IDs
        if query.agent_ids:
            agent_sets = [
                self._get_index_key("agent", agent_id)
                for agent_id in query.agent_ids
            ]
            sets_to_intersect.extend(agent_sets)

        # Filter by memory types
        if query.memory_types:
            type_sets = [
                self._get_index_key("type", memory_type.value)
                for memory_type in query.memory_types
            ]
            sets_to_intersect.extend(type_sets)

        # Filter by thread
        if query.thread_id:
            thread_key = self._get_index_key("thread", query.thread_id)
            sets_to_intersect.append(thread_key)

        # Filter by tags
        if query.tags:
            tag_sets = [
                self._get_index_key("tag", tag)
                for tag in query.tags
            ]
            sets_to_intersect.extend(tag_sets)

        # Get intersection of all sets
        if sets_to_intersect:
            if len(sets_to_intersect) == 1:
                candidates = await self.redis.smembers(sets_to_intersect[0])
            else:
                candidates = await self.redis.sinter(*sets_to_intersect)
            return list(candidates)

        # If no filters, scan all memory keys
        candidates = []
        async for key in self.redis.scan_iter(match="memory:*"):
            memory_id = key.split(":", 1)[1]
            candidates.append(memory_id)

        return candidates

    def _matches_query(self, entry: MemoryEntry, query: MemorySearchQuery) -> bool:
        """Check if memory entry matches search query."""
        # Check text content
        if query.query and query.query.lower() not in entry.content.lower():
            return False

        # Check date range
        if query.start_date and entry.timestamp < query.start_date:
            return False
        if query.end_date and entry.timestamp > query.end_date:
            return False

        # Check relevance
        if entry.relevance_score < query.min_relevance:
            return False

        return True