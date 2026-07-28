# backend/tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def mock_db_lifecycle():
    """Mock DB startup & connection lifecycle globally for unit/smoke tests."""
    with patch("app.core.database.DatabaseManager.connect", new_callable=AsyncMock), \
         patch("app.core.database.DatabaseManager._ensure_qdrant_collection", new_callable=AsyncMock):
        from app.core.database import db_manager
        db_manager.qdrant_client = AsyncMock()
        db_manager.redis_client = AsyncMock()
        db_manager.db = MagicMock()
        yield

@pytest.fixture
def app_client():
    """Provides a TestClient connected to the FastAPI app with mocked connections."""
    from app.main import app
    return TestClient(app)
