import os
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
import appserver.serveur_arbitre as module
from appserver.serveur_arbitre import app, BattleArbitre, MovementAction, RobotSession

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    yield
    with module.robots_lock:
        threads = list(module.robot_threads.values())
        module.robot_threads.clear()
        module.robots_scores.clear()
        module.robot_sessions.clear()
    for thread in threads:
        thread.stop()


class TestBattleArbitre:
    def setup_method(self):
        self.arbitre = BattleArbitre()

    def test_celebrate_adds_ten(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="celebrate"), session)
        assert score == 10

    def test_walk_no_color_adds_one(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="walk"), session)
        assert score == 1

    def test_walk_red_adds_six(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="walk", color_detected="red"), session)
        assert score == 6

    def test_walk_blue_adds_three(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="walk", color_detected="blue"), session)
        assert score == 3

    def test_turn_no_change(self):
        session = RobotSession(robot_id="r1", team="blue", current_score=5)
        score = self.arbitre.evaluate_action(MovementAction(action_type="turn"), session)
        assert score == 5

    def test_unknown_action_subtracts_one(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="fly"), session)
        assert score == -1

    def test_score_accumulates(self):
        session = RobotSession(robot_id="r1", team="blue")
        self.arbitre.evaluate_action(MovementAction(action_type="walk"), session)
        self.arbitre.evaluate_action(MovementAction(action_type="walk"), session)
        score = self.arbitre.evaluate_action(MovementAction(action_type="celebrate"), session)
        assert score == 12

    def test_color_ignored_for_celebrate(self):
        session = RobotSession(robot_id="r1", team="blue")
        score = self.arbitre.evaluate_action(MovementAction(action_type="celebrate", color_detected="red"), session)
        assert score == 10


class TestBattleFile:
    def _default_path(self):
        return os.path.join(os.path.dirname(module.__file__), "default.battle")

    def test_default_battle_file_loads_mvs(self):
        arbitre = BattleArbitre(self._default_path())
        assert arbitre.mvs_limit == 50

    def test_default_battle_file_preserves_scoring(self):
        arbitre = BattleArbitre(self._default_path())
        session = RobotSession(robot_id="r1", team="blue")
        assert arbitre.evaluate_action(MovementAction(action_type="walk", color_detected="red"), session) == 6

    def test_missing_file_keeps_defaults(self):
        arbitre = BattleArbitre("fichier_inexistant.battle")
        session = RobotSession(robot_id="r1", team="blue")
        assert arbitre.evaluate_action(MovementAction(action_type="celebrate"), session) == 10
        assert arbitre.mvs_limit == 0

    def test_custom_rules_and_limit_from_file(self, tmp_path):
        battle = tmp_path / "custom.battle"
        battle.write_text("[LIMITE]\nMVS=10\n\n[REGLES]\ncelebrate: 100\ndefault: -5\n", encoding="utf-8")
        arbitre = BattleArbitre(str(battle))
        assert arbitre.mvs_limit == 10
        session = RobotSession(robot_id="r1", team="blue")
        assert arbitre.evaluate_action(MovementAction(action_type="celebrate"), session) == 100
        other = RobotSession(robot_id="r2", team="blue")
        assert arbitre.evaluate_action(MovementAction(action_type="fly"), other) == -5

    def test_color_bonus_parsed_from_file(self, tmp_path):
        battle = tmp_path / "couleurs.battle"
        battle.write_text("[REGLES]\nwalk: 2, red=8, green=3\n", encoding="utf-8")
        arbitre = BattleArbitre(str(battle))
        session = RobotSession(robot_id="r1", team="blue")
        assert arbitre.evaluate_action(MovementAction(action_type="walk", color_detected="green"), session) == 5

    def test_limite_atteinte(self, tmp_path):
        battle = tmp_path / "limite.battle"
        battle.write_text("[LIMITE]\nMVS=3\n", encoding="utf-8")
        arbitre = BattleArbitre(str(battle))
        assert arbitre.limite_atteinte(2) is False
        assert arbitre.limite_atteinte(3) is True

    def test_no_limit_means_never_reached(self):
        arbitre = BattleArbitre()
        assert arbitre.limite_atteinte(9999) is False


