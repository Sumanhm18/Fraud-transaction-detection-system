"""
Redis configuration and connection management
"""

import json
from typing import Any, Optional

import redis.asyncio as redis
import structlog

from .config import get_settings

logger = structlog.get_logger()

# Global Redis connection
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    settings = get_settings()
    
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.error("Redis initialization failed", error=str(e))
        raise


async def close_redis():
    """Close Redis connection"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client


class RedisCache:
    """Redis caching utility"""
    
    def __init__(self, prefix: str = "finsentinel"):
        self.prefix = prefix
    
    def _key(self, key: str) -> str:
        """Generate prefixed key"""
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = get_redis()
            value = await client.get(self._key(key))
            return json.loads(value) if value else None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        try:
            client = get_redis()
            serialized = json.dumps(value, default=str)
            return await client.set(
                self._key(key), 
                serialized, 
                ex=expire
            )
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = get_redis()
            return await client.delete(self._key(key)) > 0
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            client = get_redis()
            return await client.exists(self._key(key)) > 0
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False


# Global cache instance
cache = RedisCache()