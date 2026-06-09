from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn

app = FastAPI(title="AKIMBOT - Serveur Arbitre")

class MovementAction(BaseModel):
    # Données envoyées par le robot après un mouvement
    action_type: str
    color_detected: Optional[str] = None

class RobotSession(BaseModel):
    # Etat d'un robot pendant le match
    robot_id: str
    team: str
    current_score: int = 0

robot_sessions: Dict[str, RobotSession] = {}

class BattleArbitre:
    # Moteur du jeu qui lit les règles et donne les points
    def __init__(self):
        # Règles simplifiées pour le test
        self.rules = {
            "celebrate": {"score_modifier": 10},
            "walk": {"score_modifier": 1, "color_bonus": {"red": 5, "blue": 2}},
            "turn": {"score_modifier": 0},
            "default": {"score_modifier": -1} # Pénalité pour action non reconnue
        }

    def evaluate_action(self, action: MovementAction, session: RobotSession):
        score_change = 0
        rule = self.rules.get(action.action_type, self.rules["default"])
        
        score_change += rule.get("score_modifier", 0)

        if action.color_detected and "color_bonus" in rule:
            color_bonus = rule["color_bonus"].get(action.color_detected, 0)
            score_change += color_bonus

        session.current_score += score_change
        return session.current_score

arbitre = BattleArbitre()

@app.post("/api/mouvements")
def receive_movement(action: MovementAction, robot_id: str = "marty_01"):
    if robot_id not in robot_sessions:
        robot_sessions[robot_id] = RobotSession(robot_id=robot_id, team="blue", current_score=0)
    new_score = arbitre.evaluate_action(action, robot_sessions[robot_id])
    return {"robot_id": robot_id, "new_score": new_score}

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Le Serveur Arbitre AKIMBOT est prêt !"}

if __name__ == "__main__":
    uvicorn.run("appserver.serveur_arbitre:app", host="0.0.0.0", port=8000, reload=True)
