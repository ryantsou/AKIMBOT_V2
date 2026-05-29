import sys
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QGroupBox
from PyQt5.QtCore import QThread

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

# --- 2. Thread d'arrière-plan pour uvicorn ---
class UvicornThread(QThread):
    def run(self):
        # Lancement du serveur sans bloquer l'interface PyQt5.
        # On passe l'objet `app` directement au lieu d'une chaîne de texte, et on enlève reload=True.
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# --- 3. Partie Interface Graphique (PyQt5) - Tâche #46 ---
class ArbitreWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AKIMBOT - Serveur Arbitre")
        self.resize(900, 600)
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        left_group = QGroupBox("Robots Connectés & Scores")
        left_layout = QVBoxLayout()
        self.score_placeholder = QLabel("En attente de la tâche #47 (Scores)...")
        left_layout.addWidget(self.score_placeholder)
        left_layout.addStretch()
        left_group.setLayout(left_layout)

        right_group = QGroupBox("Logs Réseau")
        right_layout = QVBoxLayout()
        self.log_placeholder = QLabel("En attente de la tâche #48 (Logs)...")
        right_layout.addWidget(self.log_placeholder)
        right_layout.addStretch()
        right_group.setLayout(right_layout)

        main_layout.addWidget(left_group, 1)
        main_layout.addWidget(right_group, 2)

        self.setCentralWidget(main_widget)

def main():
    qt_app = QApplication(sys.argv)
    window = ArbitreWindow()
    window.show()
    api_thread = UvicornThread()
    api_thread.start()
    sys.exit(qt_app.exec_())

if __name__ == "__main__":
    main()
