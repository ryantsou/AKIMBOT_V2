import sys
import signal
import json
import math
import os, requests
import time
from urllib.parse import urlparse, urlunparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit, QGridLayout, QComboBox, QLineEdit, QFileDialog, QProgressBar, QDialog, QScrollArea, QFrame)
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
import martypy

CALIBRATION_FILE = "calibration_couleurs.json"

APP_STYLESHEET = """
QTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    background-color: #ffffff;
    color: #000000;
}
"""

class ColorSensor:
	DEFAULT_COLORS = {
		"red":    [255,   0,   0],
		"green":  [  0, 255,   0],
		"blue":   [  0,   0, 255],
		"cyan":   [  0, 255, 255],
		"yellow": [255, 255,   0],
		"white":  [250, 250, 250],
		"black":  [ 10,  10,  10],
	}

	def __init__(self):
		self.calibration = self._load()

	def _load(self) -> dict:
		merged = dict(self.DEFAULT_COLORS)
		if os.path.exists(CALIBRATION_FILE):
			with open(CALIBRATION_FILE, "r") as f:
				merged.update(json.load(f))
		return merged

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
	color_detected = pyqtSignal(str, int, int, int)
	movements_verified = pyqtSignal(int, int, bool)

class MockMarty:
	def __init__(self, signals: ControllerSignals):
		self.signals = signals

	def celebrate(self):
		self.signals.log_message.emit("[MOCK] celebrate()")

	def walk(self, num_steps=2, turn=0, **kwargs):
		self.signals.log_message.emit(f"[MOCK] walk(num_steps={num_steps}, turn={turn})")

	def arms(self, left_angle, right_angle, move_time=1000, **kwargs):
		self.signals.log_message.emit(f"[MOCK] arms(left={left_angle}°, right={right_angle}°)")

	def eyes(self, pose_or_angle, **kwargs):
		self.signals.log_message.emit(f"[MOCK] eyes({pose_or_angle})")

	def set_color(self, r: int, g: int, b: int):
		self.signals.log_message.emit(f"[MOCK] set_color(r={r}, g={g}, b={b})")

	def get_color_sensor_value_by_channel(self, add_on_or_side: str, channel: str) -> int:
		mock_channels = {
			"left":  {"clear": 235, "red": 180, "green": 30, "blue": 25},
			"right": {"clear": 235, "red": 30, "green": 180, "blue": 25},
		}
		side = add_on_or_side.lower() if isinstance(add_on_or_side, str) else "left"
		return mock_channels.get(side, mock_channels["left"]).get(str(channel).lower(), 0)

	def get_ground_sensor_reading(self, foot: str) -> tuple:
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
		self.api_client = None

		self.arm_left = ""
		self.arm_right = ""
		self.exp = "XNT"
		self.current_color = "unknown"
		self.is_busy = False

	def _set_color(self, r: int, g: int, b: int):
		if not self.connected or not self.marty:
			return
		try:
			if hasattr(self.marty, "disco_color"):
				self.marty.disco_color((r, g, b))
			elif hasattr(self.marty, "set_color"):
				self.marty.set_color(r, g, b)
		except Exception: pass

	def reset_to_neutral(self):
		self.arm_left = ""
		self.arm_right = ""
		self.exp = "XNT"
		self.current_color = "N"
		if not self.connected or not self.marty: return
		try:
			self.marty.arms(0, 0, 500)
			self.marty.eyes("normal")
			self._set_color(0, 0, 0)
		except: pass

	def apply_act_state(self, actions: list):
		if not self.connected or not self.marty: return
		left_angle = 0
		right_angle = 0
		for act in actions:
			if act == "ALU": self.arm_left = "ALU"; left_angle = 100
			elif act == "ALB": self.arm_left = "ALB"; left_angle = -100
			elif act == "ARU": self.arm_right = "ARU"; right_angle = 100
			elif act == "ARB": self.arm_right = "ARB"; right_angle = -100
			elif act in ["XNT", "XSD", "XNG", "XHP", "XDN"]:
				self.exp = act
		try:
			self.marty.arms(left_angle, right_angle, 500)
			if self.exp == "XNT":
				self.marty.eyes("normal")
				self._set_color(0, 0, 0)
			elif self.exp == "XSD":
				self.marty.eyes("normal")
				self._set_color(0, 0, 255) # Bleu triste
			elif self.exp == "XNG":
				self.marty.eyes("angry")
				self._set_color(255, 0, 0) # Rouge colère
			elif self.exp == "XHP":
				self.marty.eyes("excited")
				self._set_color(0, 255, 0) # Vert content
			elif self.exp == "XDN":
				self.marty.eyes("wiggle")
				self._set_color(200, 0, 200) # Violet wiggle
		except Exception as e:
			self.signals.log_message.emit(f"Erreur posture ACT : {e}")

	def _envoyer(self, action_type: str, color: str = "unknown"):
		if self.api_client:
			c = color if color != "unknown" else self.current_color
			if len(c) == 1 and c.isupper():
				col_code = c
			else:
				col_map = {"black": "N", "blue": "B", "red": "R", "purple": "P", "yellow": "Y", "green": "G", "white": "C", "cyan": "C"}
				col_code = col_map.get(c.lower(), "N")

			arms = []
			if self.arm_left: arms.append(self.arm_left)
			if self.arm_right: arms.append(self.arm_right)
			arm_code = "+".join(arms)

			self.api_client.step(col_code, arm_code, self.exp)

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

	def disconnect(self):
		if not self.connected:
			return
		self.signals.log_message.emit("Déconnexion de Marty...")
		if self.api_client:
			self.api_client.bye()
		if self.marty:
			try:
				if hasattr(self.marty, 'close'):
					self.marty.close()
			except Exception as e:
				self.signals.log_message.emit(f"Erreur lors de la déconnexion : {e}")
			self.marty = None
		self.connected = False
		self.signals.connection_status.emit(False)

	def _action(self, message: str, mouvement, action_type: str, echec: str):
		if not (self.connected and self.marty):
			self.signals.log_message.emit(echec)
			return
		if self.is_busy:
			self.signals.log_message.emit("⏳ Marty est déjà occupé, commande ignorée.")
			return
		
		self.is_busy = True
		try:
			self.signals.log_message.emit(message)
			mouvement()
			self._envoyer(action_type)
		finally:
			self.is_busy = False

	def test_mouvement(self):
		self._action("Test basique : Marty célèbre !", lambda: self.marty.celebrate(), "celebrate", "Marty n'est pas connecté. Impossible de tester le mouvement.")

	def avancer(self):
		self._action("Action : Marty avance de 4 pas !", lambda: self.marty.walk(num_steps=4, turn=0), "walk", "Marty n'est pas connecté. Impossible d'avancer.")

	def reculer(self):
		self._action("Action : Marty recule de 4 pas !", lambda: self.marty.walk(num_steps=4, step_length=-25, turn=0), "walk", "Marty n'est pas connecté. Impossible de reculer.")

	def tourner_gauche(self):
		self._action("Action : Marty tourne à gauche !", lambda: self.marty.walk(num_steps=2, turn=25, step_length=0), "turn", "Marty n'est pas connecté. Impossible de tourner.")

	def tourner_droite(self):
		self._action("Action : Marty tourne à droite !", lambda: self.marty.walk(num_steps=2, turn=-25, step_length=0), "turn", "Marty n'est pas connecté. Impossible de tourner.")

	def lever_bras_gauche(self):
		self.arm_left = "ALU"
		self._action("Action : Marty lève le bras gauche !", lambda: self.marty.arms(100, 0, 1000), "arms", "Marty n'est pas connecté. Impossible de bouger les bras.")

	def baisser_bras_gauche(self):
		self.arm_left = ""
		self._action("Action : Marty baisse le bras gauche !", lambda: self.marty.arms(0, 0, 1000), "arms", "Marty n'est pas connecté. Impossible de bouger les bras.")

	def lever_bras_droit(self):
		self.arm_right = "ARU"
		self._action("Action : Marty lève le bras droit !", lambda: self.marty.arms(0, 100, 1000), "arms", "Marty n'est pas connecté. Impossible de bouger les bras.")

	def baisser_bras_droit(self):
		self.arm_right = ""
		self._action("Action : Marty baisse le bras droit !", lambda: self.marty.arms(0, 0, 1000), "arms", "Marty n'est pas connecté. Impossible de bouger les bras.")

	def bouger_yeux(self, expression: str):
		if expression == "angry": self.exp = "XNG"
		elif expression == "excited": self.exp = "XDN"
		elif expression == "wiggle": self.exp = "XDN"
		else: self.exp = "XNT"
		self._action(f"Action : Marty change ses yeux ({expression}) !", lambda: self.marty.eyes(expression), "eyes", "Marty n'est pas connecté. Impossible de bouger les yeux.")

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

	def lire_rgb(self, source: str = "foot", foot: str = "left", verbose: bool = True) -> tuple:
		if not self.connected or not self.marty:
			self.signals.log_message.emit("Marty non connecté. Impossible de lire le capteur couleur.")
			return None
		if not hasattr(self.marty, "get_color_sensor_value_by_channel"):
			self.signals.log_message.emit("Aucun capteur couleur compatible trouvé sur Marty.")
			return None
		side = "right" if source != "color" and foot.lower() == "right" else "left"
		try:
			r = int(self.marty.get_color_sensor_value_by_channel(side, "red"))
			g = int(self.marty.get_color_sensor_value_by_channel(side, "green"))
			b = int(self.marty.get_color_sensor_value_by_channel(side, "blue"))
			if verbose:
				self.signals.log_message.emit(f"Capteur couleur ({side}) brut — R:{r}  G:{g}  B:{b}")
			return (r, g, b)
		except Exception as e:
			self.signals.log_message.emit(f"Erreur lecture capteur couleur : {e}")
			return None

	def calibrer_couleur(self, couleur: str, color_sensor: ColorSensor):
		self.signals.log_message.emit(f"Calibration en cours pour '{couleur}'... (5 mesures)")
		prises = 0
		r_sum, g_sum, b_sum = 0, 0, 0
		for _ in range(5):
			rgb = self.lire_rgb(source="color", verbose=False) or self.lire_rgb(source="foot", foot="left", verbose=False) or self.lire_rgb(source="foot", foot="right", verbose=False)
			if rgb:
				r_sum += rgb[0]
				g_sum += rgb[1]
				b_sum += rgb[2]
				prises += 1
			time.sleep(0.2)
			QApplication.processEvents()
		
		if prises > 0:
			r_avg = int(r_sum / prises)
			g_avg = int(g_sum / prises)
			b_avg = int(b_sum / prises)
			color_sensor.calibrer(couleur, r_avg, g_avg, b_avg)
			self.signals.log_message.emit(f"Calibration '{couleur}' terminée — RGB:({r_avg}, {g_avg}, {b_avg})")
		else:
			self.signals.log_message.emit(f"Erreur : Capteur injoignable pour '{couleur}'.")

	def emotion_celebrer(self):
		self.exp = "XHP"
		self._action("Émotion : Célébration (LED or) !", lambda: (self._set_color(255, 215, 0), self.marty.celebrate()), "celebrate", "Marty non connecté.")

	def emotion_bras_ouverts(self):
		self.arm_left = "ALU"
		self.arm_right = "ARU"
		self.exp = "XSD"
		self._action("Émotion : Bras ouverts (LED bleu) !", lambda: (self._set_color(0, 0, 255), self.marty.arms(left_angle=100, right_angle=-100)), "arms", "Marty non connecté.")

	def emotion_yeux_wiggle(self):
		self.exp = "XDN"
		self._action("Émotion : Yeux wiggle (LED violet) !", lambda: (self._set_color(200, 0, 200), self.marty.eyes("wiggle")), "eyes", "Marty non connecté.")

