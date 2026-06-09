import os
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn

app = FastAPI(title="AKIMBOT - Serveur Arbitre")

DEFAULT_BATTLE_FILE = Path(__file__).parent.parent / "example.battle"


class MovementAction(BaseModel):
    action_type: str
    color_detected: Optional[str] = None


class RobotSession(BaseModel):
    robot_id: str
    team: str
    current_score: int = 0


robot_sessions: Dict[str, RobotSession] = {}


class BattleArbitre:
    def __init__(self):
        self.max_score: int = 0
        self.rules: Dict[str, Dict[str, int]] = {}

    def load_rules(self, filepath: str):
        self.rules = {}
        self.max_score = 0
        current_color = None
        with open(filepath, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("MVS"):
                    self.max_score = int(line.split()[1])
                elif line.startswith("[") and line.endswith("]"):
                    current_color = line[1:-1].upper()
                    self.rules[current_color] = {}
                elif "=" in line and current_color is not None:
                    actions_part, value_str = line.rsplit("=", 1)
                    value = int(value_str)
                    if "+" in actions_part:
                        self.rules[current_color][actions_part.upper()] = value
                    else:
                        for action in actions_part.split(","):
                            self.rules[current_color][action.strip().upper()] = value

    def evaluate_action(self, action: MovementAction, session: RobotSession) -> int:
        color = (action.color_detected or "").upper()
        color_rules = self.rules.get(color, {})
        score_change = color_rules.get(action.action_type.upper(), 0)
        new_score = session.current_score + score_change
        if self.max_score > 0:
            new_score = max(0, min(new_score, self.max_score))
        session.current_score = new_score
        return session.current_score


arbitre = BattleArbitre()


@app.on_event("startup")
def startup():
    battle_path = Path(os.getenv("BATTLE_FILE", str(DEFAULT_BATTLE_FILE)))
    if battle_path.exists():
        arbitre.load_rules(str(battle_path))


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
