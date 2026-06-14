import pytest
from fastapi.testclient import TestClient
from appserver.serveur_arbitre import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()
    assert response.json()["version"] == "1.2"

def test_hello():
    response = client.post("/hello")
    assert response.status_code == 200
    assert "rid" in response.json()
    assert len(response.json()["rid"]) > 0

def test_full_cycle():
    # 1. Enregistrement
    hello_response = client.post("/hello")
    assert hello_response.status_code == 200
    rid = hello_response.json()["rid"]

    # 2. Démarrage de la danse
    start_response = client.post("/start", json={"rid": rid})
    assert start_response.status_code == 200
    assert "steps" in start_response.json()

    # 3. Envoi d'un pas
    step_response = client.post("/step", json={"rid": rid, "col": "R", "arm": "ALU+ARU", "exp": "XSD"})
    assert step_response.status_code == 200
    assert "points" in step_response.json()

    # 4. Vérification du score
    score_response = client.request("GET", "/score", json={"rid": rid})
    assert score_response.status_code == 200
    assert "points" in score_response.json()
    assert score_response.json()["points"] == step_response.json()["points"]

    # 5. Déconnexion
    bye_response = client.post("/bye", json={"rid": rid})
    assert bye_response.status_code == 200
