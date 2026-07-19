# backend/test_backend.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# 1. Mock DB connections to prevent live networking during import
with patch("app.core.database.DatabaseManager.connect", new_callable=AsyncMock):
    with patch("app.core.database.DatabaseManager._ensure_qdrant_collection", new_callable=AsyncMock):
        from app.main import app
        from app.core.database import db_manager

client = TestClient(app)

def test_healthz_healthy():
    """Verifies health check router returns online when database pings succeed."""
    mock_mongo = MagicMock()
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1.0})
    mock_mongo.__getitem__.return_value = mock_db
    
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with patch.object(db_manager, "mongo_client", mock_mongo), \
         patch.object(db_manager, "db", mock_db), \
         patch.object(db_manager, "redis_client", mock_redis):
        
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_healthz_unhealthy():
    """Verifies health check router returns offline when database pings fail."""
    mock_mongo = MagicMock()
    mock_db = MagicMock()
    mock_db.command = AsyncMock(side_effect=Exception("Connection timed out"))
    mock_mongo.__getitem__.return_value = mock_db
    
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis connection error"))

    with patch.object(db_manager, "mongo_client", mock_mongo), \
         patch.object(db_manager, "db", mock_db), \
         patch.object(db_manager, "redis_client", mock_redis):
        
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"
        assert response.json()["services"]["mongodb"] == "offline"
        assert response.json()["services"]["redis"] == "offline"

def test_auth_register_existing_user():
    """Verifies registration route returns 400 when email is already registered."""
    from app.core.database import get_db

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value={"email": "test@example.com"})

    # Override the get_db FastAPI dependency with our mock
    async def override_get_db():
        return mock_db

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "strongpassword123",
        "full_name": "Test User",
        "role": "Viewer"
    })

    # Reset dependency overrides after the test
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
