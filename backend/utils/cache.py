import sqlite3
import json
import hashlib
import pickle
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager

class SQLiteCache:
    """Thread-safe SQLite cache with optional in-memory layer"""
    
    def __init__(self, db_path: str = "data/research_cache.db", use_memory: bool = True):
        self.db_path = db_path
        self.use_memory = use_memory
        self.memory_cache = {} if use_memory else None
        self.lock = threading.Lock()
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database with proper schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    hit_count INTEGER DEFAULT 0,
                    size_bytes INTEGER
                )
            """)
            
            # Create indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON cache(expires_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON cache(created_at)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper handling"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level='DEFERRED'
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        # Check memory cache first
        if self.use_memory and key in self.memory_cache:
            entry = self.memory_cache[key]
            if datetime.now() < entry['expires_at']:
                return entry['value']
            else:
                del self.memory_cache[key]
        
        # Check SQLite
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT value, expires_at FROM cache 
                    WHERE key = ? AND expires_at > datetime('now')
                """, (key,))
                
                result = cursor.fetchone()
                
                if result:
                    value = pickle.loads(result['value'])
                    
                    # Update hit count
                    cursor.execute("""
                        UPDATE cache SET hit_count = hit_count + 1 
                        WHERE key = ?
                    """, (key,))
                    conn.commit()
                    
                    # Add to memory cache
                    if self.use_memory:
                        self.memory_cache[key] = {
                            'value': value,
                            'expires_at': datetime.fromisoformat(result['expires_at'])
                        }
                    
                    return value
        
        return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        expires_at = datetime.now() + timedelta(seconds=ttl)
        value_bytes = pickle.dumps(value)
        size_bytes = len(value_bytes)
        
        # Add to memory cache
        if self.use_memory:
            self.memory_cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
        
        # Add to SQLite
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO cache 
                    (key, value, created_at, expires_at, size_bytes)
                    VALUES (?, ?, datetime('now'), ?, ?)
                """, (key, value_bytes, expires_at.isoformat(), size_bytes))
                
                conn.commit()
                return True
    
    async def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        # Remove from memory cache
        if self.use_memory and key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove from SQLite
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0
    
    async def clear_expired(self) -> int:
        """Clear expired entries and return count"""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM cache 
                    WHERE expires_at < datetime('now')
                """)
                
                conn.commit()
                deleted_count = cursor.rowcount
        
        # Clear memory cache
        if self.use_memory:
            now = datetime.now()
            expired_keys = [
                k for k, v in self.memory_cache.items() 
                if v['expires_at'] < now
            ]
            for key in expired_keys:
                del self.memory_cache[key]
        
        return deleted_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(size_bytes) as total_size,
                    AVG(hit_count) as avg_hits,
                    MAX(hit_count) as max_hits
                FROM cache
                WHERE expires_at > datetime('now')
            """)
            
            stats = dict(cursor.fetchone())
            
            # Get memory cache stats
            if self.use_memory:
                stats['memory_entries'] = len(self.memory_cache)
            
            return stats