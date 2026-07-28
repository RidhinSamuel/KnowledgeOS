# backend/tests/unit/test_rag_pipeline_unit.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.cache_service import _generate_cache_key, get_cached_query_response, set_cached_query_response
from app.services.agent_graph import decide_to_rewrite, grade_relevance_node


def test_cache_key_generation():
    key1 = _generate_cache_key("ws-123", "What is GDPR?")
    key2 = _generate_cache_key("ws-123", "what is gdpr?  ")
    assert key1 == key2
    assert key1.startswith("cache:query:ws-123:")


@pytest.mark.asyncio
async def test_redis_cache_get_hit():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = '{"content": "Cached answer", "sources": []}'

    res = await get_cached_query_response("ws-123", "What is GDPR?", mock_redis)
    assert res is not None
    assert res["content"] == "Cached answer"
    assert res["cached"] is True


@pytest.mark.asyncio
async def test_redis_cache_get_miss():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    res = await get_cached_query_response("ws-123", "Unknown question?", mock_redis)
    assert res is None


@pytest.mark.asyncio
async def test_redis_cache_set():
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    success = await set_cached_query_response(
        workspace_id="ws-123",
        prompt="What is GDPR?",
        content="Test answer",
        sources=[],
        redis_client=mock_redis
    )
    assert success is True
    mock_redis.set.assert_called_once()


def test_decide_to_rewrite_router():
    # Low score & retries < 2 -> should rewrite
    state_low = {"relevance_score": 0.2, "retry_count": 0}
    assert decide_to_rewrite(state_low) == "rewrite_query"

    # High score -> generate answer directly
    state_high = {"relevance_score": 0.8, "retry_count": 0}
    assert decide_to_rewrite(state_high) == "generate_answer"

    # Low score but max retries reached (2) -> proceed to generate answer
    state_max_retries = {"relevance_score": 0.2, "retry_count": 2}
    assert decide_to_rewrite(state_max_retries) == "generate_answer"
