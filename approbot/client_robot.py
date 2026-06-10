import sys
import signal
import json
import math
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit, QGridLayout, QComboBox)
from PyQt5.QtCore import QObject, pyqtSignal
import martypy
# import requests

<<<<<<< Updated upstream
CALIBRATION_FILE = "calibration.json"
=======
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration_couleurs.json")
>>>>>>> Stashed changes

class ColorSensor:
	# Identifie les couleurs par distance euclidienne RGB avec valeurs calibrables
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
	# Définit les signaux émis par le contrôleur pour communiquer avec l'UI
	log_message = pyqtSignal(str)
	connection_status = pyqtSignal(bool)

class MockMarty:
	# Faux robot pour pouvoir tester l'interface sans le matériel
	def __init__(self, signals: ControllerSignals):
		self.signals = signals

	def celebrate(self):
		self.signals.log_message.emit("[MOCK] Marty fait une danse de célébration !")
        
	def walk(self, num_steps=2, turn=0, **kwargs):
		self.signals.log_message.emit(f"[MOCK] 🚶 Le faux robot marche : {num_steps} pas, rotation {turn}, options: {kwargs}")

	def get_color_sensor_value_by_channel(self, add_on_name: str, channel_index: int) -> int:
		mock_rgb = {0: 180, 1: 30, 2: 25}  # rouge simulé par défaut
		return mock_rgb.get(channel_index, 0)

class MartyController:
	# Gère la connexion et les commandes directes au robot Marty
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

<<<<<<< Updated upstream
=======
	def _parse_raw_rgb(self, raw) -> tuple:
		if isinstance(raw, (tuple, list)) and len(raw) == 3:
			return raw
		if isinstance(raw, dict):
			return (int(raw.get("r", 0)), int(raw.get("g", 0)), int(raw.get("b", 0)))
		val = int(raw)
		return (val, val, val)

>>>>>>> Stashed changes
	def calibrer_couleur(self, couleur: str, color_sensor: ColorSensor):
		rgb = self.lire_rgb()
		if rgb is None:
			return
		r, g, b = rgb
		color_sensor.calibrer(couleur, r, g, b)
		self.signals.log_message.emit(f"Calibration '{couleur}' enregistrée — R:{r}  G:{g}  B:{b}")

class DanceParser:
	# Décode les fichiers .dance pour extraire les séquences de mouvements
	def parse(self, filepath: str) -> list:
		# TODO: Lire le fichier et parser les instructions
		print(f"Lecture de la chorégraphie : {filepath}")
		return []

class ChoreographyPlayer:
	# Exécute une liste de mouvements sans bloquer l'interface principale
	def __init__(self, controller: MartyController):
		self.controller = controller

	def play(self, sequence: list):
		# TODO: Exécuter les commandes dans un QThread
		print(f"Lancement de la chorégraphie ({len(sequence)} mouvements)")

class ArbitreAPIClient:
	# Communique avec le serveur REST pour envoyer les actions et récupérer le score
	def __init__(self, base_url="http://localhost:8000"):
		self.base_url = base_url

	def send_movement(self, action_type: str, color: str = None):
		# TODO: Faire un POST via requests
		payload = {"action_type": action_type, "color_detected": color}
<<<<<<< Updated upstream
		print(f"Envoi de l'action à l'arbitre : {payload}")
=======
		self.signals.log_message.emit(f"[API] Envoi : {action_type} (Couleur: {color})")
		try:
			response = requests.post(f"{self.base_url}/api/mouvements?robot_id={robot_id}", json=payload, timeout=5)
			response.raise_for_status()
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

>>>>>>> Stashed changes

