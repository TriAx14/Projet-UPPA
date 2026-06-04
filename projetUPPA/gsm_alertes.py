"""

  MODULE ALERTES GSM — Projet UPPA LFCR
  Rôle     : Lire les températures depuis InfluxDB,
             déclencher un appel si seuil dépassé,
             et notifier Django pour l'affichage web.

  Dépendances :
    pip install pyserial influxdb-client requests --break-system-packages

"""

import serial       # Communication série UART avec le SIM800C
import time         # Gestion des délais
import logging      # Journalisation fichier + console
import json         # Lecture de config.json
import os           # Gestion des chemins
import requests     # Envoi des notifications vers Django

from influxdb_client import InfluxDBClient  # Client InfluxDB v2



#  CONFIGURATION


CHEMIN_CONFIG = os.path.join(os.path.dirname(__file__), "config.json")

# URL de l'API Django pour enregistrer les alertes
# Django tourne sur le même Pi → localhost
DJANGO_API_URL = "http://localhost:8000/api/alerte/"


def charger_config(chemin=CHEMIN_CONFIG):
    """
    Charge config.json.
    Rechargé à chaque cycle → seuils modifiables sans redémarrage.
    """
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERREUR] config.json introuvable : {chemin}")
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"[ERREUR] config.json invalide : {e}")
        raise SystemExit(1)

CONFIG = charger_config()


# =============================================================
#  LOGGING
# =============================================================

LOG_FILE = "/home/admin_uppa/alertes_gsm.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# =============================================================
#  CLASSE SIM800C
# =============================================================

class SIM800C:
    """
    Gère la communication avec le module GSM SIM800C via UART.
    Initialise le module, la SIM Syma Mobile et le réseau GSM.
    """

    def __init__(self):
        cfg = CONFIG["gsm"]
        try:
            self.ser = serial.Serial(cfg["port_serie"], cfg["baudrate"], timeout=1)
            log.info(f"Port série ouvert : {cfg['port_serie']} @ {cfg['baudrate']} baud")
        except serial.SerialException as e:
            log.error(f"Impossible d'ouvrir le port série : {e}")
            raise

        log.info("Attente démarrage SIM800C (3s)...")
        time.sleep(3)
        self._init_module()
        self._init_sim()
        self._init_reseau()

    def _init_module(self):
        """Initialisation de base : test AT + options."""
        log.info("--- Init module ---")
        reponse = self.send_cmd("AT", attente=1)
        if "OK" in reponse:
            log.info("SIM800C opérationnel.")
        else:
            log.error("Module ne répond pas ! Vérifier câblage.")
        self.send_cmd("AT+CMGF=1", attente=0.5)   # Mode SMS texte
        self.send_cmd("AT+CLIP=1", attente=0.5)    # Afficher numéro appelant
        signal = self.send_cmd("AT+CSQ", attente=1)
        log.info(f"Signal GSM : {signal.strip()}")

    def _init_sim(self):
        """
        Vérifie et déverrouille la SIM.
        AT+CPIN? → READY / SIM PIN / SIM PUK / ERROR
        """
        log.info("--- Init SIM ---")
        cfg_sim = CONFIG["sim"]
        reponse = self.send_cmd("AT+CPIN?", attente=1)

        if "READY" in reponse:
            log.info("SIM prête (pas de PIN requis).")

        elif "SIM PIN" in reponse:
            pin = cfg_sim.get("pin", "")
            if not pin:
                log.error("PIN requis mais non défini dans config.json !")
                raise SystemExit(1)
            log.info("Saisie du PIN...")
            reponse_pin = self.send_cmd(f"AT+CPIN={pin}", attente=3)
            if "OK" in reponse_pin:
                log.info("PIN accepté.")
                time.sleep(2)
            else:
                log.error("PIN refusé ! Vérifier config.json.")
                raise SystemExit(1)

        elif "SIM PUK" in reponse:
            log.critical("SIM BLOQUÉE (PUK) ! Intervention manuelle requise.")
            raise SystemExit(1)

        else:
            log.error("SIM non détectée ! Vérifier l'insertion (Mini-SIM 2FF).")
            raise SystemExit(1)

        reponse_finale = self.send_cmd("AT+CPIN?", attente=1)
        if "READY" in reponse_finale:
            log.info("SIM opérationnelle.")

    def _init_reseau(self):
        """
        Attend l'enregistrement sur le réseau SFR/Syma.
        AT+CREG? → ,1 = réseau local / ,5 = itinérance
        """
        log.info("--- Enregistrement réseau ---")
        for essai in range(10):
            reponse = self.send_cmd("AT+CREG?", attente=1)
            if ",1" in reponse or ",5" in reponse:
                log.info("Enregistré sur le réseau GSM.")
                operateur = self.send_cmd("AT+COPS?", attente=1)
                log.info(f"Opérateur : {operateur.strip()}")
                return
            elif ",2" in reponse:
                log.info(f"Recherche réseau... ({essai+1}/10)")
            else:
                log.warning(f"Non enregistré ({essai+1}/10)")
            time.sleep(3)
        log.warning("Réseau GSM non trouvé après 30s.")

    def send_cmd(self, cmd, attente=0.5):
        """Envoie une commande AT et retourne la réponse."""
        self.ser.write((cmd + "\r\n").encode())
        time.sleep(attente)
        reponse = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
        log.debug(f">> {cmd} | << {reponse.strip()}")
        return reponse

    def appeler(self, numero):
        """
        Passe un appel vocal.
        ATD<numero>; = appel voix
        ATH          = raccroche après la durée configurée
        """
        duree = CONFIG["gsm"]["duree_appel"]
        log.info(f"Appel vers {numero} ({duree}s max)...")
        self.send_cmd(f"ATD{numero};", attente=duree)
        self.send_cmd("ATH", attente=1)
        log.info("Appel terminé.")

    def fermer(self):
        if self.ser.is_open:
            self.ser.close()
            log.info("Port série fermé.")


