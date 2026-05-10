# 📚 Référence des Commandes `martypy` (AKIMBOT)

Ce document regroupe les commandes les plus utiles de la librairie `martypy` pour piloter le robot Marty. C'est la boîte à outils principale pour développer les actions dans `client_robot.py`, parser les fichiers `.dance` et envoyer les données des capteurs au serveur arbitre.

---

## 1. 🚀 Actions de Haut Niveau (Mouvements pré-programmés)
Idéal pour le contrôle manuel (clavier/pad directionnel) ou les actions simples.

- **Marcher / Tourner / Reculer**
  ```python
  marty.walk(num_steps=2, turn=0, step_length=25, side='left', move_time=1500)
  ```
  *Paramètres clés :*
  - `num_steps` : Nombre de pas.
  - `turn` : Angle (positif pour la gauche, négatif pour la droite). `0` = tout droit.
  - `step_length` : Longueur. Une valeur négative (ex: `-25`) fait reculer.

- **Célébration et Danse**
  ```python
  marty.celebrate() # Petite danse de victoire
  marty.dance()     # Séquence de danse complète
  ```

- **Interactions Physiques**
  ```python
  marty.kick(side='right')   # side = 'left' ou 'right'
  marty.stand_straight()     # Remet le robot droit à sa position initiale (zéro)
  ```

---

## 2. ⚙️ Contrôle Fin (Bas niveau pour les chorégraphies `.dance`)
Essentiel pour la classe `DanceParser` et pour créer vos propres mouvements.

- **Contrôle d'un moteur spécifique**
  ```python
  marty.move_joint(joint_id, angle, move_time)
  # Exemple : lève le bras gauche à 45° en 1 seconde
  marty.move_joint('left_arm', 45, 1000) 
  ```
  *Notes sur `joint_id` : Peut être un nom (ex: `'left_knee'`, `'right_hip'`, `'eyes'`) ou un ID numérique (0-8).*

- **Raccourcis corporels**
  ```python
  marty.arms(left_angle, right_angle, move_time)
  marty.lean(direction, amount, move_time) # direction = 'left', 'right', 'forward', 'back'
  ```

- **Expressions (Yeux)**
  ```python
  marty.eyes('angry')    # Options : 'angry', 'excited', 'wide', 'normal'
  marty.eyes(45)         # Angle personnalisé
  ```

---

## 3. 📡 Lecture des Capteurs (Pour l'Arbitre)
Ces commandes servent à interagir avec l'environnement pour déclencher des règles dans le fichier `.battle`.

- **Capteur de couleur / Pied**
  ```python
  # Lire la valeur brute du capteur sous le pied
  lecture = marty.get_ground_sensor_reading('left') # ou 'right'
  
  # Détecter si le pied touche le sol
  au_sol = marty.foot_on_ground('left') # Retourne True ou False
  
  # Détecter un obstacle devant le pied
  obstacle = marty.foot_obstacle_sensed('left')
  ```

- **Batterie et Télémétrie**
  ```python
  # Retourne le % de batterie (pour la jauge de l'UI)
  batterie = marty.get_battery_remaining()
  
  # Lire l'accéléromètre (pour détecter une chute, un saut...)
  accel_x = marty.get_accelerometer('x') # axes: 'x', 'y', 'z'
  ```

---

## 4. 🔊 Audio et Visuels (Feedback)
Pour donner plus de vie au robot lors d'un match.

- **Sons**
  ```python
  marty.play_sound('excited')
  ```

- **Lumières (Si add-on LED "Disco" branché)**
  ```python
  marty.disco_color('red')
  ```