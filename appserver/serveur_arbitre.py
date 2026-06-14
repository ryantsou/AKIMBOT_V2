import sys
import os
import uuid
import threading
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
robots_lock = threading.Lock()


class ServerSignals(QObject):
    new_log = pyqtSignal(str)
    robot_updated = pyqtSignal(str, int)
    robot_disconnected = pyqtSignal(str)


signals = ServerSignals()


class StartRequest(BaseModel):
    rid: str


class StepRequest(BaseModel):
    rid: str
    col: str
    arm: str
    exp: str


class ScoreRequest(BaseModel):
    rid: str


class ByeRequest(BaseModel):
    rid: str


class BattleArbitre:
    def __init__(self, battle_file: Optional[str] = None):
        self.mvs_limit = 10
        self.rules = {}
        if battle_file:
            self.charger_battle(battle_file)

    def charger_battle(self, battle_file: str) -> bool:
        if not os.path.exists(battle_file):
            return False
        try:
            self.rules = {}
            current_color = None
            with open(battle_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    
                    if line.startswith("MVS"):
                        try:
                            self.mvs_limit = int(line.split()[1])
                        except Exception:
                            pass
                    elif line.startswith("[") and line.endswith("]"):
                        current_color = line[1:-1]
                        self.rules[current_color] = []
                    elif "=" in line and current_color:
                        cond_str, pts_str = line.split("=")
                        try:
                            pts = int(pts_str)
                            if "+" in cond_str:
                                conds = cond_str.split("+")
                                self.rules[current_color].append({"type": "AND", "conds": conds, "pts": pts})
                            elif "," in cond_str:
                                conds = cond_str.split(",")
                                self.rules[current_color].append({"type": "OR", "conds": conds, "pts": pts})
                            else:
                                self.rules[current_color].append({"type": "SINGLE", "conds": [cond_str], "pts": pts})
                        except Exception:
                            pass
            return True
        except Exception:
            return False

    def evaluate(self, col: str, arm: str, exp: str) -> int:
        if col not in self.rules:
            return 0
        
        active_arms = set(arm.split("+")) if arm else set()
        active_states = active_arms.copy()
        if exp:
            active_states.add(exp)
            
        points = 0
        for rule in self.rules[col]:
            conds = set(rule["conds"])
            if rule["type"] == "AND":
                if conds.issubset(active_states):
                    points += rule["pts"]
            elif rule["type"] == "OR":
                if not conds.isdisjoint(active_states):
                    points += rule["pts"]
            elif rule["type"] == "SINGLE":
                if conds.issubset(active_states):
                    points += rule["pts"]
        return points


BATTLE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default.battle")
arbitre = BattleArbitre(BATTLE_FILE)


@app.get("/")
def read_root():
    return {"version": "1.2"}


@app.post("/hello")
def hello():
    rid = str(uuid.uuid4())[:6].upper()
    with robots_lock:
        robots_scores[rid] = 0
    signals.new_log.emit(f"Nouveau robot enregistré : {rid}")
    signals.robot_updated.emit(rid, 0)
    return {"rid": rid}


@app.post("/start")
def start(req: StartRequest):
    signals.new_log.emit(f"Robot {req.rid} démarre une chorégraphie (MVS attendus: {arbitre.mvs_limit})")
    return {"steps": arbitre.mvs_limit}


@app.post("/step")
def step(req: StepRequest):
    points = arbitre.evaluate(req.col, req.arm, req.exp)
    with robots_lock:
        if req.rid in robots_scores:
            robots_scores[req.rid] += points
        else:
            robots_scores[req.rid] = points
        total = robots_scores[req.rid]
    signals.new_log.emit(f"Step {req.rid} | {req.col} {req.arm} {req.exp} -> {points} pts (Total: {total})")
    signals.robot_updated.emit(req.rid, total)
    return {"points": points}


@app.get("/score")
def get_score(req: ScoreRequest):
    with robots_lock:
        pts = robots_scores.get(req.rid, 0)
    return {"points": pts}


@app.post("/bye")
def bye(req: ByeRequest):
    with robots_lock:
        if req.rid in robots_scores:
            del robots_scores[req.rid]
    signals.new_log.emit(f"Robot {req.rid} déconnecté.")
    signals.robot_disconnected.emit(req.rid)
    return {}


class UvicornThread(QThread):
    def run(self):
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


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