class DanceParser:
	_CMDS = {"U", "D", "B", "L", "R", "T"}
	_COLOR_MAP = {
		'n': 'N',
		'b': 'B',
		'r': 'R',
		'p': 'P',  
		'y': 'Y',
		'g': 'G',
		'c': 'C',   
	}

	def parse(self, filepath: str) -> tuple:
		steps = []
		act_mapping = {}
		current_section = None
		try:
			with open(filepath, "r", encoding="utf-8") as f:
				for line in f:
					line = line.strip()
					if not line or line.startswith("#") or line.startswith("//"):
						continue

					upper_line = line.upper()
					if upper_line.startswith("SEQ"):
						current_section = "SEQUENCE"
						continue
					elif upper_line == "ACT":
						current_section = "ACT"
						continue

					if current_section == "ACT":
						parts = line.split()
						if len(parts) >= 2:
							color_code = parts[0].strip().lower()
							actions = [a.strip().upper() for a in parts[1:]]
							official_color = self._COLOR_MAP.get(color_code, color_code.upper())
							act_mapping[official_color] = actions
					elif current_section == "SEQUENCE":
						if len(line) > 1:
							cmd = line[-1].upper()
							n_str = line[:-1]
							try:
								n = int(n_str)
								if cmd in self._CMDS:
									steps.append((cmd, n))
							except ValueError:
								continue
		except Exception as e:
			print(f"Erreur lecture .dance: {e}")
		return steps, act_mapping

