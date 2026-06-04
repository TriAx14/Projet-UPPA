#!/bin/bash
# =============================================================
#  INSTALLATION DJANGO — Projet UPPA LFCR
# =============================================================
set -e

VERT="\033[0;32m"
JAUNE="\033[1;33m"
RESET="\033[0m"

echo ""
echo "============================================="
echo "  Installation Django — UPPA GSM"
echo "============================================="

# 1. Installation Django
echo -e "${JAUNE}[1/4] Installation Django...${RESET}"
pip install django --break-system-packages
echo -e "${VERT}✓ Django installé${RESET}"

# 2. Migrations base de données
echo -e "${JAUNE}[2/4] Création base de données...${RESET}"
python3 manage.py makemigrations
python3 manage.py migrate
echo -e "${VERT}✓ Base de données prête${RESET}"

# 3. Création du superutilisateur
echo -e "${JAUNE}[3/4] Création compte admin...${RESET}"
python3 manage.py shell << PYEOF
from django.contrib.auth.models import User
if not User.objects.filter(username='uppaadmin').exists():
    User.objects.create_superuser('uppaadmin', '', 'aDmin"#26"')
    print("Compte uppaadmin créé.")
else:
    print("Compte uppaadmin déjà existant.")
PYEOF
echo -e "${VERT}✓ Compte créé : uppaadmin / aDmin\"#26\"${RESET}"

# 4. Instructions finales
echo ""
echo "============================================="
echo -e "${VERT}  Installation terminée !${RESET}"
echo "============================================="
echo ""
echo "  Lancer le serveur Django :"
echo "  python3 manage.py runserver 0.0.0.0:8000"
echo ""
echo "  Accès depuis n'importe quel PC du réseau :"
echo "  http://10.0.251.223:8000/dashboard/"
echo ""
echo "  Login : uppaadmin"
echo "  MDP   : aDmin\"#26\""
