import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def user_data():
    return {
        "username": "testuser21",
        "email": "testuser21@example.com",
        "password": "String123_*"
    }


def test_register_user(user_data):
    # first signup
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 200

    assert response.json()["username"] == user_data["username"]

    # next signup (the same user)
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"
