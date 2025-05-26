"""Memory management for agents."""

from .base import Memory, MemoryStore
from .types import MemoryEntry, MemoryType

try:
    from .redis_store import RedisMemoryStore
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisMemoryStore = None

from .sqlite_store import SQLiteMemoryStore

__all__ = ["Memory", "MemoryStore", "SQLiteMemoryStore", "MemoryEntry", "MemoryType"]

if REDIS_AVAILABLE:
    __all__.append("RedisMemoryStore")