# =============================================================
#  CLASSE LecteurInflux
# =============================================================

class LecteurInflux:
    """
    Interroge InfluxDB pour récupérer les dernières températures
    enregistrées par Corentin (module RS485).
    """

    def __init__(self):
        cfg = CONFIG["influxdb"]
        self.client = InfluxDBClient(
            url=cfg["url"],
            token=cfg["token"],
            org=cfg["org"]
        )
        self.query_api   = self.client.query_api()
        self.org         = cfg["org"]
        self.bucket      = cfg["bucket"]
        self.measurement = cfg["measurement"]
        self.field       = cfg["field"]
        log.info(f"Connecté à InfluxDB : {cfg['url']}")

    def lire_temperature(self, nom_capteur):
        """
        Récupère la dernière température du capteur dans les 5 dernières minutes.
        Retourne float ou None si aucune donnée.
        """
        requete = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "{self.field}")
          |> filter(fn: (r) => r.capteur == "{nom_capteur}")
          |> last()
        '''
        try:
            tables = self.query_api.query(requete, org=self.org)
            for table in tables:
                for record in table.records:
                    temp = float(record.get_value())
                    log.info(f"[InfluxDB] {nom_capteur} : {temp:.2f}°C")
                    return temp
            log.warning(f"[InfluxDB] Pas de donnée récente pour '{nom_capteur}'.")
            return None
        except Exception as e:
            log.error(f"[InfluxDB] Erreur '{nom_capteur}' : {e}")
            return None

    def fermer(self):
        self.client.close()
        log.info("Connexion InfluxDB fermée.")


# =============================================================
#  NOTIFICATION DJANGO
# =============================================================

def notifier_django(cle_capteur, config_capteur, temperature, type_alerte, nb_tentatives):
    """
    Envoie une notification HTTP POST à Django pour enregistrer
    l'alerte dans la base de données et l'afficher sur le dashboard.

    Django doit tourner sur le même Pi (localhost:8000).
    Si Django n'est pas démarré, on log un avertissement mais
    le programme continue — les appels GSM ne sont pas bloqués.

    Args:
        cle_capteur     : clé du capteur (ex: "frigo1")
        config_capteur  : dict de config du capteur
        temperature     : température qui a déclenché l'alerte
        type_alerte     : description de l'alerte
        nb_tentatives   : nombre d'appels effectués
    """
    payload = {
        "capteur":     cle_capteur,
        "nom_capteur": config_capteur["nom"],
        "temperature": temperature,
        "type_alerte": type_alerte,
        "tentatives":  nb_tentatives
    }

    try:
        # Timeout court : si Django ne répond pas en 2s, on continue quand même
        reponse = requests.post(DJANGO_API_URL, json=payload, timeout=2)

        if reponse.status_code == 200:
            log.info(f"[Django] Alerte enregistrée dans le dashboard.")
        else:
            log.warning(f"[Django] Réponse inattendue : {reponse.status_code}")

    except requests.exceptions.ConnectionError:
        # Django pas démarré → pas bloquant, juste un avertissement
        log.warning("[Django] Serveur web non disponible — alerte non enregistrée dans le dashboard.")
    except requests.exceptions.Timeout:
        log.warning("[Django] Timeout — Django trop lent à répondre.")
    except Exception as e:
        log.warning(f"[Django] Erreur notification : {e}")


# =============================================================
#  VÉRIFICATION DES SEUILS
# =============================================================

def verifier_seuils(temperature, config_capteur):
    """
    Compare la température aux seuils de config.json.
    Retourne une description d'alerte ou None si tout va bien.
    """
    if temperature > config_capteur["seuil_max"]:
        return (
            f"SEUIL MAX DÉPASSÉ "
            f"(mesure : {temperature:.1f}°C / seuil : {config_capteur['seuil_max']}°C)"
        )
    if temperature < config_capteur["seuil_min"]:
        return (
            f"SEUIL MIN DÉPASSÉ "
            f"(mesure : {temperature:.1f}°C / seuil : {config_capteur['seuil_min']}°C)"
        )
    return None


# =============================================================
#  SÉQUENCE D'ALERTE
# =============================================================

def sequence_alerte(gsm, temperature, cle_capteur, config_capteur, type_alerte):
    """
    Déclenche les appels téléphoniques ET notifie Django.

    Ordre :
    1. Log de l'alerte
    2. Appels téléphoniques (jusqu'à MAX_TENTATIVES)
    3. Notification Django (enregistrement dans le dashboard)
    """
    cfg    = CONFIG["gsm"]
    numero = cfg["numero_alerte"]
    max_t  = cfg["max_tentatives"]
    delai  = cfg["delai_entre_tentatives"]

    log.warning(
        f"!!! ALERTE — {config_capteur['nom']} : "
        f"{temperature:.1f}°C — {type_alerte} !!!"
    )

    # ── Appels téléphoniques ──────────────────────────────────
    for tentative in range(1, max_t + 1):
        log.info(f"Tentative {tentative}/{max_t}...")
        gsm.appeler(numero)
        if tentative < max_t:
            log.info(f"Prochaine tentative dans {delai}s...")
            time.sleep(delai)

    log.info("Fin des appels.")

    # ── Notification Django ───────────────────────────────────
    # Envoyée APRÈS les appels pour ne pas retarder les alertes
    notifier_django(cle_capteur, config_capteur, temperature, type_alerte, max_t)


# =============================================================
#  BOUCLE PRINCIPALE
# =============================================================

def main():
    log.info("=" * 55)
    log.info("  Démarrage module alertes GSM — UPPA LFCR")
    log.info("=" * 55)

    # Affichage des seuils au démarrage
    log.info("Seuils configurés :")
    for cle, cfg in CONFIG["capteurs"].items():
        log.info(f"  {cfg['nom']} : min={cfg['seuil_min']}°C / max={cfg['seuil_max']}°C")

    # ── Init GSM ──────────────────────────────────────────────
    try:
        gsm = SIM800C()
    except SystemExit:
        log.critical("Arrêt : problème SIM ou module GSM.")
        return
    except Exception as e:
        log.critical(f"Erreur init GSM : {e}")
        return

    # ── Init InfluxDB ─────────────────────────────────────────
    try:
        influx = LecteurInflux()
    except Exception as e:
        log.critical(f"Erreur connexion InfluxDB : {e}")
        gsm.fermer()
        return

    # ── Suivi alertes actives ─────────────────────────────────
    # Évite les appels répétés tant que la température est anormale
    alertes_actives = {cle: False for cle in CONFIG["capteurs"]}

    intervalle = CONFIG["surveillance"]["intervalle_lecture"]
    log.info(f"Surveillance active — lecture toutes les {intervalle}s.")
    log.info("Ctrl+C pour arrêter.")

    # ── Boucle de surveillance ────────────────────────────────
    try:
        while True:
            # Rechargement config → seuils modifiables à chaud depuis Django
            CONFIG.update(charger_config())

            for cle_capteur, config_capteur in CONFIG["capteurs"].items():

                # Lecture température InfluxDB
                temperature = influx.lire_temperature(cle_capteur)
                if temperature is None:
                    continue

                # Vérification seuils
                type_alerte = verifier_seuils(temperature, config_capteur)

                if type_alerte and not alertes_actives[cle_capteur]:
                    # Nouvelle alerte → appels + notification Django
                    alertes_actives[cle_capteur] = True
                    sequence_alerte(
                        gsm, temperature,
                        cle_capteur, config_capteur,
                        type_alerte
                    )

                elif not type_alerte and alertes_actives[cle_capteur]:
                    # Retour à la normale
                    log.info(
                        f"{config_capteur['nom']} normale : "
                        f"{temperature:.2f}°C. Alerte réinitialisée."
                    )
                    alertes_actives[cle_capteur] = False

            time.sleep(intervalle)

    except KeyboardInterrupt:
        log.info("Arrêt demandé (Ctrl+C).")

    finally:
        gsm.fermer()
        influx.fermer()
        log.info("Programme arrêté proprement.")


if __name__ == "__main__":
    main()
