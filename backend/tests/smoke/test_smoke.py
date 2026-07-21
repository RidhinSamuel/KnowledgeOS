# backend/tests/smoke/test_smoke.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.database import db_manager

def test_smoke_healthz_healthy(app_client):
    """Smoke test: Verify system healthz returns 200 and healthy status when dependencies respond."""
    mock_mongo = MagicMock()
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1.0})
    mock_mongo.__getitem__.return_value = mock_db

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with patch.object(db_manager, "mongo_client", mock_mongo), \
         patch.object(db_manager, "db", mock_db), \
         patch.object(db_manager, "redis_client", mock_redis):

        response = app_client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_smoke_openapi_schema(app_client):
    """Smoke test: Verify OpenAPI JSON schema is generated and accessible."""
    response = app_client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
