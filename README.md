- `approbot/client_robot.py`: l'interface graphique du client (PyQt5)
- `requirements.txt`: liste des dépendances Python (FastAPI, PyQt5, etc.)
+- `appserver/serveur_arbitre.py`: le serveur arbitre (FastAPI)
# 🤖 AKIMBOT

Bienvenue sur le dépôt du projet **AKIMBOT** ! 
Il s'agit de notre projet visant à développer un système complet pour contrôler le robot Marty (via une interface graphique) et gérer des affrontements/danses via un serveur arbitre central.
src : https://userguides.robotical.io/martyv2/documentation/python_function_reference#init

## 🎯 Les grands objectifs du projet

Pour mener à bien ce projet, voici ce que nous allons développer :

- **L'application client robot** : pour piloter Marty et lire les capteurs (interface PyQt + librairie martypy).
- **L'application serveur arbitre** : une API REST (FastAPI) pour centraliser et calculer les scores.
- **La gestion des fichiers** : parsing et exécution des chorégraphies (`.dance`) et des règles (`.battle`).
- **La gestion de projet** : suivi rigoureux sur GitHub (issues, kanban, branches, pull requests).
- **La qualité** : tests unitaires, revue de code, et bien sûr une démo finale fonctionnelle !

## 👥 L'équipe

- **RAJHONSON**
- **IHEB**
- **ILLAS**



## 🛠️ Installation

Pour configurer l'environnement (`.venv`) et installer les dépendances :
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

## 🚀 Lancement

**Lancer l'interface Client Robot :**
```bash
.venv/bin/python approbot/client_robot.py
```

## 🌿 Branches Git par fonctionnalité

Chaque phase du Gantt correspond à une branche dédiée :

| Branche | Phase |
|---|---|
| `feature/initialisation` | 🚀 Initialisation |
| `feature/gestion` | 📋 Gestion |
| `feature/conception` | 🏗️ Conception |
| `feature/client-marty` | 🔌 Client – Marty |
| `feature/client-ui` | 🖥️ Client – UI |
| `feature/arbitre` | ⚖️ Arbitre |
| `feature/integration` | 🔗 Intégration |

### Création des branches

Le script `create_feature_branches.sh` crée toutes les branches depuis `master` en une seule commande :

```bash
chmod +x scripts/create_feature_branches.sh
./scripts/create_feature_branches.sh
```

Le script est idempotent : il ne recrée pas une branche qui existe déjà.

### Convention de nommage

- Branches de fonctionnalité : `feature/<nom-court>` (minuscules, tirets)
- Branches de correction : `fix/<description>`
- Branches de release : `release/<version>`

Toute modification transite par une **Pull Request** vers `master` (branche protégée).

## 📁 Fichiers importants

- `gantt.xlsx`: planning source
- `scripts/sync_gantt_project.py`: synchronisation Gantt -> GitHub
- `scripts/install.sh`: création de l'environnement local
- `scripts/create_feature_branches.sh`: création des branches Git par fonctionnalité
- `approbot/client_robot.py`: l'interface graphique du client (PyQt5)
- `requirements.txt`: liste des dépendances Python (FastAPI, PyQt5, etc.)
