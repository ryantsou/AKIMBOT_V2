import sys
import signal
import json
import math
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit, QGridLayout, QComboBox)
from PyQt5.QtCore import QObject, pyqtSignal
import martypy

CALIBRATION_FILE = "calibration.json"

class ColorSensor:
	DEFAULT_COLORS = {
		"red":    [255,   0,   0],
		"green":  [  0, 255,   0],
		"blue":   [  0,   0, 255],
		"yellow": [255, 255,   0],
		"white":  [250, 250, 250],
		"black":  [ 10,  10,  10],
	}

	def __init__(self):
		self.calibration = self._load()

	def _load(self) -> dict:
		if os.path.exists(CALIBRATION_FILE):
			with open(CALIBRATION_FILE, "r") as f:
				return json.load(f)
		return dict(self.DEFAULT_COLORS)

	def _save(self):
		with open(CALIBRATION_FILE, "w") as f:
			json.dump(self.calibration, f, indent=2)

	def calibrer(self, couleur: str, r: int, g: int, b: int):
		self.calibration[couleur] = [r, g, b]
		self._save()

	def identifier(self, r: int, g: int, b: int, sensitivity: int = 150) -> str:
		min_dist = float("inf")
		detected = "unknown"
		for name, ref in self.calibration.items():
			dist = math.sqrt((r-ref[0])**2 + (g-ref[1])**2 + (b-ref[2])**2)
			if dist < min_dist:
				min_dist = dist
				detected = name
		return detected if min_dist < sensitivity else "unknown"

class ControllerSignals(QObject):
	log_message = pyqtSignal(str)
	connection_status = pyqtSignal(bool)

class MockMarty:
	def __init__(self, signals: ControllerSignals):
		self.signals = signals

	def celebrate(self):
		self.signals.log_message.emit("[MOCK] Marty fait une danse de célébration !")
        
	def walk(self, num_steps=2, turn=0, **kwargs):
		self.signals.log_message.emit(f"[MOCK] Le faux robot marche : {num_steps} pas, rotation {turn}, options: {kwargs}")

	def arms(self, left_angle, right_angle, move_time=1000, **kwargs):
		self.signals.log_message.emit(f"[MOCK] Bras - Gauche: {left_angle}°, Droit: {right_angle}°")

	def get_color_sensor_value_by_channel(self, add_on_name: str, channel_index: int) -> int:
		mock_rgb = {0: 180, 1: 30, 2: 25}
		return mock_rgb.get(channel_index, 0)

