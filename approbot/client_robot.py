import sys
import signal
import json
import math
import os, requests
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit, QGridLayout, QComboBox, QLineEdit, QFileDialog, QProgressBar, QDialog)
from PyQt5.QtCore import QObject, pyqtSignal
import martypy

CALIBRATION_FILE = "calibration_couleurs.json"

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
	dance_progress = pyqtSignal(int, int)
	battery_updated = pyqtSignal(float)
	score_updated = pyqtSignal(int)
	color_detected = pyqtSignal(str)

class MockMarty:
	def __init__(self, signals: ControllerSignals):
		self.signals = signals

	def celebrate(self):
		self.signals.log_message.emit("[MOCK] celebrate()")

	def walk(self, num_steps=2, turn=0, **kwargs):
		self.signals.log_message.emit(f"[MOCK] walk(num_steps={num_steps}, turn={turn})")

	def turn(self, num_steps=2, turn=25, move_time=1500):
		self.signals.log_message.emit(f"[MOCK] turn(num_steps={num_steps}, turn={turn})")

	def arms(self, left_angle, right_angle, move_time=1000, **kwargs):
		self.signals.log_message.emit(f"[MOCK] arms(left={left_angle}°, right={right_angle}°)")

	def eyes(self, pose_or_angle, **kwargs):
		self.signals.log_message.emit(f"[MOCK] eyes({pose_or_angle})")

	def get_color_sensor_value_by_channel(self, add_on_name: str, channel_index: int) -> int:
		mock_rgb = {0: 180, 1: 30, 2: 25}
		return mock_rgb.get(channel_index, 0)

	def get_ground_sensor_reading(self, foot: str):
		mock_ground_rgb = {
			"left":  (180, 30, 25),
			"right": (30, 180, 25),
		}
		return mock_ground_rgb.get(foot.lower(), (0, 0, 0))

	def get_battery_remaining(self) -> float:
		self.signals.log_message.emit("[MOCK] Lecture de la batterie...")
		return 85.5

	def get_battery_voltage(self) -> float:
		return 8.2

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
			self.marty.turn(num_steps=2, turn=25)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de tourner.")

	def tourner_droite(self):
		if self.connected and self.marty:
			self.signals.log_message.emit("Action : Marty tourne à droite !")
			self.marty.turn(num_steps=2, turn=-25)
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

	def bouger_yeux(self, expression: str):
		if self.connected and self.marty:
			self.signals.log_message.emit(f"Action : Marty change ses yeux ({expression}) !")
			self.marty.eyes(expression)
		else:
			self.signals.log_message.emit("Marty n'est pas connecté. Impossible de bouger les yeux.")

	def lire_batterie(self) -> float:
		if not self.connected or not self.marty:
			self.signals.log_message.emit("Marty non connecté. Impossible de lire la batterie.")
			return 0.0
		try:
			bat = self.marty.get_battery_remaining()
			if bat == 0:
				try:
					volt = self.marty.get_battery_voltage()
					self.signals.log_message.emit(f"Alerte : Batterie à 0%. Voltage brut : {volt}V (En charge ?)")
				except Exception:
					pass
			self.signals.log_message.emit(f"Niveau de batterie : {bat}%")
			self.signals.battery_updated.emit(float(bat))
			return bat
		except Exception as e:
			self.signals.log_message.emit(f"Erreur lecture batterie : {e}")
			return 0.0

	def lire_rgb(self, source: str = "foot", foot: str = "left") -> tuple:
		if not self.connected or not self.marty:
			self.signals.log_message.emit("Marty non connecté. Impossible de lire le capteur couleur.")
			return None
		try:
			if source == "color" and hasattr(self.marty, "get_color_sensor_value_by_channel"):
				r = self.marty.get_color_sensor_value_by_channel("ColorSensor", 0)
				g = self.marty.get_color_sensor_value_by_channel("ColorSensor", 1)
				b = self.marty.get_color_sensor_value_by_channel("ColorSensor", 2)
				self.signals.log_message.emit(f"Capteur add-on brut — R:{r}  G:{g}  B:{b}")
			elif source == "foot" and hasattr(self.marty, "get_ground_sensor_reading"):
				raw = self.marty.get_ground_sensor_reading(foot.lower())
				if isinstance(raw, (tuple, list)) and len(raw) == 3:
					r, g, b = raw
				elif isinstance(raw, dict):
					r = int(raw.get("r", raw.get("red", 0)))
					g = int(raw.get("g", raw.get("green", 0)))
					b = int(raw.get("b", raw.get("blue", 0)))
				else:
					r = g = b = int(raw)
				self.signals.log_message.emit(f"Capteur pied brut ({foot}) — R:{r}  G:{g}  B:{b}")
			else:
				# Fallback: try color add-on first, then foot ground sensor
				if hasattr(self.marty, "get_color_sensor_value_by_channel"):
					r = self.marty.get_color_sensor_value_by_channel("ColorSensor", 0)
					g = self.marty.get_color_sensor_value_by_channel("ColorSensor", 1)
					b = self.marty.get_color_sensor_value_by_channel("ColorSensor", 2)
					self.signals.log_message.emit(f"Capteur add-on brut — R:{r}  G:{g}  B:{b}")
				elif hasattr(self.marty, "get_ground_sensor_reading"):
					raw = self.marty.get_ground_sensor_reading(foot.lower())
					if isinstance(raw, (tuple, list)) and len(raw) == 3:
						r, g, b = raw
					elif isinstance(raw, dict):
						r = int(raw.get("r", raw.get("red", 0)))
						g = int(raw.get("g", raw.get("green", 0)))
						b = int(raw.get("b", raw.get("blue", 0)))
					else:
						r = g = b = int(raw)
					self.signals.log_message.emit(f"Capteur pied brut ({foot}) — R:{r}  G:{g}  B:{b}")
				else:
					raise AttributeError("Aucun capteur couleur compatible trouvé sur Marty")
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
		sequence = []
		try:
			with open(filepath, "r", encoding="utf-8") as f:
				for line in f:
					line = line.strip()
					if not line or line.startswith("#"):
						continue
					sequence.append(line)
		except Exception as e:
			print(f"Erreur lecture .dance: {e}")
		return sequence