class MainWindow(QMainWindow):
	# Fenêtre principale de l'application PyQt
	def __init__(self):
		super().__init__()
		self.setWindowTitle("AKIMBOT - Client Robot")
		self.resize(900, 700)
        
		# Instanciation des sous-composants
		
		self.controller = MartyController(address="192.168.0.100")
		self.api_client = ArbitreAPIClient()
		self.parser = DanceParser()
		self.player = ChoreographyPlayer(self.controller)
		self.color_sensor = ColorSensor()
        
		# Lier les signaux du contrôleur aux slots de la fenêtre
		self.controller.signals.log_message.connect(self.update_log)
		self.controller.signals.connection_status.connect(self.on_connection_status_changed)

		self.init_ui()

	def init_ui(self):
		# Widget central et layout principal horizontal
		main_widget = QWidget()
		main_layout = QHBoxLayout(main_widget)

		# === Panneau de gauche : Contrôles ===
		left_panel_layout = QVBoxLayout()

		# Groupe Connexion
		connection_group = QGroupBox("Connexion")
		connection_layout = QVBoxLayout()
		self.status_label = QLabel("Statut : Déconnecté")
<<<<<<< Updated upstream
=======
		self.status_label.setStyleSheet("color: red;")
>>>>>>> Stashed changes
		connection_layout.addWidget(self.status_label)
		self.btn_connect = QPushButton("Connecter Marty")
		self.btn_connect.clicked.connect(self.connect_marty)
		connection_layout.addWidget(self.btn_connect)
		connection_group.setLayout(connection_layout)

		# Groupe Contrôles Manuels (Pad Directionnel)
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

		# Ajout des boutons directionnels à la grille
		manual_controls_layout.addWidget(self.btn_walk, 0, 1)
		manual_controls_layout.addWidget(self.btn_left, 1, 0)
		manual_controls_layout.addWidget(self.btn_test, 1, 1)
		manual_controls_layout.addWidget(self.btn_right, 1, 2)
		manual_controls_layout.addWidget(self.btn_backward, 2, 1)
		manual_controls_layout.addWidget(self.btn_rgb, 3, 0, 1, 3)
		manual_controls_group.setLayout(manual_controls_layout)

		# Groupe Calibration
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
		left_panel_layout.addWidget(calibration_group)
		left_panel_layout.addStretch()

<<<<<<< Updated upstream
		# === Panneau de droite : Logs ===
		right_panel_layout = QVBoxLayout()
=======
		self.btn_play_dance = QPushButton("Jouer la séquence")
		self.btn_play_dance.clicked.connect(self.play_dance)

		self.btn_toggle_act = QPushButton("Démarrer Mode Automatique (ACT)")
		self.btn_toggle_act.clicked.connect(self.toggle_act_mode)
		self.btn_toggle_act.setEnabled(False)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.movements_check_label = QLabel("Mouvements : -/-")
		
		dance_layout.addWidget(self.btn_load_dance)
		dance_layout.addWidget(self.dance_info_label)
		dance_layout.addWidget(self.btn_play_dance)
		dance_layout.addWidget(self.btn_toggle_act)
		dance_layout.addWidget(self.progress_bar)
		dance_layout.addWidget(self.movements_check_label)
		dance_group.setLayout(dance_layout)
		parent_layout.addWidget(dance_group)

	def _init_right_panel_content(self, layout: QVBoxLayout):
		logs_title = QLabel("Logs d'activité")
>>>>>>> Stashed changes
		self.log_console = QTextEdit()
		self.log_console.setReadOnly(True)
		right_panel_layout.addWidget(QLabel("Logs d'activité :"))
		right_panel_layout.addWidget(self.log_console)

		# Ajout des deux panneaux au layout principal
		main_layout.addLayout(left_panel_layout, 1)
		main_layout.addLayout(right_panel_layout, 2)

		self.setCentralWidget(main_widget)

	def connect_marty(self):
<<<<<<< Updated upstream
		self.status_label.setText("Connexion en cours...")
=======
		self.controller.method = self.method_combo.currentText()
		self.controller.address = self.address_input.text()
		self.status_label.setText("Statut : Connexion en cours…")
		self.status_label.setStyleSheet("color: blue;")
>>>>>>> Stashed changes
		QApplication.processEvents()
		self.controller.connect()

	def on_connection_status_changed(self, connected: bool):
		if connected:
			self.status_label.setText(f"Statut : Connecté ({self.controller.method} - {self.controller.address}) !")
