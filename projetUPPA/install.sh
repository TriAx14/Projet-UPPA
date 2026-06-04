#!/bin/bash
# =============================================================
#  SCRIPT D'INSTALLATION — Module Alertes GSM
#  Projet UPPA LFCR — BTS CIEL — Alexandre ALIAS
# =============================================================
#  Ce script installe et configure tout le nécessaire pour
#  faire fonctionner le module d'alertes GSM sur le Pi.
#
#  Utilisation :
#    chmod +x install.sh
#    ./install.sh
# =============================================================

# Arrêt immédiat si une commande échoue
set -e

# Couleurs pour l'affichage
VERT="\033[0;32m"
ROUGE="\033[0;31m"
JAUNE="\033[1;33m"
RESET="\033[0m"

echo ""
echo "============================================="
echo "  Installation Module Alertes GSM — UPPA"
echo "============================================="
echo ""

# ── Étape 1 : Vérification Python 3 ──────────────────────────
echo -e "${JAUNE}[1/6] Vérification Python 3...${RESET}"
if command -v python3 &>/dev/null; then
    VERSION=$(python3 --version)
    echo -e "${VERT}✓ $VERSION détecté${RESET}"
else
    echo -e "${ROUGE}✗ Python 3 non trouvé !${RESET}"
    exit 1
fi

# ── Étape 2 : Installation des bibliothèques Python ───────────
echo ""
echo -e "${JAUNE}[2/6] Installation des bibliothèques Python...${RESET}"

# Vérification si les libs sont déjà installées (mode hors ligne possible)
if pip3 show pyserial &>/dev/null && pip3 show influxdb-client &>/dev/null; then
    echo -e "${VERT}✓ pyserial et influxdb-client déjà installés${RESET}"
else
    # Tentative installation en ligne
    echo "Tentative installation via pip..."
    if pip3 install pyserial influxdb-client --break-system-packages 2>/dev/null; then
        echo -e "${VERT}✓ Bibliothèques installées${RESET}"
    else
        # Installation hors ligne depuis le dossier libs_gsm (clé USB)
        echo -e "${JAUNE}Pas d'accès internet — tentative depuis ./libs_gsm...${RESET}"
        if [ -d "./libs_gsm" ]; then
            pip3 install --no-index --find-links=./libs_gsm pyserial influxdb-client --break-system-packages
            echo -e "${VERT}✓ Bibliothèques installées depuis libs_gsm${RESET}"
        else
            echo -e "${ROUGE}✗ Dossier libs_gsm introuvable !${RESET}"
            echo "  → Télécharger sur un PC : pip download pyserial influxdb-client -d ./libs_gsm"
            echo "  → Copier le dossier libs_gsm ici et relancer install.sh"
            exit 1
        fi
    fi
fi

# ── Étape 3 : Activation UART et désactivation Bluetooth ──────
echo ""
echo -e "${JAUNE}[3/6] Vérification configuration UART...${RESET}"

CONFIG_BOOT="/boot/firmware/config.txt"

# Vérification disable-bt
if grep -q "dtoverlay=disable-bt" "$CONFIG_BOOT"; then
    echo -e "${VERT}✓ Bluetooth déjà désactivé${RESET}"
else
    echo "Désactivation du Bluetooth (libère l'UART principal)..."
    echo "dtoverlay=disable-bt" | sudo tee -a "$CONFIG_BOOT" > /dev/null
    echo -e "${VERT}✓ Bluetooth désactivé${RESET}"
    REBOOT_REQUIS=1
fi

# Vérification w1-gpio pour DS18B20 (si utilisé)
if grep -q "dtoverlay=w1-gpio" "$CONFIG_BOOT"; then
    echo -e "${VERT}✓ Interface 1-Wire (DS18B20) déjà activée${RESET}"
else
    echo "Activation interface 1-Wire pour capteurs DS18B20..."
    echo "dtoverlay=w1-gpio" | sudo tee -a "$CONFIG_BOOT" > /dev/null
    echo -e "${VERT}✓ Interface 1-Wire activée${RESET}"
    REBOOT_REQUIS=1
fi

# ── Étape 4 : Copie des fichiers du projet ────────────────────
echo ""
echo -e "${JAUNE}[4/6] Copie des fichiers...${RESET}"

DEST="/home/admin_uppa"

# Copie du script principal
if [ -f "./gsm_alertes.py" ]; then
    cp ./gsm_alertes.py "$DEST/gsm_alertes.py"
    echo -e "${VERT}✓ gsm_alertes.py copié dans $DEST${RESET}"
else
    echo -e "${ROUGE}✗ gsm_alertes.py introuvable dans le répertoire courant !${RESET}"
    exit 1
fi

# Copie de la config (uniquement si elle n'existe pas déjà, pour ne pas écraser)
if [ ! -f "$DEST/config.json" ]; then
    if [ -f "./config.json" ]; then
        cp ./config.json "$DEST/config.json"
        echo -e "${VERT}✓ config.json copié dans $DEST${RESET}"
    else
        echo -e "${ROUGE}✗ config.json introuvable !${RESET}"
        exit 1
    fi
else
    echo -e "${JAUNE}⚠ config.json déjà présent — non écrasé (vos paramètres sont conservés)${RESET}"
fi

# Création du fichier de log s'il n'existe pas
touch "$DEST/alertes_gsm.log"
echo -e "${VERT}✓ Fichier de log prêt : $DEST/alertes_gsm.log${RESET}"

# ── Étape 5 : Installation du service systemd ─────────────────
echo ""
echo -e "${JAUNE}[5/6] Installation du service systemd...${RESET}"

sudo cp ./gsm_alertes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gsm_alertes
echo -e "${VERT}✓ Service gsm_alertes installé et activé au démarrage${RESET}"

# ── Étape 6 : Résumé et instructions finales ──────────────────
echo ""
echo -e "${JAUNE}[6/6] Vérification finale...${RESET}"
echo ""
echo "============================================="
echo -e "${VERT}  Installation terminée avec succès !${RESET}"
echo "============================================="
echo ""
echo "  Avant de démarrer, vérifier config.json :"
echo "  → nano /home/admin_uppa/config.json"
echo ""
echo "  Renseigner :"
echo "  - numero_alerte : votre numéro en +336XXXXXXXX"
echo "  - token InfluxDB (fourni par l'Étudiant 4)"
echo "  - pin SIM : laisser vide si PIN désactivé"
echo ""
echo "  Commandes utiles :"
echo "  → Démarrer  : sudo systemctl start gsm_alertes"
echo "  → Arrêter   : sudo systemctl stop gsm_alertes"
echo "  → Statut    : sudo systemctl status gsm_alertes"
echo "  → Logs live : sudo journalctl -u gsm_alertes -f"
echo ""

# Redémarrage si nécessaire (UART ou 1-Wire modifié)
if [ "$REBOOT_REQUIS" = "1" ]; then
    echo -e "${JAUNE}⚠ Un redémarrage est nécessaire pour appliquer les"
    echo -e "  modifications de /boot/firmware/config.txt${RESET}"
    echo ""
    read -p "  Redémarrer maintenant ? (o/n) : " CHOIX
    if [ "$CHOIX" = "o" ] || [ "$CHOIX" = "O" ]; then
        sudo reboot
    else
        echo "  → Penser à redémarrer avant de lancer le service !"
    fi
fi
