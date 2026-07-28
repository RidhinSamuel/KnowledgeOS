# backend/tests/functional/test_rag_stream_route.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from app.core.database import get_db, get_qdrant, get_redis
from app.core.security import get_current_user_token


def test_stream_chat_response_redis_cache_hit(app_client):
    """Functional Test: Stream chat response returns instant cached response on Redis cache hit."""
    from app.main import app

    session_id = str(ObjectId())
    workspace_id = str(ObjectId())
    user_id = "user-123"

    mock_db = MagicMock()
    mock_db.chat_sessions.find_one = AsyncMock(return_value={
        "_id": ObjectId(session_id),
        "workspace_id": workspace_id,
        "user_id": user_id
    })
    mock_db.messages.insert_one = AsyncMock(return_value=MagicMock())

    mock_redis = AsyncMock()
    mock_redis.get.return_value = '{"content": "Fast cached response", "sources": [{"filename": "doc.pdf", "page": 1}]}'

    async def override_db(): return mock_db
    async def override_redis(): return mock_redis
    async def override_token(): return {"sub": user_id, "role": "Viewer"}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_current_user_token] = override_token

    response = app_client.post(
        f"/api/v1/chat/session/{session_id}/stream",
        json={"prompt": "What is GDPR compliance?"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "data: " in response.text
    assert "Fast cached response" in response.text
