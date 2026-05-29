import sys
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QGroupBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from PyQt5.QtGui import QColor

app = FastAPI(title="AKIMBOT - Serveur Arbitre")

# Stockage en mémoire : robot_id -> score
robots_scores: dict = {}

class ServerSignals(QObject):
    new_log = pyqtSignal(str)
    robot_updated = pyqtSignal(str, int)  # (robot_id, score)

signals = ServerSignals()

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
    signals.new_log.emit("GET / - Vérification de l'état du serveur.")
    return {"status": "ok", "message": "Le Serveur Arbitre AKIMBOT est prêt !"}

@app.post("/robot/connect")
def robot_connect(session: RobotSession):
    if session.robot_id not in robots_scores:
        robots_scores[session.robot_id] = 0
    signals.new_log.emit(f"POST /robot/connect - Robot '{session.robot_id}' (équipe {session.team}) connecté.")
    signals.robot_updated.emit(session.robot_id, robots_scores[session.robot_id])
    return {"status": "connected", "robot_id": session.robot_id}

@app.post("/robot/score")
def update_score(session: RobotSession):
    robots_scores[session.robot_id] = session.current_score
    signals.new_log.emit(f"POST /robot/score - Robot '{session.robot_id}' → score {session.current_score}.")
    signals.robot_updated.emit(session.robot_id, session.current_score)
    return {"status": "updated", "robot_id": session.robot_id, "score": session.current_score}

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
        signals.new_log.connect(self.add_log)
        signals.robot_updated.connect(self.update_robot_table)

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        left_group = QGroupBox("Robots Connectés & Scores")
        left_layout = QVBoxLayout()

        self.robots_table = QTableWidget(0, 2)
        self.robots_table.setHorizontalHeaderLabels(["Robot", "Score"])
        self.robots_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.robots_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.robots_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.robots_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.robots_table.verticalHeader().setVisible(False)

        left_layout.addWidget(self.robots_table)
        left_group.setLayout(left_layout)

        right_group = QGroupBox("Logs Réseau")
        right_layout = QVBoxLayout()
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.append("Serveur démarré. En attente de requêtes...")
        right_layout.addWidget(self.log_console)
        right_group.setLayout(right_layout)

        main_layout.addWidget(left_group, 1)
        main_layout.addWidget(right_group, 2)

        self.setCentralWidget(main_widget)

    def add_log(self, message: str):
        self.log_console.append(message)

    def update_robot_table(self, robot_id: str, score: int):
        for row in range(self.robots_table.rowCount()):
            if self.robots_table.item(row, 0).text() == robot_id:
                self.robots_table.item(row, 1).setText(str(score))
                return
        row = self.robots_table.rowCount()
        self.robots_table.insertRow(row)
        self.robots_table.setItem(row, 0, QTableWidgetItem(robot_id))
        score_item = QTableWidgetItem(str(score))
        score_item.setForeground(QColor("#2ecc71"))
        self.robots_table.setItem(row, 1, score_item)

def main():
    qt_app = QApplication(sys.argv)
    window = ArbitreWindow()
    window.show()
    api_thread = UvicornThread()
    api_thread.start()
    sys.exit(qt_app.exec_())

if __name__ == "__main__":
    main()
