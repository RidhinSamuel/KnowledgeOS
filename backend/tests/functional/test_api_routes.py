# backend/tests/functional/test_api_routes.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.database import get_db

def test_auth_register_existing_user_conflict(app_client):
    """Functional test: Registering an existing email returns HTTP 400."""
    from app.main import app

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value={"email": "existing@example.com"})

    async def override_get_db():
        return mock_db

    app.dependency_overrides[get_db] = override_get_db

    response = app_client.post("/api/v1/auth/register", json={
        "email": "existing@example.com",
        "password": "Password123!",
        "full_name": "Existing User",
        "role": "Viewer"
    })

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