<<<<<<< Updated upstream
			for btn in [self.btn_walk, self.btn_left, self.btn_test, self.btn_right, self.btn_backward, self.btn_rgb, self.btn_calibrate]:
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
	signal.signal(signal.SIGINT, signal.SIG_DFL)  # Permet de quitter avec Ctrl+C proprement
=======
			self.status_label.setStyleSheet("color: green;")
			self._set_controls_enabled(True)
		else:
			self.status_label.setText("Statut : Échec de la connexion.")
			self.status_label.setStyleSheet("color: red;")
			self._set_controls_enabled(False)

	def _set_controls_enabled(self, enabled: bool):
		controls = [
			self.btn_walk, self.btn_left, self.btn_test, self.btn_right, self.btn_backward, self.btn_rgb, self.btn_calibrate, self.btn_calibration_dialog, self.btn_battery,
			self.sensor_source_combo,
			self.btn_bras_gauche_up, self.btn_bras_gauche_down, self.btn_bras_droit_up, self.btn_bras_droit_down,
			self.btn_yeux_faches, self.btn_yeux_surpris, self.btn_yeux_wiggle,
			self.btn_emotion_celebrer, self.btn_emotion_bras, self.btn_emotion_wiggle,
			self.btn_load_dance, self.btn_play_dance, self.btn_toggle_act
		]
		for control in controls:
			control.setEnabled(enabled)
		self.btn_connect.setEnabled(not enabled)

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
		self.btn_toggle_act.setText("ARRÊTER Mode Automatique")
		self.update_log("Mode ACT démarré : surveillance du capteur couleur...")

	def _stop_act_mode(self):
		self.act_timer.stop()
		self.is_processing_act = False
		self.btn_toggle_act.setText("Démarrer Mode Automatique (ACT)")
		self.update_log("Mode ACT arrêté.")

	def process_act_loop(self):
		if self.is_processing_act or not self.controller.connected:
			return

		self.is_processing_act = True
		sensors_to_check = [
			("foot", "left", "Pied Gauche"),
			("foot", "right", "Pied Droit"),
			("color", "", "Capteur Add-on")
		]
		
		try:
			for source, foot, name in sensors_to_check:
				rgb = self.controller.lire_rgb(source=source, foot=foot, verbose=False)
				if rgb:
					color_name = self.color_sensor.identifier(*rgb)
					if color_name != "unknown":
						actions = self.act_mapping.get(color_name)
						if actions:
							self.update_log(f"[ACT] {name} a vu {color_name.upper()} -> Actions : {', '.join(actions)}")
							for action in actions:
								if hasattr(self.controller, action):
									getattr(self.controller, action)()
									self.api_client.send_movement(action, color=color_name)
								QApplication.processEvents()
								time.sleep(0.2)
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
		self.progress_bar.setValue(0)
		self.movements_check_label.setText(f"Mouvements : 0/{n}")
		self.movements_check_label.setStyleSheet("")

	def play_dance(self):
		if not self.current_sequence:
			self.update_log("Aucune chorégraphie chargée.")
			return
		self.btn_play_dance.setEnabled(False)
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

	def update_movements_verified_ui(self, executed: int, total: int, ok: bool):
		self.movements_check_label.setText(f"Mouvements : {executed}/{total}")
		if ok:
			self.movements_check_label.setStyleSheet("color: green;")
		else:
			self.movements_check_label.setStyleSheet("color: red;")

	def lire_capteur_rgb(self):
		source = self.sensor_source_combo.currentText()
		foot_param = "left" if source == "Pied gauche" else "right"
		source_param = "color" if source == "Capteur couleur" else "foot"
		
		rgb = self.controller.lire_rgb(source=source_param, foot=foot_param)
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
	app.setStyle("Fusion")
	
	style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.qss")
	if os.path.exists(style_path):
		with open(style_path, "r", encoding="utf-8") as f:
			app.setStyleSheet(f.read())
			
	signal.signal(signal.SIGINT, signal.SIG_DFL)
>>>>>>> Stashed changes
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
