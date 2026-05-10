from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
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

class BattleArbitre:
    # Moteur du jeu qui lit les règles et donne les points
    def __init__(self):
        self.rules = {}

    def evaluate_action(self, action: MovementAction, session: RobotSession):
        # TODO: Calculer les points en fonction de l'action et des règles
        pass

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Le Serveur Arbitre AKIMBOT est prêt !"}

if __name__ == "__main__":
    uvicorn.run("appserver.serveur_arbitre:app", host="0.0.0.0", port=8000, reload=True)
