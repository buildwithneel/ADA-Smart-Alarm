import logging

import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import settings

logger = logging.getLogger("ada.redis")

# Connection pool for high concurrency
pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
    socket_connect_timeout=0.2,
    socket_timeout=0.5,
)


def get_redis_client() -> redis.Redis:
    """
    Provides a Redis client instance backed by the shared connection pool.
    Ready for:
    - ETA caching
    - rate limiting
    - background jobs coordination
    - temporary state
    - distributed locks
    """
    return redis.Redis(connection_pool=pool)


def check_redis_health() -> bool:
    """
    Checks if Redis server is reachable and responding to PING.
    """
    try:
        client = get_redis_client()
        return bool(client.ping())
    except (RedisConnectionError, Exception) as e:
        logger.warning(f"Redis health check failed: {e}")
        return False
