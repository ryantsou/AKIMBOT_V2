#!/bin/bash
# Script pour créer les branches de fonctionnalités du projet AKIMBOT_V2
# À lancer depuis la racine du dépôt (branche master à jour)

set -euo pipefail

BRANCHES=(
  "feature/initialisation"
  "feature/conception"
  "feature/gestion"
  "feature/client-marty"
  "feature/client-ui"
  "feature/arbitre"
  "feature/integration"
)

git checkout master

git fetch origin

git pull origin master

for branch in "${BRANCHES[@]}"; do
  if git show-ref --verify --quiet refs/heads/$branch; then
    echo "[OK] Branche locale déjà présente : $branch"
  else
    git branch $branch master
    echo "[+] Branche locale créée : $branch"
  fi
  if git ls-remote --exit-code --heads origin $branch > /dev/null 2>&1; then
    echo "[OK] Branche distante déjà présente : $branch"
  else
    git push -u origin $branch
    echo "[+] Branche poussée sur origin : $branch"
  fi
done

echo "Toutes les branches de fonctionnalités sont prêtes !"
