"""SQLite-based memory store implementation for fallback."""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from ..utils import get_logger
from .base import MemoryStore
from .types import MemoryEntry, MemorySearchQuery

logger = get_logger(__name__)


class SQLiteMemoryStore(MemoryStore):
    """SQLite-based memory storage implementation."""

    def __init__(self, db_path: str = "memory.db"):
        """Initialize SQLite memory store."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize SQLite database."""
        if not self._initialized:
            # Create tables
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    agent_id TEXT NOT NULL,
                    thread_id TEXT,
                    timestamp REAL NOT NULL,
                    relevance_score REAL DEFAULT 1.0,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    expires_at REAL,
                    tags TEXT,
                    embedding TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON memories(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON memories(thread_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
            
            conn.commit()
            conn.close()
            
            self._initialized = True
            logger.info("SQLite memory store initialized")

    async def close(self) -> None:
        """Close database connection."""
        # SQLite connections are closed automatically
        pass

    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry in SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO memories (
                    id, type, content, metadata, agent_id, thread_id,
                    timestamp, relevance_score, access_count, last_accessed,
                    expires_at, tags, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.type.value,
                entry.content,
                json.dumps(entry.metadata),
                entry.agent_id,
                entry.thread_id,
                entry.timestamp.timestamp(),
                entry.relevance_score,
                entry.access_count,
                entry.last_accessed.timestamp() if entry.last_accessed else None,
                entry.expires_at.timestamp() if entry.expires_at else None,
                json.dumps(entry.tags),
                json.dumps(entry.embedding) if entry.embedding else None,
            ))
            
            conn.commit()
            return entry.id
            
        finally:
            conn.close()

    async def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM memories WHERE id = ?
            """, (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return self._row_to_entry(row)
            
        finally:
            conn.close()

    async def search(self, query: MemorySearchQuery) -> List[MemoryEntry]:
        """Search memory entries in SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build query
            sql = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if query.agent_ids:
                placeholders = ",".join("?" * len(query.agent_ids))
                sql += f" AND agent_id IN ({placeholders})"
                params.extend(query.agent_ids)
            
            if query.memory_types:
                placeholders = ",".join("?" * len(query.memory_types))
                sql += f" AND type IN ({placeholders})"
                params.extend([t.value for t in query.memory_types])
            
            if query.thread_id:
                sql += " AND thread_id = ?"
                params.append(query.thread_id)
            
            if query.query:
                sql += " AND content LIKE ?"
                params.append(f"%{query.query}%")
            
            if query.start_date:
                sql += " AND timestamp >= ?"
                params.append(query.start_date.timestamp())
            
            if query.end_date:
                sql += " AND timestamp <= ?"
                params.append(query.end_date.timestamp())
            
            sql += " ORDER BY relevance_score DESC, timestamp DESC"
            sql += f" LIMIT {query.limit}"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_entry(row) for row in rows]
            
        finally:
            conn.close()

    async def update(self, memory_id: str, entry: MemoryEntry) -> bool:
        """Update a memory entry in SQLite."""
        # Same as store since we use INSERT OR REPLACE
        await self.store(entry)
        return True

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry from SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            conn.close()

    async def cleanup_expired(self) -> int:
        """Clean up expired memories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = datetime.utcnow().timestamp()
            cursor.execute("""
                DELETE FROM memories 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            
            conn.commit()
            count = cursor.rowcount
            
            if count > 0:
                logger.info("cleaned_up_memories", count=count)
            
            return count
            
        finally:
            conn.close()

    def _row_to_entry(self, row) -> MemoryEntry:
        """Convert database row to MemoryEntry."""
        from .types import MemoryType
        
        (id, type_str, content, metadata_str, agent_id, thread_id,
         timestamp, relevance_score, access_count, last_accessed,
         expires_at, tags_str, embedding_str) = row
        
        return MemoryEntry(
            id=id,
            type=MemoryType(type_str),
            content=content,
            metadata=json.loads(metadata_str) if metadata_str else {},
            agent_id=agent_id,
            thread_id=thread_id,
            timestamp=datetime.fromtimestamp(timestamp),
            relevance_score=relevance_score,
            access_count=access_count,
            last_accessed=datetime.fromtimestamp(last_accessed) if last_accessed else None,
            expires_at=datetime.fromtimestamp(expires_at) if expires_at else None,
            tags=json.loads(tags_str) if tags_str else [],
            embedding=json.loads(embedding_str) if embedding_str else None,
        )