class ChoreographyPlayer:
	_ACTIONS = {
		"U": lambda m, n: m.walk(num_steps=n, turn=0),
		"D": lambda m, n: m.walk(num_steps=n, step_length=-25, turn=0),
		"B": lambda m, n: m.walk(num_steps=n, step_length=-25, turn=0),
		"L": lambda m, n: m.walk(num_steps=n, turn=25, step_length=0),
		"R": lambda m, n: m.walk(num_steps=n, turn=-25, step_length=0),
		"T": lambda m, n: m.walk(num_steps=n, turn=100, step_length=0),
	}

	def __init__(self, controller: MartyController, api_client: 'ArbitreAPIClient'):
		self.controller = controller
		self.api_client = api_client

	def play(self, steps: list, act_mapping: dict, color_sensor: ColorSensor):
		if self.controller.is_busy:
			self.controller.signals.log_message.emit("⏳ Marty danse déjà, impossible de lancer une autre action !")
			return 0
			
		self.controller.is_busy = True
		try:
			total = len(steps)
			executed = 0
			self.controller.signals.log_message.emit(f"Chorégraphie : {total} étapes.")
			self.api_client.start()
			
			color_name_to_code = {"black": "N", "blue": "B", "red": "R", "purple": "P", "yellow": "Y", "green": "G", "cyan": "C", "white": "C", "unknown": "N"}
	
			for idx, (cmd, n) in enumerate(steps, start=1):
				self.controller.signals.log_message.emit(f"[{idx}/{total}] {cmd}={n}")
				if self.controller.marty and cmd in self._ACTIONS:
					
					self.controller.reset_to_neutral()
					
					rgb = self.controller.lire_rgb(source="color", verbose=False)
					if not rgb:
						rgb = self.controller.lire_rgb(source="foot", foot="left", verbose=False)
					
					detected_code = "N"
					if rgb:
						color_name = color_sensor.identifier(*rgb)
						detected_code = color_name_to_code.get(color_name, "N")
					
					self.controller.current_color = detected_code
					actions = act_mapping.get(detected_code, [])
					if actions:
						self.controller.signals.log_message.emit(f"Couleur {detected_code} détectée -> Posture : {actions}")
						self.controller.apply_act_state(actions)
					
					QApplication.processEvents()
					time.sleep(0.5) 
					
					self.controller._envoyer(cmd, color=detected_code)
					
					self._ACTIONS[cmd](self.controller.marty, n)
					executed += 1
					
					self.controller.reset_to_neutral()
				else:
					self.controller.signals.log_message.emit(f"Mouvement ignoré (commande invalide ou robot absent) : {cmd}")
				time.sleep(0.5)
				self.controller.signals.dance_progress.emit(idx, total)
				QApplication.processEvents()
	
			ok = executed == total
			if ok:
				self.controller.signals.log_message.emit(f"Vérification : {executed}/{total} mouvements exécutés (conforme).")
			else:
				self.controller.signals.log_message.emit(f"Vérification : {executed}/{total} mouvements exécutés (écart de {total - executed}).")
			self.controller.signals.movements_verified.emit(executed, total, ok)
			return executed
		finally:
			self.controller.is_busy = False

