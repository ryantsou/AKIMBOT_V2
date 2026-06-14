import os
import pytest
from fastapi.testclient import TestClient
import appserver.serveur_arbitre as module
from appserver.serveur_arbitre import app, BattleArbitre

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    yield
    with module.robots_lock:
        module.robots_scores.clear()


class TestBattleArbitre:
    def setup_method(self):
        self.arbitre = BattleArbitre()
        # Création de fausses règles pour les tests unitaires
        self.arbitre.rules = {
            "R": [
                {"type": "AND", "conds": ["ALU", "ARU"], "pts": 2},
                {"type": "OR", "conds": ["ALU", "ARU"], "pts": 1},
                {"type": "SINGLE", "conds": ["XSD"], "pts": -2}
            ]
        }

    def test_evaluate_and_condition(self):
        # ALU+ARU active le AND (+2 pts) et le OR (+1 pt) -> Total 3
        assert self.arbitre.evaluate("R", "ALU+ARU", "") == 3

    def test_evaluate_or_condition(self):
        # Un seul bras active uniquement le OR (+1 pt)
        assert self.arbitre.evaluate("R", "ALU", "") == 1
        assert self.arbitre.evaluate("R", "ARU", "") == 1

    def test_evaluate_single_condition(self):
        assert self.arbitre.evaluate("R", "", "XSD") == -2

    def test_unknown_color(self):
        assert self.arbitre.evaluate("Z", "ALU", "") == 0


class TestBattleFile:
    def _default_path(self):
        return os.path.join(os.path.dirname(module.__file__), "default.battle")

    def test_default_battle_file_loads_mvs(self):
        arbitre = BattleArbitre(self._default_path())
        assert arbitre.mvs_limit == 10

    def test_default_battle_file_preserves_scoring(self):
        arbitre = BattleArbitre(self._default_path())
        # Noir (N) : ALB+ARB=1, ALB=1, ARB=1 -> Total 3 pts
        assert arbitre.evaluate("N", "ALB+ARB", "XNT") == 3

    def test_missing_file_keeps_defaults(self):
        arbitre = BattleArbitre("fichier_inexistant.battle")
        assert arbitre.mvs_limit == 10
        assert arbitre.rules == {}
