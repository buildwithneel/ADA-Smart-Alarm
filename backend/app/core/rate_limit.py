from __future__ import annotations

import logging
import time
from typing import Optional
from fastapi import Request

from app.core.config import settings
from app.core.errors import RateLimitExceededException
from app.core.redis import get_redis_client

logger = logging.getLogger("ada.rate_limit")

# In-memory fallback if Redis is unavailable
_memory_counts: dict[str, list[float]] = {}


def check_rate_limit(
    key_prefix: str,
    identifier: str,
    max_requests: int = 60,
    window_seconds: int = 60,
) -> None:
    """
    Sliding window rate limiter using Redis sorted sets.
    Falls back gracefully to in-memory sliding window if Redis is offline.
    Raises RateLimitExceededException (HTTP 429) if threshold is exceeded.
    """
    now = time.time()
    rate_key = f"ratelimit:{key_prefix}:{identifier}"

    try:
        redis_client = get_redis_client()
        pipe = redis_client.pipeline()

        # Remove elements older than window
        pipe.zremrangebyscore(rate_key, 0, now - window_seconds)
        # Add current timestamp
        pipe.zadd(rate_key, {str(now): now})
        # Count items in the window
        pipe.zcard(rate_key)
        # Set expire
        pipe.expire(rate_key, window_seconds + 5)

        _, _, count, _ = pipe.execute()

        if count > max_requests:
            logger.warning(
                f"Rate limit exceeded for key '{rate_key}' ({count}/{max_requests} in {window_seconds}s)"
            )
            raise RateLimitExceededException(
                message=f"Rate limit exceeded. Maximum {max_requests} requests per minute.",
                details={"retry_after_seconds": window_seconds},
            )
    except RateLimitExceededException:
        raise
    except Exception as e:
        logger.debug(f"Redis rate limit fallback to memory due to: {e}")
        # In-memory sliding window fallback
        timestamps = _memory_counts.get(rate_key, [])
        valid_ts = [t for t in timestamps if t > now - window_seconds]
        valid_ts.append(now)
        _memory_counts[rate_key] = valid_ts

        if len(valid_ts) > max_requests:
            raise RateLimitExceededException(
                message=f"Rate limit exceeded. Maximum {max_requests} requests per minute.",
                details={"retry_after_seconds": window_seconds},
            )


def rate_limit_dependency(
    prefix: str = "location",
    max_requests: Optional[int] = None,
    window_seconds: int = 60,
):
    """FastAPI dependency to rate limit endpoints by authenticated user or client IP."""
    limit = max_requests or settings.RATE_LIMIT_PER_MINUTE

    async def dependency(request: Request) -> None:
        # Prefer authenticated user identity or token hash to avoid NAT collisions
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            import hashlib
            token = auth_header[7:].strip()
            identifier = f"usr_{hashlib.sha256(token.encode()).hexdigest()[:16]}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            identifier = f"ip_{client_ip}"

        check_rate_limit(
            key_prefix=prefix,
            identifier=identifier,
            max_requests=limit,
            window_seconds=window_seconds,
        )

    return dependency
