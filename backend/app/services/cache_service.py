# backend/app/services/cache_service.py
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
import redis.asyncio as aioredis

logger = logging.getLogger("cache_service")

DEFAULT_CACHE_TTL = 86400  # 24 hours


def _generate_cache_key(workspace_id: str, prompt: str) -> str:
    """Generate SHA256 key scoped to workspace_id and normalized prompt."""
    normalized_prompt = prompt.strip().lower()
    raw_key = f"{workspace_id}:{normalized_prompt}"
    hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"cache:query:{workspace_id}:{hashed}"


async def get_cached_query_response(
    workspace_id: str,
    prompt: str,
    redis_client: Optional[aioredis.Redis]
) -> Optional[Dict[str, Any]]:
    """
    Checks Redis cache for identical query in workspace.
    Returns cached response payload if hit (0ms latency, 0 token cost).
    """
    if not redis_client:
        return None

    try:
        cache_key = _generate_cache_key(workspace_id, prompt)
        cached_data = await redis_client.get(cache_key)

        if cached_data:
            logger.info("redis_cache_hit", workspace_id=workspace_id, key=cache_key)
            payload = json.loads(cached_data)
            payload["cached"] = True
            return payload

    except Exception as e:
        logger.warning("redis_cache_get_failed", error=str(e))

    return None


async def set_cached_query_response(
    workspace_id: str,
    prompt: str,
    content: str,
    sources: List[Dict[str, Any]],
    redis_client: Optional[aioredis.Redis],
    ttl_seconds: int = DEFAULT_CACHE_TTL
) -> bool:
    """Stores generated response in Redis cache with TTL."""
    if not redis_client or not content:
        return False

    try:
        cache_key = _generate_cache_key(workspace_id, prompt)
        payload = {
            "content": content,
            "sources": sources
        }
        await redis_client.set(cache_key, json.dumps(payload), ex=ttl_seconds)
        logger.info("redis_cache_set", workspace_id=workspace_id, key=cache_key, ttl=ttl_seconds)
        return True
    except Exception as e:
        logger.warning("redis_cache_set_failed", error=str(e))
        return False
