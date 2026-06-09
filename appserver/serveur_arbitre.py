from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn

app = FastAPI(title="AKIMBOT - Serveur Arbitre")

class MovementResponse(BaseModel):
    robot_id: str
    action_type: str
    color_detected: Optional[str]
    new_score: int
    message: str

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
        
        self.rules = {
            "celebrate": {"score_modifier": 10},
            "walk": {"score_modifier": 1, "color_bonus": {"red": 5, "blue": 2}},
            "turn": {"score_modifier": 0},
            "default": {"score_modifier": 0} 
        }

<<<<<<< HEAD
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
def receive_movement(action: MovementAction, robot_id: str = "marty_01") -> MovementResponse:
    """Réception d'un mouvement, calcul du score via l'arbitre et retour du nouvel état."""
    if robot_id not in robot_sessions:
        robot_sessions[robot_id] = RobotSession(robot_id=robot_id, team="blue", current_score=0)
    
    new_score = arbitre.evaluate_action(action, robot_sessions[robot_id])
    
    return MovementResponse(
        robot_id=robot_id,
        action_type=action.action_type,
        color_detected=action.color_detected,
        new_score=new_score,
        message="Mouvement validé et score mis à jour."
    )
=======
    def evaluate_action(self, action: MovementAction, session: Optional[RobotSession] = None) -> int:
        # TODO: Calculer les points en fonction de l'action et des règles
        # Exemple minimal: renvoyer 1 point pour certaines actions, sinon 0
        if action.action_type.lower() in ("success", "score", "point"):
            return 1
        return 0
>>>>>>> e47b9009a754f392b70278ebb300c3574c5d5015

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Le Serveur Arbitre AKIMBOT est prêt !"}

<<<<<<< HEAD
=======
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

class MovementRequest(BaseModel):
    action: MovementAction
    session: Optional[RobotSession] = None

# POST /api/mouvements
@app.post("/api/mouvements")
def post_mouvement(payload: MovementRequest):
    """Recevoir un mouvement du robot, l'évaluer et renvoyer le score attribué."""
    arbitre = BattleArbitre()
    points = arbitre.evaluate_action(payload.action, payload.session)
    response = {
        "status": "ok",
        "awarded_points": points,
        "action_type": payload.action.action_type,
        "color_detected": payload.action.color_detected,
    }
    if payload.session:
        response["robot_id"] = payload.session.robot_id
        response["team"] = payload.session.team
    return response

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

        self.current_score_label = QLabel("Score en temps réel : aucun mouvement reçu")
        self.current_score_label.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        self.total_score_label = QLabel("Score total : 0")
        self.total_score_label.setStyleSheet("margin-bottom: 12px;")

        self.robots_table = QTableWidget(0, 2)
        self.robots_table.setHorizontalHeaderLabels(["Robot", "Score"])
        self.robots_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.robots_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.robots_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.robots_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.robots_table.verticalHeader().setVisible(False)

        left_layout.addWidget(self.current_score_label)
        left_layout.addWidget(self.total_score_label)
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
        updated = False
        for row in range(self.robots_table.rowCount()):
            if self.robots_table.item(row, 0).text() == robot_id:
                self.robots_table.item(row, 1).setText(str(score))
                updated = True
                break
        if not updated:
            row = self.robots_table.rowCount()
            self.robots_table.insertRow(row)
            self.robots_table.setItem(row, 0, QTableWidgetItem(robot_id))
            score_item = QTableWidgetItem(str(score))
            score_item.setForeground(QColor("#2ecc71"))
            self.robots_table.setItem(row, 1, score_item)

        self.current_score_label.setText(f"Score en temps réel : {robot_id} → {score}")
        self.total_score_label.setText(f"Score total : {sum(robots_scores.values())}")

def main():
    qt_app = QApplication(sys.argv)
    window = ArbitreWindow()
    window.show()
    api_thread = UvicornThread()
    api_thread.start()
    sys.exit(qt_app.exec_())

>>>>>>> e47b9009a754f392b70278ebb300c3574c5d5015
if __name__ == "__main__":
    uvicorn.run("appserver.serveur_arbitre:app", host="0.0.0.0", port=8000, reload=True)
