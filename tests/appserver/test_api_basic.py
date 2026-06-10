from fastapi.testclient import TestClient
from appserver.serveur_arbitre import app, robot_sessions, robot_threads, robots_scores

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"


def test_robot_connect_and_disconnect_cleanup():
    robot_id = "pytest_robot"
    payload = {"robot_id": robot_id, "team": "blue", "current_score": 0}

    connect_response = client.post("/robot/connect", json=payload)
    assert connect_response.status_code == 200
    assert robot_id in robot_threads
    assert robot_id in robot_sessions
    assert robot_id in robots_scores

    disconnect_response = client.post("/robot/disconnect", json=payload)
    assert disconnect_response.status_code == 200
    assert robot_id not in robot_threads
    assert robot_id not in robot_sessions
    assert robot_id not in robots_scores