class TestRouteRoot:
    def test_returns_ok(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestRouteRobotConnect:
    def test_connect_new_robot(self):
        response = client.post("/robot/connect", json={"robot_id": "bot_1", "team": "red"})
        assert response.status_code == 200
        assert response.json() == {"status": "connected", "robot_id": "bot_1"}

    def test_connect_creates_thread(self):
        client.post("/robot/connect", json={"robot_id": "bot_1", "team": "red"})
        assert "bot_1" in module.robot_threads
        assert module.robot_threads["bot_1"].is_alive()

    def test_connect_same_robot_twice_is_idempotent(self):
        payload = {"robot_id": "bot_1", "team": "red"}
        client.post("/robot/connect", json=payload)
        response = client.post("/robot/connect", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "connected"
        assert list(module.robot_threads.keys()).count("bot_1") == 1


class TestRouteRobotScore:
    def test_update_score_connected_robot(self):
        client.post("/robot/connect", json={"robot_id": "bot_2", "team": "blue"})
        response = client.post("/robot/score", json={"robot_id": "bot_2", "team": "blue", "current_score": 42})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["score"] == 42

    def test_update_score_unknown_robot_returns_error(self):
        response = client.post("/robot/score", json={"robot_id": "ghost", "team": "blue", "current_score": 10})
        assert response.status_code == 200
        assert response.json()["status"] == "error"


class TestRouteRobotDisconnect:
    def test_disconnect_connected_robot(self):
        client.post("/robot/connect", json={"robot_id": "bot_3", "team": "red"})
        response = client.post("/robot/disconnect", json={"robot_id": "bot_3", "team": "red"})
        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"

    def test_disconnect_removes_thread(self):
        client.post("/robot/connect", json={"robot_id": "bot_3", "team": "red"})
        client.post("/robot/disconnect", json={"robot_id": "bot_3", "team": "red"})
        assert "bot_3" not in module.robot_threads

    def test_disconnect_unknown_robot(self):
        response = client.post("/robot/disconnect", json={"robot_id": "ghost", "team": "blue"})
        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"


class TestRouteMouvements:
    def test_celebrate_returns_score_ten(self):
        response = client.post("/api/mouvements?robot_id=m_bot1", json={"action_type": "celebrate"})
        assert response.status_code == 200
        assert response.json()["new_score"] == 10

    def test_walk_red_returns_score_six(self):
        response = client.post(
            "/api/mouvements?robot_id=m_bot2",
            json={"action_type": "walk", "color_detected": "red"}
        )
        assert response.status_code == 200
        assert response.json()["new_score"] == 6

    def test_unknown_action_returns_minus_one(self):
        response = client.post("/api/mouvements?robot_id=m_bot3", json={"action_type": "fly"})
        assert response.status_code == 200
        assert response.json()["new_score"] == -1

    def test_score_accumulates_across_requests(self):
        client.post("/api/mouvements?robot_id=m_bot4", json={"action_type": "walk"})
        client.post("/api/mouvements?robot_id=m_bot4", json={"action_type": "walk"})
        response = client.post("/api/mouvements?robot_id=m_bot4", json={"action_type": "walk"})
        assert response.json()["new_score"] == 3

    def test_response_contains_required_fields(self):
        response = client.post(
            "/api/mouvements?robot_id=m_bot5",
            json={"action_type": "turn", "color_detected": "red"}
        )
        data = response.json()
        assert "robot_id" in data
        assert "action_type" in data
        assert "new_score" in data
        assert "message" in data

    def test_default_robot_id_used_when_omitted(self):
        response = client.post("/api/mouvements", json={"action_type": "celebrate"})
        assert response.status_code == 200
        assert response.json()["robot_id"] == "marty_01"

    def test_first_movement_creates_thread(self):
        client.post("/api/mouvements?robot_id=m_bot6", json={"action_type": "walk"})
        assert "m_bot6" in module.robot_threads
        assert module.robot_threads["m_bot6"].is_alive()


class TestMovementParsing:
    def test_action_type_is_lowercased_and_stripped(self):
        action = MovementAction(action_type="  WALK ")
        assert action.action_type == "walk"

    def test_color_is_lowercased_and_stripped(self):
        action = MovementAction(action_type="walk", color_detected=" RED ")
        assert action.color_detected == "red"

    def test_unknown_color_becomes_none(self):
        action = MovementAction(action_type="walk", color_detected="unknown")
        assert action.color_detected is None

    def test_empty_color_becomes_none(self):
        action = MovementAction(action_type="walk", color_detected="   ")
        assert action.color_detected is None

    def test_empty_action_type_is_rejected(self):
        with pytest.raises(ValidationError):
            MovementAction(action_type="   ")

    def test_uppercase_payload_still_scores(self):
        response = client.post(
            "/api/mouvements?robot_id=parse_bot",
            json={"action_type": "WALK", "color_detected": "RED"}
        )
        assert response.status_code == 200
        assert response.json()["new_score"] == 6

    def test_empty_action_type_returns_422(self):
        response = client.post("/api/mouvements?robot_id=parse_bot2", json={"action_type": ""})
        assert response.status_code == 422
