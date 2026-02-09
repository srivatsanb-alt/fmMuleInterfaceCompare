import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json
from app.main import app

# Test Data
MOCK_SHERPA = {
    "name": "test_sherpa",
    "fleet_name": "test_fleet",
    "hwid": "test_hwid",
    "api_key": "test_api_key",
    "sherpa_type": "test_type"
}

MOCK_FLEET = {
    "name": "test_fleet",
    "site": "test_site",
    "location": "test_location",
    "customer": "test_customer"
}

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock redis.Redis to return expected values."""
    with patch("redis.Redis") as mock_redis_class:
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None
        mock_redis_instance.set.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        yield mock_redis_instance

@pytest.fixture(autouse=True)
def mock_aioredis():
    """Mock aioredis.Redis for async operations."""
    with patch("aioredis.Redis") as mock_redis_class:
        mock_redis_instance = AsyncMock()
        mock_redis_instance.set = AsyncMock(return_value=True)
        mock_redis_class.from_url.return_value = mock_redis_instance
        yield mock_redis_instance

@pytest.fixture(autouse=True)
def mock_db_session():
    """Mock database session."""
    with patch("models.db_session.DBSession") as mock_session:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        
        # Mock sherpa methods
        mock_instance.get_sherpa.return_value = MagicMock(
            name=MOCK_SHERPA["name"],
            fleet=MagicMock(name=MOCK_SHERPA["fleet_name"]),
            hashed_api_key="hashed_key"
        )
        mock_instance.get_sherpa_status_with_none.return_value = MagicMock(
            trip_id=None,
            inducted=False,
            sherpa_name=MOCK_SHERPA["name"]
        )
        mock_instance.get_all_sherpas.return_value = [
            MagicMock(
                name=MOCK_SHERPA["name"],
                fleet=MagicMock(name=MOCK_SHERPA["fleet_name"])
            )
        ]
        mock_instance.get_all_sherpa_names.return_value = [MOCK_SHERPA["name"]]
        
        # Mock fleet methods
        mock_instance.get_fleet.return_value = MagicMock(
            name=MOCK_FLEET["name"],
            id=1
        )
        mock_instance.get_all_fleets.return_value = [
            MagicMock(
                name=MOCK_FLEET["name"],
                site=MOCK_FLEET["site"],
                location=MOCK_FLEET["location"],
                customer=MOCK_FLEET["customer"]
            )
        ]
        mock_instance.get_all_fleet_names.return_value = [MOCK_FLEET["name"]]
        
        mock_session.return_value = mock_instance
        yield mock_instance

@pytest.fixture(autouse=True)
def mock_mongo():
    """Mock MongoDB client."""
    with patch("models.mongo_client.FMMongo") as mock_mongo_class:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_mongo_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture(autouse=True)
def client():
    """Create test client."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def auth_token():
    """Generate auth token for tests."""
    from app.routers.dependencies import generate_jwt_token
    return generate_jwt_token("admin", "support")

def test_get_all_sherpa_info(client, auth_token):
    """Test getting all sherpa information."""
    response = client.get(
        "/api/v1/configure_fleet/all_sherpa_info",
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert MOCK_SHERPA["name"] in data
    assert data[MOCK_SHERPA["name"]]["fleet_name"] == MOCK_SHERPA["fleet_name"]

def test_get_all_fleet_info(client, auth_token):
    """Test getting all fleet information."""
    response = client.get(
        "/api/v1/configure_fleet/all_fleet_info",
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert MOCK_FLEET["name"] in data
    assert data[MOCK_FLEET["name"]]["site"] == MOCK_FLEET["site"]

def test_add_edit_sherpa(client, auth_token):
    """Test adding/editing a sherpa."""
    sherpa_data = {
        "hwid": MOCK_SHERPA["hwid"],
        "api_key": MOCK_SHERPA["api_key"],
        "fleet_name": MOCK_SHERPA["fleet_name"],
        "sherpa_type": MOCK_SHERPA["sherpa_type"]
    }
    
    response = client.post(
        f"/api/v1/configure_fleet/add_edit_sherpa/{MOCK_SHERPA['name']}",
        json=sherpa_data,
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200

def test_delete_sherpa(client, auth_token):
    """Test deleting a sherpa."""
    response = client.get(
        f"/api/v1/configure_fleet/delete_sherpa/{MOCK_SHERPA['name']}",
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200

def test_add_edit_fleet(client, auth_token):
    """Test adding/editing a fleet."""
    fleet_data = {
        "site": MOCK_FLEET["site"],
        "location": MOCK_FLEET["location"],
        "customer": MOCK_FLEET["customer"],
        "map_name": "test_map"
    }
    
    response = client.post(
        f"/api/v1/configure_fleet/add_edit_fleet/{MOCK_FLEET['name']}",
        data=fleet_data,
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200

def test_delete_fleet(client, auth_token):
    """Test deleting a fleet."""
    response = client.get(
        f"/api/v1/configure_fleet/delete_fleet/{MOCK_FLEET['name']}",
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200

def test_get_all_available_maps(client, auth_token):
    """Test getting all available maps for a fleet."""
    response = client.get(
        f"/api/v1/configure_fleet/get_all_available_maps/{MOCK_FLEET['name']}",
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "use current map" in data

def test_update_map(client, auth_token):
    """Test updating a fleet's map."""
    update_data = {
        "fleet_name": MOCK_FLEET["name"],
        "map_path": "use current map"
    }
    
    response = client.post(
        "/api/v1/configure_fleet/update_map",
        json=update_data,
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200

def test_switch_sherpa(client, auth_token):
    """Test switching a sherpa to a different fleet."""
    switch_data = {
        "hwid": MOCK_SHERPA["hwid"],
        "api_key": MOCK_SHERPA["api_key"],
        "fleet_name": "new_fleet",
        "sherpa_type": MOCK_SHERPA["sherpa_type"],
        "is_add": True
    }
    
    response = client.post(
        f"/api/v1/configure_fleet/switch_sherpa/{MOCK_SHERPA['name']}",
        json=switch_data,
        headers={"X-User-Token": auth_token}
    )
    assert response.status_code == 200