class MartyController:
	def __init__(self, method="wifi", address="mock"):
		self.method = method
		self.address = address
		self.connected = False
		self.marty = None
		self.signals = ControllerSignals()

	def connect(self):
		self.signals.log_message.emit(f"Tentative de connexion à Marty via {self.method} sur {self.address}...")
		try:
			if self.address == "mock":
				self.marty = MockMarty(self.signals)
			else:
				self.marty = martypy.Marty(self.method, self.address)
			self.connected = True
			self.signals.log_message.emit("Connexion à Marty réussie !")
			self.signals.connection_status.emit(True)
			return True
		except Exception as e:
			self.signals.log_message.emit(f"Erreur de connexion à Marty : {e}")
			self.connected = False
			self.signals.connection_status.emit(False)
			return False

	def test_mouvement(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Test basique : Marty célèbre !")
			self.marty.celebrate()
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de tester le mouvement.")

	def avancer(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty avance de 4 pas !")
			self.marty.walk(num_steps=4, turn=0)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible d'avancer.")

	def reculer(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty recule de 4 pas !")
			self.marty.walk(num_steps=4, step_length=-25, turn=0)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de reculer.")

	def tourner_gauche(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty tourne à gauche !")
			self.marty.walk(num_steps=2, turn=25)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de tourner.")

	def tourner_droite(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty tourne à droite !")
			self.marty.walk(num_steps=2, turn=-25)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de tourner.")

	def lever_bras_gauche(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty lève le bras gauche !")
			self.marty.arms(100, 0, 1000)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de bouger les bras.")

	def baisser_bras_gauche(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty baisse le bras gauche !")
			self.marty.arms(0, 0, 1000)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de bouger les bras.")

	def lever_bras_droit(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty lève le bras droit !")
			self.marty.arms(0, 100, 1000)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de bouger les bras.")

	def baisser_bras_droit(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty baisse le bras droit !")
			self.marty.arms(0, 0, 1000)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de bouger les bras.")

	def lire_rgb(self) -> tuple:
		if not self.connected or not self.marty:
			self.signals.log_message.emit("Marty non connecté. Impossible de lire le capteur couleur.")
			return None
		try:
			r = self.marty.get_color_sensor_value_by_channel("ColorSensor", 0)
			g = self.marty.get_color_sensor_value_by_channel("ColorSensor", 1)
			b = self.marty.get_color_sensor_value_by_channel("ColorSensor", 2)
			self.signals.log_message.emit(f"Capteur couleur brut — R:{r}  G:{g}  B:{b}")
			return (r, g, b)
		except Exception as e:
			self.signals.log_message.emit(f"Erreur lecture capteur couleur : {e}")
			return None

	def calibrer_couleur(self, couleur: str, color_sensor: ColorSensor):
		rgb = self.lire_rgb()
		if rgb is None:
			return
		r, g, b = rgb
		color_sensor.calibrer(couleur, r, g, b)
		self.signals.log_message.emit(f"Calibration '{couleur}' enregistrée — R:{r}  G:{g}  B:{b}")

class DanceParser:
	def parse(self, filepath: str) -> list:
		print(f"Lecture de la chorégraphie : {filepath}")
		return []

class ChoreographyPlayer:
	def __init__(self, controller: MartyController):
		self.controller = controller

	def play(self, sequence: list):
		print(f"Lancement de la chorégraphie ({len(sequence)} mouvements)")

class ArbitreAPIClient:
	def __init__(self, base_url="http://localhost:8000"):
		self.base_url = base_url

	def send_movement(self, action_type: str, color: str = None):
		payload = {"action_type": action_type, "color_detected": color}
		print(f"Envoi de l'action à l'arbitre : {payload}")

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("AKIMBOT - Client Robot")
		self.resize(900, 700)
        
		self.controller = MartyController(address="192.168.0.100")
		self.api_client = ArbitreAPIClient()
		self.parser = DanceParser()
		self.player = ChoreographyPlayer(self.controller)
		self.color_sensor = ColorSensor()
        
		self.controller.signals.log_message.connect(self.update_log)
		self.controller.signals.connection_status.connect(self.on_connection_status_changed)

		self.init_ui()

	def init_ui(self):
		main_widget = QWidget()
		main_layout = QHBoxLayout(main_widget)

		left_panel_layout = QVBoxLayout()

		connection_group = QGroupBox("Connexion")
		connection_layout = QVBoxLayout()
		self.status_label = QLabel("Statut : Déconnecté")
		connection_layout.addWidget(self.status_label)
		self.btn_connect = QPushButton("Connecter Marty")
		self.btn_connect.clicked.connect(self.connect_marty)
		connection_layout.addWidget(self.btn_connect)
		connection_group.setLayout(connection_layout)

		manual_controls_group = QGroupBox("Piloter Marty")
		manual_controls_layout = QGridLayout()
        
		self.btn_walk = QPushButton("Avancer")
		self.btn_walk.clicked.connect(self.walk_marty)
		self.btn_walk.setEnabled(False)
        
		self.btn_left = QPushButton("Gauche")
		self.btn_left.clicked.connect(self.left_marty)
		self.btn_left.setEnabled(False)
        
		self.btn_test = QPushButton("Célébrer")
		self.btn_test.clicked.connect(self.test_marty)
		self.btn_test.setEnabled(False)
        
		self.btn_right = QPushButton("Droite")
		self.btn_right.clicked.connect(self.right_marty)
		self.btn_right.setEnabled(False)
        
		self.btn_backward = QPushButton("Reculer")
		self.btn_backward.clicked.connect(self.backward_marty)
		self.btn_backward.setEnabled(False)

		self.btn_rgb = QPushButton("Lire capteur couleur (RGB)")
		self.btn_rgb.clicked.connect(self.lire_capteur_rgb)
		self.btn_rgb.setEnabled(False)

		manual_controls_layout.addWidget(self.btn_walk, 0, 1)
		manual_controls_layout.addWidget(self.btn_left, 1, 0)
		manual_controls_layout.addWidget(self.btn_test, 1, 1)
		manual_controls_layout.addWidget(self.btn_right, 1, 2)
		manual_controls_layout.addWidget(self.btn_backward, 2, 1)
		manual_controls_layout.addWidget(self.btn_rgb, 3, 0, 1, 3)
		manual_controls_group.setLayout(manual_controls_layout)

		arms_group = QGroupBox("Contrôles Bras")
		arms_layout = QGridLayout()

		self.btn_bras_gauche_up = QPushButton("Lever Bras G.")
		self.btn_bras_gauche_up.clicked.connect(self.controller.lever_bras_gauche)
		self.btn_bras_gauche_up.setEnabled(False)

		self.btn_bras_gauche_down = QPushButton("Baisser Bras G.")
		self.btn_bras_gauche_down.clicked.connect(self.controller.baisser_bras_gauche)
		self.btn_bras_gauche_down.setEnabled(False)

		self.btn_bras_droit_up = QPushButton("Lever Bras D.")
		self.btn_bras_droit_up.clicked.connect(self.controller.lever_bras_droit)
		self.btn_bras_droit_up.setEnabled(False)

		self.btn_bras_droit_down = QPushButton("Baisser Bras D.")
		self.btn_bras_droit_down.clicked.connect(self.controller.baisser_bras_droit)
		self.btn_bras_droit_down.setEnabled(False)

		arms_layout.addWidget(self.btn_bras_gauche_up, 0, 0)
		arms_layout.addWidget(self.btn_bras_gauche_down, 0, 1)
		arms_layout.addWidget(self.btn_bras_droit_up, 1, 0)
		arms_layout.addWidget(self.btn_bras_droit_down, 1, 1)
		arms_group.setLayout(arms_layout)

		calibration_group = QGroupBox("Calibrer le capteur couleur")
		calibration_layout = QVBoxLayout()
		self.color_combo = QComboBox()
		self.color_combo.addItems(["red", "green", "blue", "yellow", "white", "black"])
		calibration_layout.addWidget(self.color_combo)
		self.btn_calibrate = QPushButton("Calibrer cette couleur")
		self.btn_calibrate.clicked.connect(self.calibrer_couleur)
		self.btn_calibrate.setEnabled(False)
		calibration_layout.addWidget(self.btn_calibrate)
		calibration_group.setLayout(calibration_layout)

		left_panel_layout.addWidget(connection_group)
		left_panel_layout.addWidget(manual_controls_group)
		left_panel_layout.addWidget(arms_group)
		left_panel_layout.addWidget(calibration_group)
		left_panel_layout.addStretch()

		right_panel_layout = QVBoxLayout()
		self.log_console = QTextEdit()
		self.log_console.setReadOnly(True)
		right_panel_layout.addWidget(QLabel("Logs d'activité :"))
		right_panel_layout.addWidget(self.log_console)

		main_layout.addLayout(left_panel_layout, 1)
		main_layout.addLayout(right_panel_layout, 2)

		self.setCentralWidget(main_widget)

	def connect_marty(self):
		self.status_label.setText("Connexion en cours...")
		QApplication.processEvents()
		self.controller.connect()

	def on_connection_status_changed(self, connected: bool):
		if connected:
			self.status_label.setText(f"Statut : Connecté ({self.controller.method} - {self.controller.address}) !")
			buttons = [
				self.btn_walk, self.btn_left, self.btn_test, self.btn_right, self.btn_backward, self.btn_rgb, self.btn_calibrate,
				self.btn_bras_gauche_up, self.btn_bras_gauche_down, self.btn_bras_droit_up, self.btn_bras_droit_down
			]
			for btn in buttons:
				btn.setEnabled(True)
			self.btn_connect.setEnabled(False)
		else:
			self.status_label.setText("Statut : Échec de la connexion.")
			self.btn_connect.setEnabled(True)

	def update_log(self, message: str): self.log_console.append(message)
	def walk_marty(self): self.controller.avancer()
	def left_marty(self): self.controller.tourner_gauche()
	def test_marty(self): self.controller.test_mouvement()
	def right_marty(self): self.controller.tourner_droite()
	def backward_marty(self): self.controller.reculer()
	def lire_capteur_rgb(self): self.controller.lire_rgb()
	def calibrer_couleur(self): self.controller.calibrer_couleur(self.color_combo.currentText(), self.color_sensor)

if __name__ == "__main__":
	app = QApplication(sys.argv)
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
