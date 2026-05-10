import pytest
from fastapi.testclient import TestClient
from appserver.serveur_arbitre import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"
