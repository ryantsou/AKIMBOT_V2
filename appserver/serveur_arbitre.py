## reset all
import sys
import threading
import queue
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QGroupBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from PyQt5.QtGui import QColor

app = FastAPI(title="AKIMBOT - Serveur Arbitre")

robots_scores: dict = {}
robot_threads: dict = {}
robot_sessions: Dict[str, "RobotSession"] = {}
robots_lock = threading.Lock()


class ServerSignals(QObject):
    new_log = pyqtSignal(str)
    robot_updated = pyqtSignal(str, int)
    robot_disconnected = pyqtSignal(str)


signals = ServerSignals()


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


class BattleArbitre:
    def __init__(self):
        self.rules = {
            "celebrate": {"score_modifier": 10},
            "walk": {"score_modifier": 1, "color_bonus": {"red": 5, "blue": 2}},
            "turn": {"score_modifier": 0},
            "default": {"score_modifier": -1},
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


class RobotThread(threading.Thread):
    def __init__(self, robot_id: str, team: str):
        super().__init__(daemon=True)
        self.robot_id = robot_id
        self.team = team
        self.score = 0
        self._queue = queue.Queue()
        self._stop_event = threading.Event()

    def update_score(self, new_score: int):
        self._queue.put(new_score)

    def stop(self):
        self._stop_event.set()
        self._queue.put(None)

    def run(self):
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=1)
                if item is None:
                    break
                self.score = item
                with robots_lock:
                    robots_scores[self.robot_id] = self.score
                signals.robot_updated.emit(self.robot_id, self.score)
            except queue.Empty:
                continue


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Le Serveur Arbitre AKIMBOT est prêt !"}


@app.post("/api/mouvements")
def receive_movement(action: MovementAction, robot_id: str = "marty_01") -> MovementResponse:
    """Réception d'un mouvement, calcul du score via l'arbitre et retour du nouvel état."""
    with robots_lock:
        if robot_id not in robot_sessions:
            robot_sessions[robot_id] = RobotSession(robot_id=robot_id, team="blue", current_score=0)
            if robot_id not in robot_threads:
                thread = RobotThread(robot_id, "blue")
                thread.start()
                robot_threads[robot_id] = thread
                robots_scores[robot_id] = 0
        new_score = arbitre.evaluate_action(action, robot_sessions[robot_id])
        thread = robot_threads.get(robot_id)
    if thread:
        thread.update_score(new_score)
    return MovementResponse(
        robot_id=robot_id,
        action_type=action.action_type,
        color_detected=action.color_detected,
        new_score=new_score,
        message="Mouvement validé et score mis à jour."
    )


@app.post("/robot/connect")
def robot_connect(session: RobotSession):
    with robots_lock:
        if session.robot_id not in robot_threads:
            thread = RobotThread(session.robot_id, session.team)
            thread.start()
            robot_threads[session.robot_id] = thread
            robots_scores[session.robot_id] = 0
    signals.new_log.emit(f"POST /robot/connect - Robot '{session.robot_id}' (équipe {session.team}) connecté.")
    signals.robot_updated.emit(session.robot_id, 0)
    return {"status": "connected", "robot_id": session.robot_id}


@app.post("/robot/score")
def update_score(session: RobotSession):
    with robots_lock:
        thread = robot_threads.get(session.robot_id)
    if thread is None:
        return {"status": "error", "message": f"Robot '{session.robot_id}' non connecté."}
    thread.update_score(session.current_score)
    signals.new_log.emit(f"POST /robot/score - Robot '{session.robot_id}' → score {session.current_score}.")
    return {"status": "updated", "robot_id": session.robot_id, "score": session.current_score}


@app.post("/robot/disconnect")
def robot_disconnect(session: RobotSession):
    with robots_lock:
        thread = robot_threads.pop(session.robot_id, None)
        robots_scores.pop(session.robot_id, None)
    if thread:
        thread.stop()
    signals.new_log.emit(f"POST /robot/disconnect - Robot '{session.robot_id}' déconnecté.")
    signals.robot_disconnected.emit(session.robot_id)
    return {"status": "disconnected", "robot_id": session.robot_id}


class UvicornThread(QThread):
    def run(self):
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


class ArbitreWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AKIMBOT - Serveur Arbitre")
        self.resize(900, 600)
        self.init_ui()
        signals.new_log.connect(self.add_log)
        signals.robot_updated.connect(self.update_robot_table)
        signals.robot_disconnected.connect(self.remove_robot_from_table)

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        left_group = QGroupBox("Robots Connectés & Scores")
        left_layout = QVBoxLayout()

        self.current_score_label = QLabel("Score en temps réel : ")
        self.total_score_label = QLabel("Score total : 0")

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
        with robots_lock:
            self.total_score_label.setText(f"Score total : {sum(robots_scores.values())}")

    def remove_robot_from_table(self, robot_id: str):
        for row in range(self.robots_table.rowCount()):
            if self.robots_table.item(row, 0).text() == robot_id:
                self.robots_table.removeRow(row)
                return


def main():
    qt_app = QApplication(sys.argv)
    window = ArbitreWindow()
    window.show()
    api_thread = UvicornThread()
    api_thread.start()
    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    main()