class ChoreographyPlayer:
	def __init__(self, controller: MartyController, api_client: 'ArbitreAPIClient'):
		self.controller = controller
		self.api_client = api_client

	def play(self, sequence: list, progress_callback=None):
		"""Joue la séquence et informe l'arbitre de chaque mouvement pour mettre à jour le score."""
		total = len(sequence)
		self.controller.signals.log_message.emit(f"Lancement de la chorégraphie ({total} mouvements)...")
		for idx, action in enumerate(sequence, start=1):
			self.controller.signals.log_message.emit(f"Exécution action {idx}/{total}: {action}")
			self.api_client.send_movement(action) # Envoi à l'arbitre
			time.sleep(0.5)
			self.controller.signals.dance_progress.emit(idx, total)
			QApplication.processEvents() # Ensure UI updates

class ArbitreAPIClient:
	def __init__(self, signals: ControllerSignals, base_url="http://localhost:8000"):
		self.base_url = base_url
		self.signals = signals

	def send_movement(self, action_type: str, color: str = None, robot_id: str = "marty_01"):
		payload = {"action_type": action_type, "color_detected": color}
		self.signals.log_message.emit(f"[API] Envoi à l'arbitre : {action_type} ({color or 'N/A'})")
		try:
			response = requests.post(f"{self.base_url}/api/mouvements?robot_id={robot_id}", json=payload, timeout=5)
			response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP
			data = response.json()
			new_score = data.get("new_score", 0)
			self.signals.log_message.emit(f"[API] Score actuel : {new_score}")
			self.signals.score_updated.emit(new_score)
		except requests.exceptions.ConnectionError:
			self.signals.log_message.emit(f"[API] Erreur de connexion à l'arbitre à {self.base_url}")
		except requests.exceptions.HTTPError as e:
			self.signals.log_message.emit(f"[API] Erreur HTTP de l'arbitre : {e} - {e.response.text}")
		except Exception as e:
			self.signals.log_message.emit(f"[API] Erreur inattendue lors de l'envoi à l'arbitre : {e}")

