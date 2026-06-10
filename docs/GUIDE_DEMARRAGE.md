# Guide de démarrage AKIMBOT

Ce document détaille les procédures standards pour contribuer au projet.

## 1. Mise à jour du dépôt local

Avant toute modification, synchronisez la branche principale :
```bash
git checkout master
git pull origin master
```
*Note : Les fichiers sont maintenant proprement rangés dans `approbot/`, `appserver/`, `scripts/` et `tests/`.*

## Étape 2 : Choisir sa branche de travail

Ne codez pas directement sur `master`. mais faut Placez sur la branche correspondant au tâche (ex: conception) :
```bash
git checkout feature/conception
```

## Étape 3 : Lancer les applications

Puisque les dossiers ont changé, voici les nouvelles commandes à exécuter depuis la racine (`AKIMBOT/`) :
- **Pour lancer le Client (Interface) :** `.venv/bin/python approbot/client_robot.py`
- **Pour lancer le Serveur (Arbitre) :** `.venv/bin/python appserver/serveur_arbitre.py`

## Étape 4 : Sauvegarder son travail (Commit)

Utilisez toujours la convention de l'équipe pour vos commits avec numero #issues, j'ai oublier mais faut qu'on fait ça pour ne pas se perdre:
```bash
git commit -m "feat(client): ajout du bouton avancer"
```

## Étape 5 : Partager son code

Quand vous avez fini une tâche, poussez votre code (`git push origin votre-branche`) puis allez sur GitHub pour ouvrir une **Pull Request** vers `master`. 