class ArbitreAPIClient:
	def __init__(self, signals: ControllerSignals, base_url="http://localhost:8000"):
		self.base_url = base_url
		self.signals = signals
		self.rid = None

	def test_connection(self):
		if not self.base_url:
			self.signals.log_message.emit("[API] Adresse vide.")
			return False
		self.signals.log_message.emit(f"[API] Test de connexion à {self.base_url}...")
		try:
			response = requests.get(self.base_url, timeout=3)
			response.raise_for_status()
			data = response.json()
			v = data.get("version", "?")
			self.signals.log_message.emit(f"[API] Serveur arbitre dispo (version {v})")
			return True
		except Exception as e:
			self.signals.log_message.emit(f"[API] Erreur connexion arbitre : {e}")
			return False

	def hello(self):
		if not self.base_url: return
		try:
			r = requests.post(f"{self.base_url}/hello", timeout=3)
			r.raise_for_status()
			self.rid = r.json().get("rid", "")
			self.signals.log_message.emit(f"[API] Robot enregistré (rid: {self.rid})")
		except Exception as e:
			self.signals.log_message.emit(f"[API] Erreur /hello : {e}")

	def start(self):
		if not self.base_url or not self.rid: return
		try:
			r = requests.post(f"{self.base_url}/start", json={"rid": self.rid}, timeout=3)
			r.raise_for_status()
			steps = r.json().get("steps", 0)
			self.signals.log_message.emit(f"[API] Chorégraphie démarrée. Pas attendus : {steps}")
		except Exception as e:
			self.signals.log_message.emit(f"[API] Erreur /start : {e}")

	def step(self, col: str, arm: str, exp: str):
		if not self.base_url or not self.rid: return
		try:
			payload = {"rid": self.rid, "col": col, "arm": arm, "exp": exp}
			r = requests.post(f"{self.base_url}/step", json=payload, timeout=3)
			r.raise_for_status()
			self.get_score()
		except Exception as e:
			self.signals.log_message.emit(f"[API] Erreur /step : {e}")

	def get_score(self):
		if not self.base_url or not self.rid: return
		try:
			r = requests.get(f"{self.base_url}/score", json={"rid": self.rid}, timeout=3)
			r.raise_for_status()
			pts = r.json().get("points", 0)
			self.signals.score_updated.emit(pts)
		except Exception as e:
			pass

	def bye(self):
		if not self.base_url or not self.rid: return
		try:
			requests.post(f"{self.base_url}/bye", json={"rid": self.rid}, timeout=3)
			self.rid = None
			self.signals.log_message.emit("[API] Déconnecté de l'arbitre.")
		except Exception as e:
			pass

