"""
views.py — La logique de toutes les pages de l'interface web.

Dans Django, une "vue" c'est une fonction Python qui reçoit une requête HTTP
(quelqu'un qui visite une page) et retourne une réponse (le HTML à afficher).
C'est ici que se passe tout le traitement : lecture des données, calculs,
envoi au template HTML.
"""
import json
import subprocess
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import AlerteGSM

# Chemin absolu vers config.json sur le Pi
# On le met en constante ici pour ne pas avoir à le réécrire partout
CHEMIN_CONFIG = "/home/admin_uppa/config.json"


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions utilitaires pour config.json
# ─────────────────────────────────────────────────────────────────────────────

def charger_config():
    """
    Lit le fichier config.json et retourne son contenu sous forme
    de dictionnaire Python.

    Si le fichier n'existe pas ou est corrompu, on retourne un
    dictionnaire vide plutôt que de faire planter tout Django.
    """
    try:
        with open(CHEMIN_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # En cas de problème (fichier absent, JSON invalide...)
        # on retourne {} pour que les pages s'affichent quand même
        return {}


def sauvegarder_config(config):
    """
    Écrit le dictionnaire config dans config.json.

    Utilisé par la page de configuration quand l'utilisateur
    modifie les seuils ou le numéro d'alerte depuis l'interface web.
    Retourne True si ça a marché, False sinon.
    """
    try:
        with open(CHEMIN_CONFIG, "w", encoding="utf-8") as f:
            # indent=2 → fichier lisible avec une belle indentation
            # ensure_ascii=False → les accents s'écrivent normalement
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required  # si pas connecté → redirigé vers /login/ automatiquement
def dashboard(request):
    """
    La page d'accueil après connexion. Elle affiche :
    - Les compteurs d'alertes (actives, résolues, dernières 24h)
    - Le statut du service GSM (actif ou non)
    - Les seuils configurés pour chaque capteur
    - Les 20 dernières alertes dans un tableau
    - Un bouton pour déclencher un appel de test
    """

    # On commence par lire la config pour avoir les seuils et le numéro
    config = charger_config()

    # On récupère les 20 alertes les plus récentes depuis SQLite
    # Le [:20] limite à 20 résultats — inutile d'afficher 1000 lignes
    alertes_recentes = AlerteGSM.objects.all()[:20]

    # Quelques compteurs pour les stats en haut du dashboard
    alertes_actives  = AlerteGSM.objects.filter(statut='active').count()
    alertes_resolues = AlerteGSM.objects.filter(statut='resolue').count()
    total_alertes    = AlerteGSM.objects.count()

    # Alertes déclenchées dans les dernières 24 heures
    hier        = timezone.now() - timedelta(hours=24)
    alertes_24h = AlerteGSM.objects.filter(date_alerte__gte=hier).count()

    # On demande à Linux si le service gsm_alertes tourne actuellement
    # "systemctl is-active gsm_alertes" retourne "active" ou "inactive"
    try:
        result     = subprocess.run(
            ['systemctl', 'is-active', 'gsm_alertes'],
            capture_output=True,
            text=True
        )
        statut_gsm = result.stdout.strip()
    except Exception:
        # Si systemctl n'est pas dispo (tests sur PC par ex.), on met "inconnu"
        statut_gsm = "inconnu"

    # Le "context" c'est tout ce qu'on envoie au template HTML
    # Le template pourra utiliser ces variables avec {{ variable }}
    context = {
        'config':           config,
        'capteurs':         config.get('capteurs', {}),
        'alertes_recentes': alertes_recentes,
        'alertes_actives':  alertes_actives,
        'alertes_resolues': alertes_resolues,
        'total_alertes':    total_alertes,
        'alertes_24h':      alertes_24h,
        'statut_gsm':       statut_gsm,
        'numero_alerte':    config.get('gsm', {}).get('numero_alerte', 'Non configuré'),
    }

    return render(request, 'alertes/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HISTORIQUE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def historique(request):
    """
    Affiche toutes les alertes avec des filtres.

    L'utilisateur peut filtrer par capteur (ex: seulement frigo1)
    et par statut (seulement les actives, ou seulement les résolues).
    Les filtres passent par l'URL sous forme de paramètres GET :
    /historique/?capteur=frigo1&statut=active
    """

    # On part de toutes les alertes sans filtre
    alertes = AlerteGSM.objects.all()

    # Si l'utilisateur a choisi un capteur dans le menu déroulant,
    # on filtre pour ne garder que ce capteur
    capteur_filtre = request.GET.get('capteur', '')
    if capteur_filtre:
        alertes = alertes.filter(capteur=capteur_filtre)

    # Même principe pour le filtre par statut
    statut_filtre = request.GET.get('statut', '')
    if statut_filtre:
        alertes = alertes.filter(statut=statut_filtre)

    config  = charger_config()
    context = {
        'alertes':        alertes,
        'capteurs':       config.get('capteurs', {}),
        'capteur_filtre': capteur_filtre,
        'statut_filtre':  statut_filtre,
    }
    return render(request, 'alertes/historique.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION DES SEUILS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def configuration(request):
    """
    Permet de modifier les seuils d'alerte et le numéro de téléphone
    directement depuis l'interface web, sans avoir à faire un SSH sur le Pi.

    Quand l'utilisateur soumet le formulaire (méthode POST), on met à jour
    config.json. Comme gsm_alertes.py recharge ce fichier à chaque cycle,
    les nouveaux seuils sont pris en compte immédiatement sans redémarrage.
    """

    config  = charger_config()
    message = None  # sera rempli si succès ou erreur lors de la sauvegarde

    if request.method == 'POST':
        # Récupération du nouveau numéro d'alerte depuis le formulaire
        nouveau_numero = request.POST.get('numero_alerte', '').strip()
        if nouveau_numero:
            config['gsm']['numero_alerte'] = nouveau_numero

        # Pour chaque capteur dans la config, on récupère les nouveaux seuils
        # Le nom du champ dans le formulaire HTML est "seuil_max_frigo1" par ex.
        for cle in config.get('capteurs', {}):
            seuil_max = request.POST.get(f'seuil_max_{cle}')
            seuil_min = request.POST.get(f'seuil_min_{cle}')

            # On ne met à jour que si la valeur a bien été envoyée
            if seuil_max:
                config['capteurs'][cle]['seuil_max'] = float(seuil_max)
            if seuil_min:
                config['capteurs'][cle]['seuil_min'] = float(seuil_min)

        # On sauvegarde la config modifiée dans le fichier
        if sauvegarder_config(config):
            message = ('success', 'Configuration sauvegardée avec succès !')
        else:
            message = ('error', 'Erreur lors de la sauvegarde — vérifier les permissions du fichier.')

    context = {
        'config':   config,
        'capteurs': config.get('capteurs', {}),
        'message':  message,
    }
    return render(request, 'alertes/configuration.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# TEST D'APPEL MANUEL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def test_appel(request):
    """
    Déclenche un appel de test vers le numéro configuré.

    Utile pour vérifier que le module GSM fonctionne bien avant
    de le mettre en production, ou après l'insertion de la SIM.

    On utilise subprocess.Popen (et non run) pour lancer l'appel
    en arrière-plan sans bloquer la réponse HTTP — l'appel dure
    10 secondes, on ne veut pas que l'interface reste bloquée pendant ce temps.
    """
    if request.method == 'POST':
        try:
            # On lance un petit script Python inline qui ouvre le port série,
            # compose le numéro et raccroche après 10 secondes
            subprocess.Popen([
                'python3', '-c',
                '''
import sys
sys.path.insert(0, "/home/admin_uppa")
import json, serial, time

with open("/home/admin_uppa/config.json") as f:
    cfg = json.load(f)

ser    = serial.Serial(cfg["gsm"]["port_serie"], cfg["gsm"]["baudrate"], timeout=1)
time.sleep(2)
numero = cfg["gsm"]["numero_alerte"]

# ATD = AT Dial, le ";" indique un appel voix
ser.write(("ATD" + numero + ";\\r\\n").encode())
time.sleep(10)   # on laisse sonner 10 secondes

# ATH = raccroche
ser.write(b"ATH\\r\\n")
ser.close()
print("Appel test effectué")
                '''
            ])
            return JsonResponse({'statut': 'ok', 'message': 'Appel test déclenché !'})
        except Exception as e:
            return JsonResponse({'statut': 'erreur', 'message': str(e)})

    return JsonResponse({'statut': 'erreur', 'message': 'Méthode non autorisée'})


# ─────────────────────────────────────────────────────────────────────────────
# API — RÉCEPTION DES ALERTES DEPUIS gsm_alertes.py
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
# csrf_exempt est nécessaire ici car gsm_alertes.py n'est pas un navigateur web
# et n'a pas de token CSRF. Sans ça, Django refuserait toutes ses requêtes POST.
def api_alerte(request):
    """
    Point d'entrée HTTP pour recevoir les alertes depuis gsm_alertes.py.

    Quand gsm_alertes.py détecte un dépassement de seuil et passe les appels,
    il envoie automatiquement un POST JSON ici. On enregistre l'alerte
    dans SQLite pour qu'elle apparaisse dans le dashboard et l'historique.

    Format attendu :
    {
        "capteur":     "frigo1",
        "nom_capteur": "Réfrigérateur 1",
        "temperature": -55.0,
        "type_alerte": "SEUIL MAX DÉPASSÉ...",
        "tentatives":  3
    }
    """
    if request.method == 'POST':
        try:
            # On parse le JSON reçu dans le corps de la requête
            data = json.loads(request.body)

            # On crée une nouvelle ligne dans la table AlerteGSM
            AlerteGSM.objects.create(
                capteur     = data.get('capteur', ''),
                nom_capteur = data.get('nom_capteur', ''),
                temperature = data.get('temperature', 0),
                type_alerte = data.get('type_alerte', ''),
                tentatives  = data.get('tentatives', 0),
                statut      = 'active'  # toujours active à la création
            )
            return JsonResponse({'statut': 'ok'})

        except Exception as e:
            # En cas d'erreur on répond quand même pour ne pas faire planter
            # gsm_alertes.py qui attend une réponse
            return JsonResponse({'statut': 'erreur', 'message': str(e)})

    return JsonResponse({'statut': 'erreur', 'message': 'POST requis'})


@csrf_exempt
def api_resoudre_alerte(request, alerte_id):
    """
    Marque une alerte comme résolue depuis le dashboard.

    Appelée en JavaScript quand l'utilisateur clique sur le bouton
    "Résoudre" dans le tableau des alertes. L'ID de l'alerte est
    passé dans l'URL : /api/resoudre/42/
    """
    if request.method == 'POST':
        try:
            # On cherche l'alerte par son ID dans SQLite
            alerte        = AlerteGSM.objects.get(id=alerte_id)
            alerte.statut = 'resolue'
            alerte.save()
            return JsonResponse({'statut': 'ok'})

        except AlerteGSM.DoesNotExist:
            # L'alerte n'existe pas dans la base (ID incorrect)
            return JsonResponse({'statut': 'erreur', 'message': 'Alerte introuvable'})

    return JsonResponse({'statut': 'erreur'})
