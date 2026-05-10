# 🚀 Guide de survie AKIMBOT (à lire absolument !)

Yo .. Vu qu'on a restructuré les dossiers pour avoir un projet bien propre (fini le bazar à la racine), voici un petit récap express pour bien démarrer sans créer de conflits Git et tout casser.

## 1️⃣ Mettre à jour son PC (Le truc à pas oublier)

Avant de commencer à coder, assurez-vous d'avoir la toute dernière version de `master` :
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