class CalibrationDialog(QDialog):
	COLORS = [
		("ROUGE",      "red"),
		("VERT",       "green"),
		("BLEU",       "blue"),
		("BLEU CLAIR", "cyan"),
		("JAUNE",      "yellow"),
		("NOIR",       "black"),
		("BLANC",      "white"),
	]

	def __init__(self, controller: MartyController, color_sensor: ColorSensor, parent=None):
		super().__init__(parent)
		self.controller = controller
		self.color_sensor = color_sensor
		self.rgb_data = {}
		for _, key in self.COLORS:
			self.rgb_data[key] = color_sensor.calibration.get(key, [0, 0, 0])

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
		self.controller.calibrer_couleur(key, self.color_sensor)
		rgb = self.color_sensor.calibration.get(key, [0, 0, 0])
		r, g, b = rgb
		self.rgb_data[key] = list(rgb)
		lbl_r, lbl_g, lbl_b = self._rgb_labels[key]
		lbl_r.setText(str(r))
		lbl_g.setText(str(g))
		lbl_b.setText(str(b))

	def _sauvegarder(self):
		self.color_sensor._save()
		self._status_label.setText("Calibration des couleurs sauvegardée.")


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("AKIMBOT - Superviseur Robot")
		self.resize(1050, 700)
		self.setMinimumSize(850, 550)
        
		self.controller = MartyController(address="192.168.0.100")
		self.parser = DanceParser()
		self.color_sensor = ColorSensor()
		self.is_processing_act = False
		self.current_sequence = []
		self.act_mapping = {}
		
		self.act_timer = QTimer()
		self.act_timer.timeout.connect(self.process_act_loop)

		self.controller.signals.log_message.connect(self.update_log)
		self.controller.signals.connection_status.connect(self.on_connection_status_changed)
		self.controller.signals.dance_progress.connect(self.update_dance_progress)
		self.controller.signals.battery_updated.connect(self.update_battery_ui)
		self.controller.signals.score_updated.connect(self.update_score_ui)
		self.controller.signals.color_detected.connect(self.update_color_ui)
		self.controller.signals.movements_verified.connect(self.update_movements_verified_ui)

		self._init_ui()


		self.api_client = ArbitreAPIClient(self.controller.signals)
		self.controller.api_client = self.api_client
		self.player = ChoreographyPlayer(self.controller, self.api_client)
		self.arbiter_address_input.textChanged.connect(self.on_arbiter_address_changed)
		self.btn_test_arbiter.clicked.connect(self.test_arbiter_connection)

		self.on_arbiter_address_changed(self.arbiter_address_input.text())

	def _init_ui(self):
		main_widget = QWidget()
		main_layout = QHBoxLayout(main_widget)
		main_layout.setContentsMargins(12, 12, 12, 12)
		main_layout.setSpacing(12)

		left_panel_layout = QVBoxLayout()
		self._create_connection_group(left_panel_layout)
		self._create_telemetry_group(left_panel_layout)
		self._create_manual_controls_group(left_panel_layout)
		self._create_arms_group(left_panel_layout)
		self._create_emotions_group(left_panel_layout)
		self._create_calibration_group(left_panel_layout)
		self._create_dance_group(left_panel_layout)
		left_panel_layout.addStretch()

		right_panel_layout = QVBoxLayout()
		self._init_right_panel_content(right_panel_layout)

		left_panel_container = QWidget()
		left_panel_container.setLayout(left_panel_layout)
		left_scroll = QScrollArea()
		left_scroll.setWidgetResizable(True)
		left_scroll.setFrameShape(QFrame.NoFrame)
		left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		left_scroll.setWidget(left_panel_container)
		left_scroll.setMinimumWidth(370)
		left_scroll.setMaximumWidth(450)

		right_panel_container = QWidget()
		right_panel_container.setLayout(right_panel_layout)

		main_layout.addWidget(left_scroll)
		main_layout.addWidget(right_panel_container, 1)

		self.setCentralWidget(main_widget)

	def _create_connection_group(self, parent_layout: QVBoxLayout):
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

		arbiter_layout = QHBoxLayout()
		self.arbiter_address_input = QLineEdit()
		self.arbiter_address_input.setText("localhost") # Saisie de l'IP seulement
		self.btn_test_arbiter = QPushButton("Tester")
		arbiter_layout.addWidget(self.arbiter_address_input)
		arbiter_layout.addWidget(self.btn_test_arbiter)
		connection_layout.addWidget(QLabel("Adresse du serveur arbitre :"))
		connection_layout.addLayout(arbiter_layout)

		self.status_label = QLabel("État : Déconnecté")
		self.status_label.setStyleSheet("color: darkred;")
		connection_layout.addWidget(self.status_label)
		self.btn_connect = QPushButton("Connecter")
		self.btn_connect.clicked.connect(self.toggle_connection)
		connection_layout.addWidget(self.btn_connect)
		connection_group.setLayout(connection_layout)
		parent_layout.addWidget(connection_group)

	def _create_telemetry_group(self, parent_layout: QVBoxLayout):
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
		parent_layout.addWidget(telemetry_group)

	def _create_manual_controls_group(self, parent_layout: QVBoxLayout):
		manual_controls_group = QGroupBox("Piloter Marty")
		manual_controls_layout = QGridLayout()
        
		self.btn_walk = QPushButton("Avancer")
		self.btn_walk.clicked.connect(self.controller.avancer)

		self.btn_left = QPushButton("Tourner Gauche")
		self.btn_left.clicked.connect(self.controller.tourner_gauche)

		self.btn_test = QPushButton("Tester")
		self.btn_test.clicked.connect(self.controller.test_mouvement)

		self.btn_right = QPushButton("Droite")
		self.btn_right.clicked.connect(self.controller.tourner_droite)

		self.btn_backward = QPushButton("Reculer")
		self.btn_backward.clicked.connect(self.controller.reculer)

		self.sensor_source_combo = QComboBox()
		self.sensor_source_combo.addItems(["Pied gauche", "Pied droit", "Capteur couleur"])
		self.sensor_source_combo.setEnabled(False)

		self.btn_rgb = QPushButton("Lire capteur couleur (RGB)")
		self.btn_rgb.clicked.connect(self.lire_capteur_rgb)

		self.btn_battery = QPushButton("Lire Batterie")
		self.btn_battery.clicked.connect(self.controller.lire_batterie)

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
		parent_layout.addWidget(manual_controls_group)

	def _create_arms_group(self, parent_layout: QVBoxLayout):
		arms_group = QGroupBox("Contrôles Bras & Yeux")
		arms_layout = QGridLayout()

		self.btn_bras_gauche_up = QPushButton("Lever Bras G.")
		self.btn_bras_gauche_up.clicked.connect(self.controller.lever_bras_gauche)

		self.btn_bras_gauche_down = QPushButton("Baisser Bras G.")
		self.btn_bras_gauche_down.clicked.connect(self.controller.baisser_bras_gauche)

		self.btn_bras_droit_up = QPushButton("Lever Bras D.")
		self.btn_bras_droit_up.clicked.connect(self.controller.lever_bras_droit)

		self.btn_bras_droit_down = QPushButton("Baisser Bras D.")
		self.btn_bras_droit_down.clicked.connect(self.controller.baisser_bras_droit)

		line = QFrame()
		line.setFrameShape(QFrame.HLine)

		self.btn_yeux_faches = QPushButton("Fâché")
		self.btn_yeux_faches.clicked.connect(lambda checked: self.controller.bouger_yeux("angry"))

		self.btn_yeux_surpris = QPushButton("Surpris")
		self.btn_yeux_surpris.clicked.connect(lambda checked: self.controller.bouger_yeux("excited"))

		self.btn_yeux_wiggle = QPushButton("Wiggle")
		self.btn_yeux_wiggle.clicked.connect(lambda checked: self.controller.bouger_yeux("wiggle"))

		arms_layout.addWidget(self.btn_bras_gauche_up, 0, 0)
		arms_layout.addWidget(self.btn_bras_gauche_down, 1, 0)
		arms_layout.addWidget(self.btn_bras_droit_up, 0, 1)
		arms_layout.addWidget(self.btn_bras_droit_down, 1, 1)
		
		arms_layout.addWidget(line, 2, 0, 1, 2)
		
		arms_layout.addWidget(self.btn_yeux_faches, 3, 0)
		arms_layout.addWidget(self.btn_yeux_surpris, 3, 1)
		arms_layout.addWidget(self.btn_yeux_wiggle, 4, 0, 1, 2)
		
		arms_group.setLayout(arms_layout)
		parent_layout.addWidget(arms_group)

	def _create_emotions_group(self, parent_layout: QVBoxLayout):
		emotions_group = QGroupBox("Macros")
		emotions_layout = QVBoxLayout()
		emotions_layout.setSpacing(4)

		self.btn_emotion_celebrer = QPushButton("Célébration")
		self.btn_emotion_celebrer.clicked.connect(self.controller.emotion_celebrer)

		self.btn_emotion_bras = QPushButton("Bras ouverts")
		self.btn_emotion_bras.clicked.connect(self.controller.emotion_bras_ouverts)

		self.btn_emotion_wiggle = QPushButton("Yeux Wiggle")
		self.btn_emotion_wiggle.clicked.connect(self.controller.emotion_yeux_wiggle)

		emotions_layout.addWidget(self.btn_emotion_celebrer)
		emotions_layout.addWidget(self.btn_emotion_bras)
		emotions_layout.addWidget(self.btn_emotion_wiggle)
		emotions_group.setLayout(emotions_layout)
		parent_layout.addWidget(emotions_group)

	def _create_calibration_group(self, parent_layout: QVBoxLayout):
		calibration_group = QGroupBox("Étalonnage")
		calibration_layout = QHBoxLayout()
		self.color_combo = QComboBox()
		self.color_combo.addItems(["red", "green", "blue", "cyan", "yellow", "white", "black"])
		self.btn_calibrate = QPushButton("Calibrer")
		self.btn_calibrate.clicked.connect(self.calibrer_couleur)
		self.btn_calibration_dialog = QPushButton("Étalonnage étendu")
		self.btn_calibration_dialog.clicked.connect(self.ouvrir_calibration)
		
		v_layout = QVBoxLayout()
		h_layout = QHBoxLayout()
		h_layout.addWidget(self.color_combo, 1)
		h_layout.addWidget(self.btn_calibrate)
		v_layout.addLayout(h_layout)
		v_layout.addWidget(self.btn_calibration_dialog)
		
		calibration_group.setLayout(v_layout)
		parent_layout.addWidget(calibration_group)

	def _create_dance_group(self, parent_layout: QVBoxLayout):
		dance_group = QGroupBox("Séquenceur Automatique")
		dance_layout = QVBoxLayout()
		dance_layout.setSpacing(6)
		
		file_layout = QHBoxLayout()
		self.btn_load_dance = QPushButton("Importer .dance")
		self.btn_load_dance.clicked.connect(self.load_dance_file)
		
		self.dance_info_label = QLabel("Aucun fichier")
		file_layout.addWidget(self.btn_load_dance)
		file_layout.addWidget(self.dance_info_label, 1)
		dance_layout.addLayout(file_layout)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.progress_bar.setTextVisible(False)
		
		self.movements_check_label = QLabel("Mouvements : 0/0")

		dance_layout.addWidget(self.progress_bar)
		dance_layout.addWidget(self.movements_check_label)
		
		action_layout = QHBoxLayout()
		self.btn_play_dance = QPushButton("Exécuter Séquence")
		self.btn_play_dance.clicked.connect(self.play_dance)
		
		self.btn_toggle_act = QPushButton("Mode ACT")
		self.btn_toggle_act.clicked.connect(self.toggle_act_mode)
		self.btn_toggle_act.setEnabled(False)
		
		action_layout.addWidget(self.btn_play_dance)
		action_layout.addWidget(self.btn_toggle_act)
		dance_layout.addLayout(action_layout)

		dance_group.setLayout(dance_layout)
		parent_layout.addWidget(dance_group)

	def _init_right_panel_content(self, layout: QVBoxLayout):
		header_layout = QHBoxLayout()
		logs_title = QLabel("I/O Réseau et Système")
		self.clear_logs_btn = QPushButton("Effacer")
		self.clear_logs_btn.clicked.connect(lambda: self.log_console.clear())
		
		header_layout.addWidget(logs_title)
		header_layout.addStretch()
		header_layout.addWidget(self.clear_logs_btn)
		
		self.log_console = QTextEdit()
		self.log_console.setReadOnly(True)
		
		layout.addLayout(header_layout)
		layout.addWidget(self.log_console)

	def update_log(self, message: str):
		self.log_console.append(message)

	def test_arbiter_connection(self):
		if hasattr(self, 'api_client') and self.api_client:
			if self.api_client.test_connection():
				self.api_client.hello()

	def on_arbiter_address_changed(self, new_address: str):
		if not (hasattr(self, "api_client") and self.api_client):
			return

		raw_addr = new_address.strip()
		if not raw_addr:
			self.api_client.base_url = ""
			return

		processed_url = raw_addr
		if not (processed_url.startswith("http://") or processed_url.startswith("https://")):
			processed_url = "http://" + processed_url

		parsed = urlparse(processed_url)
		if parsed.hostname and not parsed.port:
			processed_url = urlunparse(parsed._replace(netloc=f"{parsed.hostname}:8000"))

		if processed_url.endswith("/"):
			processed_url = processed_url[:-1]

		self.api_client.base_url = processed_url

	def on_method_changed(self, text):
		if text == "mock":
			self.address_input.setText("mock")
		elif text == "wifi":
			self.address_input.setText("192.168.0.100")
		elif text == "usb":
			self.address_input.setText("/dev/ttyUSB0")

	def toggle_connection(self):
		if self.controller.connected:
			self.controller.disconnect()
		else:
			self.controller.method = self.method_combo.currentText()
			self.controller.address = self.address_input.text()
			self.status_label.setText("État : Connexion en cours…")
			self.status_label.setStyleSheet("color: #e67e22;")
			QApplication.processEvents()
			self.controller.connect()

	def on_connection_status_changed(self, connected: bool):
		if connected:
			self.status_label.setText(f"État : Connecté ({self.controller.method})")
			self.status_label.setStyleSheet("color: darkgreen;")
			self.btn_connect.setText("Déconnecter")
			self._set_controls_enabled(True)
		else:
			self.status_label.setText("État : Déconnecté")
			self.status_label.setStyleSheet("color: darkred;")
			self.btn_connect.setText("Connecter")
			self._set_controls_enabled(False)

	def _set_controls_enabled(self, enabled: bool):
		
		controls = [
			self.btn_walk, self.btn_left, self.btn_test, self.btn_right, self.btn_backward, self.btn_rgb, self.btn_calibrate, self.btn_calibration_dialog, self.btn_battery,
			self.sensor_source_combo,
			self.btn_bras_gauche_up, self.btn_bras_gauche_down, self.btn_bras_droit_up, self.btn_bras_droit_down,
			self.btn_yeux_faches, self.btn_yeux_surpris, self.btn_yeux_wiggle,
			self.btn_emotion_celebrer, self.btn_emotion_bras, self.btn_emotion_wiggle,
			self.btn_load_dance, self.btn_play_dance
		]
		for control in controls:
			control.setEnabled(enabled)
		self.btn_toggle_act.setEnabled(enabled and len(self.act_mapping) > 0)

	def toggle_act_mode(self):
		if self.act_timer.isActive():
			self._stop_act_mode()
		else:
			self._start_act_mode()

	def _start_act_mode(self):
		if not self.act_mapping:
			self.update_log("Erreur : Aucune section [ACT] trouvée dans le fichier .dance chargé.")
			return
		self.act_timer.start(1000)
		self.btn_toggle_act.setText("Arrêter Mode ACT")
		self.update_log("Mode ACT démarré : surveillance du capteur couleur...")

	def _stop_act_mode(self):
		self.act_timer.stop()
		self.is_processing_act = False
		self.btn_toggle_act.setText("Mode ACT")
		self.update_log("Mode ACT arrêté.")

	def process_act_loop(self):
		"""Boucle ACT : Vérifie les capteurs sous les pieds"""
		if self.is_processing_act or not self.controller.connected or self.controller.is_busy:
			return

		self.is_processing_act = True
		sensors_to_check = [
			("foot", "left", "Pied Gauche"),
			("foot", "right", "Pied Droit"),
			("color", "", "Capteur Add-on")
		]
		
		color_name_to_code = {"black": "N", "blue": "B", "red": "R", "purple": "P", "yellow": "Y", "green": "G", "cyan": "C", "white": "C", "unknown": "N"}
		
		try:
			for source, foot, name in sensors_to_check:
				rgb = self.controller.lire_rgb(source=source, foot=foot, verbose=False)
				if rgb:
					color_name = self.color_sensor.identifier(*rgb)
					if color_name != "unknown":
						detected_code = color_name_to_code.get(color_name, "N")
						actions = self.act_mapping.get(detected_code)
						if actions:
							self.update_log(f"[ACT] {name} a vu {detected_code} -> Actions : {', '.join(actions)}")
							self.controller.current_color = detected_code
							self.controller.apply_act_state(actions)
							self.controller._envoyer("ACT_TEST", color=detected_code)
							QApplication.processEvents() 
							time.sleep(1.0) 
							self.controller.reset_to_neutral()
							return 
		finally:
			self.is_processing_act = False

	def load_dance_file(self):
		fileName, _ = QFileDialog.getOpenFileName(self, "Charger un fichier .dance", "", "Dance Files (*.dance);;All Files (*)")
		if not fileName:
			return
		self.current_sequence, self.act_mapping = self.parser.parse(fileName)
		n = len(self.current_sequence)
		self.dance_info_label.setText(f"{os.path.basename(fileName)} — {n} étape(s)")
		self.update_log(f"Chargé : {os.path.basename(fileName)} ({n} étapes, {len(self.act_mapping)} règles ACT)")
		self.btn_play_dance.setEnabled(n > 0 and self.controller.connected)
		self.btn_toggle_act.setEnabled(len(self.act_mapping) > 0 and self.controller.connected)
		self.progress_bar.setValue(0)
		self.movements_check_label.setText(f"Progression : 0/{n}")

	def play_dance(self):
		if not self.current_sequence:
			self.update_log("Aucune chorégraphie chargée.")
			return
		self.btn_play_dance.setEnabled(False)
		self.player.play(self.current_sequence, self.act_mapping, self.color_sensor)
		self.btn_play_dance.setEnabled(True)
		self.update_log("Lecture chorégraphie terminée.")

	def update_dance_progress(self, current, total):
		percent = int((current / total) * 100) if total > 0 else 0
		self.progress_bar.setValue(percent)

	def update_battery_ui(self, value: float):
		self.battery_bar.setValue(int(value))
		self.battery_label.setText(f"Batterie : {value:.1f}%")

	def update_color_ui(self, color: str, r: int = 0, g: int = 0, b: int = 0):
		self.color_label.setText(f"Couleur : {color.upper()} — RGB({r}, {g}, {b})")
		cr, cg, cb = (max(0, min(255, int(v))) for v in (r, g, b))
		texte = "#000000" if (cr * 299 + cg * 587 + cb * 114) / 1000 > 140 else "#ffffff"
		self.color_label.setStyleSheet(f"background-color: rgb({cr}, {cg}, {cb}); color: {texte}; border: 1px solid #aaa; padding: 2px;")

	def update_score_ui(self, score: int):
		self.score_label.setText(f"Score : {score}")

	def update_movements_verified_ui(self, executed: int, total: int, ok: bool):
		self.movements_check_label.setText(f"Progression : {executed}/{total}")
		if ok:
			self.movements_check_label.setStyleSheet("color: darkgreen; font-weight: bold;")
		else:
			self.movements_check_label.setStyleSheet("color: darkred; font-weight: bold;")

	def lire_capteur_rgb(self):
		source = self.sensor_source_combo.currentText()
		foot_param = "left" if source == "Pied gauche" else "right"
		source_param = "color" if source == "Capteur couleur" else "foot"
		
		rgb = self.controller.lire_rgb(source=source_param, foot=foot_param)
		if rgb:
			r, g, b = rgb
			color = self.color_sensor.identifier(r, g, b)
			self.controller.signals.color_detected.emit(color, int(r), int(g), int(b))

	def calibrer_couleur(self):
		self.controller.calibrer_couleur(self.color_combo.currentText(), self.color_sensor)

	def ouvrir_calibration(self):
		CalibrationDialog(self.controller, self.color_sensor, self).exec_()

if __name__ == "__main__":
	app = QApplication(sys.argv)
	app.setStyle("Fusion")
	app.setStyleSheet(APP_STYLESHEET)
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