class CalibrationDialog(QDialog):
	COLORS = [
		("ROUGE", "red"),
		("VERT",  "green"),
		("BLEU",  "blue"),
		("JAUNE", "yellow"),
		("NOIR",  "black"),
		("BLANC", "white"),
	]

	def __init__(self, controller: MartyController, color_sensor: ColorSensor, parent=None):
		super().__init__(parent)
		self.controller = controller
		self.color_sensor = color_sensor
		self.rgb_data = {key: list(color_sensor.calibration.get(key, [0, 0, 0])) for _, key in self.COLORS}
		self._rgb_labels = {}
		self.setWindowTitle("Calibration du capteur couleur")
		self.setMinimumWidth(480)
		self._init_ui()

	def _init_ui(self):
		layout = QVBoxLayout(self)
		grid = QGridLayout()
		grid.addWidget(QLabel("Couleur"), 0, 0)
		grid.addWidget(QLabel("R"), 0, 1)
		grid.addWidget(QLabel("G"), 0, 2)
		grid.addWidget(QLabel("B"), 0, 3)
		for row, (display_name, key) in enumerate(self.COLORS, start=1):
			r, g, b = self.rgb_data[key]
			lbl_r = QLabel(str(r))
			lbl_g = QLabel(str(g))
			lbl_b = QLabel(str(b))
			btn_read = QPushButton("Lire")
			btn_read.clicked.connect(lambda _, k=key: self._lire(k))
			self._rgb_labels[key] = (lbl_r, lbl_g, lbl_b)
			grid.addWidget(QLabel(display_name), row, 0)
			grid.addWidget(lbl_r, row, 1)
			grid.addWidget(lbl_g, row, 2)
			grid.addWidget(lbl_b, row, 3)
			grid.addWidget(btn_read, row, 4)
		layout.addLayout(grid)
		self._status_label = QLabel("")
		layout.addWidget(self._status_label)
		btn_row = QHBoxLayout()
		btn_save = QPushButton("Sauvegarder")
		btn_save.clicked.connect(self._sauvegarder)
		btn_close = QPushButton("Fermer")
		btn_close.clicked.connect(self.accept)
		btn_row.addWidget(btn_save)
		btn_row.addWidget(btn_close)
		layout.addLayout(btn_row)

	def _lire(self, key: str):
		rgb = self.controller.lire_rgb()
		if rgb is None:
			return
		r, g, b = rgb
		self.rgb_data[key] = [r, g, b]
		lbl_r, lbl_g, lbl_b = self._rgb_labels[key]
		lbl_r.setText(str(r))
		lbl_g.setText(str(g))
		lbl_b.setText(str(b))

	def _sauvegarder(self):
		self.color_sensor.calibration = dict(self.rgb_data)
		self.color_sensor._save()
		self._status_label.setText("Calibration sauvegardée dans calibration_couleurs.json.")


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("AKIMBOT - Client Robot")
		self.resize(900, 700)
        
		self.controller = MartyController(address="192.168.0.100")
		self.api_client = ArbitreAPIClient(self.controller.signals)
		self.parser = DanceParser()
		self.player = ChoreographyPlayer(self.controller, self.api_client)
		self.color_sensor = ColorSensor()
		self.current_sequence = []
        
		self.controller.signals.log_message.connect(self.update_log)
		self.controller.signals.connection_status.connect(self.on_connection_status_changed)
		self.controller.signals.dance_progress.connect(self.update_dance_progress)
		self.controller.signals.battery_updated.connect(self.update_battery_ui)
		self.controller.signals.score_updated.connect(self.update_score_ui)
		self.controller.signals.color_detected.connect(self.update_color_ui)

		self.init_ui()

	def init_ui(self):
		main_widget = QWidget()
		main_layout = QHBoxLayout(main_widget)

		left_panel_layout = QVBoxLayout()

		connection_group = QGroupBox("Connexion")
		connection_layout = QVBoxLayout()

		self.method_combo = QComboBox()
		self.method_combo.addItems(["wifi", "usb", "mock"])
		self.method_combo.currentTextChanged.connect(self.on_method_changed)
		connection_layout.addWidget(QLabel("Méthode :"))
		connection_layout.addWidget(self.method_combo)

		self.address_input = QLineEdit()
		self.address_input.setText("192.168.0.100")
		connection_layout.addWidget(QLabel("Adresse (IP, port USB ou mock) :"))
		connection_layout.addWidget(self.address_input)

		self.status_label = QLabel("Statut : Déconnecté")
		connection_layout.addWidget(self.status_label)
		self.btn_connect = QPushButton("Connecter Marty")
		self.btn_connect.clicked.connect(self.connect_marty)
		connection_layout.addWidget(self.btn_connect)
		connection_group.setLayout(connection_layout)

		telemetry_group = QGroupBox("Télémétrie")
		telemetry_layout = QVBoxLayout()
		self.battery_label = QLabel("Batterie : Inconnue")
		self.color_label = QLabel("Couleur détectée : Inconnue")
		self.score_label = QLabel("Score : 0")
		self.battery_bar = QProgressBar()
		self.battery_bar.setRange(0, 100)
		self.battery_bar.setValue(0)
		telemetry_layout.addWidget(self.battery_label)
		telemetry_layout.addWidget(self.battery_bar)
		telemetry_layout.addWidget(self.color_label)
		telemetry_layout.addWidget(self.score_label)
		telemetry_group.setLayout(telemetry_layout)

		manual_controls_group = QGroupBox("Piloter Marty")
		manual_controls_layout = QGridLayout()
        
		self.btn_walk = QPushButton("Avancer")
		self.btn_walk.clicked.connect(self.controller.avancer)
		self.btn_walk.setEnabled(False)

		self.btn_left = QPushButton("Gauche")
		self.btn_left.clicked.connect(self.controller.tourner_gauche)
		self.btn_left.setEnabled(False)

		self.btn_test = QPushButton("Célébrer")
		self.btn_test.clicked.connect(self.controller.test_mouvement)
		self.btn_test.setEnabled(False)

		self.btn_right = QPushButton("Droite")
		self.btn_right.clicked.connect(self.controller.tourner_droite)
		self.btn_right.setEnabled(False)

		self.btn_backward = QPushButton("Reculer")
		self.btn_backward.clicked.connect(self.controller.reculer)
		self.btn_backward.setEnabled(False)

		self.sensor_source_combo = QComboBox()
		self.sensor_source_combo.addItems(["Pied gauche", "Pied droit", "Capteur couleur"])
		self.sensor_source_combo.setEnabled(False)

		self.btn_rgb = QPushButton("Lire capteur couleur (RGB)")
		self.btn_rgb.clicked.connect(self.lire_capteur_rgb)
		self.btn_rgb.setEnabled(False)

		self.btn_battery = QPushButton("Lire Batterie")
		self.btn_battery.clicked.connect(self.controller.lire_batterie)
		self.btn_battery.setEnabled(False)

		manual_controls_layout.addWidget(self.btn_walk, 0, 1)
		manual_controls_layout.addWidget(self.btn_left, 1, 0)
		manual_controls_layout.addWidget(self.btn_test, 1, 1)
		manual_controls_layout.addWidget(self.btn_right, 1, 2)
		manual_controls_layout.addWidget(self.btn_backward, 2, 1)
		manual_controls_layout.addWidget(QLabel("Source capteur:"), 3, 0)
		manual_controls_layout.addWidget(self.sensor_source_combo, 3, 1, 1, 2)
		manual_controls_layout.addWidget(self.btn_rgb, 4, 0, 1, 3)
		manual_controls_layout.addWidget(self.btn_battery, 5, 0, 1, 3)
		manual_controls_group.setLayout(manual_controls_layout)

		arms_group = QGroupBox("Contrôles Bras & Yeux")
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

		self.btn_yeux_faches = QPushButton("Yeux Fâchés")
		self.btn_yeux_faches.clicked.connect(lambda checked: self.controller.bouger_yeux("angry"))
		self.btn_yeux_faches.setEnabled(False)

		self.btn_yeux_surpris = QPushButton("Yeux Surpris")
		self.btn_yeux_surpris.clicked.connect(lambda checked: self.controller.bouger_yeux("excited"))
		self.btn_yeux_surpris.setEnabled(False)

		self.btn_yeux_wiggle = QPushButton("Wiggle (Yeux)")
		self.btn_yeux_wiggle.clicked.connect(lambda checked: self.controller.bouger_yeux("wiggle"))
		self.btn_yeux_wiggle.setEnabled(False)

		arms_layout.addWidget(self.btn_bras_gauche_up, 0, 0)
		arms_layout.addWidget(self.btn_bras_gauche_down, 0, 1)
		arms_layout.addWidget(self.btn_bras_droit_up, 1, 0)
		arms_layout.addWidget(self.btn_bras_droit_down, 1, 1)
		arms_layout.addWidget(self.btn_yeux_faches, 2, 0)
		arms_layout.addWidget(self.btn_yeux_surpris, 2, 1)
		arms_layout.addWidget(self.btn_yeux_wiggle, 3, 0, 1, 2)
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
		self.btn_calibration_dialog = QPushButton("Calibrer les 6 couleurs…")
		self.btn_calibration_dialog.clicked.connect(self.ouvrir_calibration)
		self.btn_calibration_dialog.setEnabled(False)
		calibration_layout.addWidget(self.btn_calibration_dialog)
		calibration_group.setLayout(calibration_layout)

		dance_group = QGroupBox("Chorégraphie")
		dance_layout = QVBoxLayout()
		self.btn_load_dance = QPushButton("Charger .dance")
		self.btn_load_dance.clicked.connect(self.load_dance_file)
		self.btn_load_dance.setEnabled(False)
		self.btn_play_dance = QPushButton("Jouer la séquence")
		self.btn_play_dance.clicked.connect(self.play_dance)
		self.btn_play_dance.setEnabled(False)
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		dance_layout.addWidget(self.btn_load_dance)
		dance_layout.addWidget(self.btn_play_dance)
		dance_layout.addWidget(self.progress_bar)
		dance_group.setLayout(dance_layout)

		left_panel_layout.addWidget(connection_group)
		left_panel_layout.addWidget(telemetry_group)
		left_panel_layout.addWidget(manual_controls_group)
		left_panel_layout.addWidget(arms_group)
		left_panel_layout.addWidget(calibration_group)
		left_panel_layout.addWidget(dance_group)
		left_panel_layout.addStretch()

		right_panel_layout = QVBoxLayout()
		self.log_console = QTextEdit()
		self.log_console.setReadOnly(True)
		right_panel_layout.addWidget(QLabel("Logs d'activité :"))
		right_panel_layout.addWidget(self.log_console)

		main_layout.addLayout(left_panel_layout, 1)
		main_layout.addLayout(right_panel_layout, 2)

		self.setCentralWidget(main_widget)

	def on_method_changed(self, text):
		if text == "mock":
			self.address_input.setText("mock")
		elif text == "wifi":
			self.address_input.setText("192.168.0.100")
		elif text == "usb":
			self.address_input.setText("/dev/ttyUSB0")

	def connect_marty(self):
		self.controller.method = self.method_combo.currentText()
		self.controller.address = self.address_input.text()
		self.status_label.setText("Connexion en cours...")
		QApplication.processEvents()
		self.controller.connect()

	def on_connection_status_changed(self, connected: bool):
		if connected:
			self.status_label.setText(f"Statut : Connecté ({self.controller.method} - {self.controller.address}) !")
			buttons = [
				self.btn_walk, self.btn_left, self.btn_test, self.btn_right, self.btn_backward, self.btn_rgb, self.btn_calibrate, self.btn_calibration_dialog, self.btn_battery,
				self.sensor_source_combo,
				self.btn_bras_gauche_up, self.btn_bras_gauche_down, self.btn_bras_droit_up, self.btn_bras_droit_down,
				self.btn_yeux_faches, self.btn_yeux_surpris, self.btn_yeux_wiggle,
				self.btn_load_dance, self.btn_play_dance
			]
			for btn in buttons:
				btn.setEnabled(True)
			self.btn_connect.setEnabled(False)
		else:
			self.status_label.setText("Statut : Échec de la connexion.")
			self.btn_connect.setEnabled(True)

	def load_dance_file(self):
		fileName, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier de chorégraphie", "", "Dance Files (*.dance);;All Files (*)")
		if fileName:
			self.current_sequence = self.parser.parse(fileName)
			self.update_log(f"Chargé : {os.path.basename(fileName)} ({len(self.current_sequence)} commandes)")
			self.btn_play_dance.setEnabled(len(self.current_sequence) > 0 and self.controller.connected)
			self.progress_bar.setValue(0)

	def play_dance(self):
		if not self.current_sequence:
			self.update_log("Aucune chorégraphie chargée.")
			return
		self.btn_play_dance.setEnabled(False)
		# Le player gère maintenant l'envoi des mouvements à l'api_client étape par étape
		self.player.play(self.current_sequence)
		self.btn_play_dance.setEnabled(True)
		self.update_log("Lecture chorégraphie terminée.")

	def update_dance_progress(self, current, total):
		percent = int((current / total) * 100) if total > 0 else 0
		self.progress_bar.setValue(percent)

	def update_battery_ui(self, value: float):
		self.battery_bar.setValue(int(value))
		self.battery_label.setText(f"Batterie : {value:.1f}%")

	def update_color_ui(self, color: str):
		self.color_label.setText(f"Couleur détectée : {color}")

	def update_score_ui(self, score: int):
		self.score_label.setText(f"Score : {score}")

	def lire_capteur_rgb(self):
		source = self.sensor_source_combo.currentText()
		if source == "Pied droit":
			rgb = self.controller.lire_rgb(source="foot", foot="right")
		elif source == "Capteur couleur":
			rgb = self.controller.lire_rgb(source="color")
		else:
			rgb = self.controller.lire_rgb(source="foot", foot="left")
		if rgb:
			r, g, b = rgb
			color = self.color_sensor.identifier(r, g, b)
			self.controller.signals.color_detected.emit(color)

	def calibrer_couleur(self):
		self.controller.calibrer_couleur(self.color_combo.currentText(), self.color_sensor)

	def ouvrir_calibration(self):
		CalibrationDialog(self.controller, self.color_sensor, self).exec_()

if __name__ == "__main__":
	app = QApplication(sys.argv)
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
