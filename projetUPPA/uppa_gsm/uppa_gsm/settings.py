"""
settings.py — Configuration générale de Django pour le projet UPPA GSM.

C'est ici qu'on définit tout ce qui touche au fonctionnement global de
l'application : base de données, applications installées, langue, etc.
On n'a normalement pas besoin de toucher à ce fichier souvent.
"""
import os
from pathlib import Path

# BASE_DIR pointe vers le dossier racine du projet (là où se trouve manage.py)
# Path(__file__) = chemin de ce fichier settings.py
# .parent.parent = deux niveaux au-dessus → le dossier uppa_gsm/
BASE_DIR = Path(__file__).resolve().parent.parent


# ─── Sécurité ────────────────────────────────────────────────────────────────

# Clé secrète utilisée par Django pour signer les sessions et les tokens CSRF
# En production réelle il faudrait la garder secrète et ne pas la mettre
# dans le code source, mais pour ce projet c'est suffisant
SECRET_KEY = 'uppa-lfcr-gsm-secret-key-2025'

# En mode DEBUG=True, Django affiche les erreurs en détail dans le navigateur
# C'est pratique pendant le développement mais à désactiver en production
DEBUG = True

# On autorise toutes les adresses IP à accéder à l'interface
# '*' = n'importe quel PC du réseau UPPA peut se connecter
ALLOWED_HOSTS = ['*']


# ─── Applications installées ─────────────────────────────────────────────────

# Django fonctionne par "applications" — chacune apporte des fonctionnalités
INSTALLED_APPS = [
    'django.contrib.admin',        # interface d'administration (/admin/)
    'django.contrib.auth',         # système de login/logout/utilisateurs
    'django.contrib.contenttypes', # nécessaire pour les permissions
    'django.contrib.sessions',     # gestion des sessions (cookie de connexion)
    'django.contrib.messages',     # messages flash (notifications)
    'django.contrib.staticfiles',  # gestion des fichiers CSS/JS/images
    'alertes',                     # notre propre application (dashboard GSM)
]


# ─── Middleware ───────────────────────────────────────────────────────────────

# Les middleware sont des couches qui traitent chaque requête HTTP
# avant qu'elle arrive à notre code et après qu'on envoie la réponse
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',           # headers de sécurité
    'django.contrib.sessions.middleware.SessionMiddleware',    # gère les sessions
    'django.middleware.common.CommonMiddleware',               # normalisation URLs
    'django.middleware.csrf.CsrfViewMiddleware',               # protection CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware', # gère request.user
    'django.contrib.messages.middleware.MessageMiddleware',    # messages flash
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # protection iframes
]


# ─── URLs ─────────────────────────────────────────────────────────────────────

# Django cherche les URLs dans ce fichier quand une requête arrive
ROOT_URLCONF = 'uppa_gsm.urls'


# ─── Templates HTML ───────────────────────────────────────────────────────────

# Configuration du moteur de templates Django
# APP_DIRS=True → Django cherche les templates dans les dossiers
# "templates/" de chaque application (alertes/templates/)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],       # pas de dossiers templates globaux supplémentaires
        'APP_DIRS': True, # chercher dans les apps → alertes/templates/
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request', # donne accès à request dans les templates
                'django.contrib.auth.context_processors.auth', # donne accès à user dans les templates
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'uppa_gsm.wsgi.application'


# ─── Base de données ──────────────────────────────────────────────────────────

# On utilise SQLite — c'est une base de données légère stockée dans un seul
# fichier (db.sqlite3). Parfait pour notre usage : stocker l'historique des alertes.
# Pas besoin d'installer MySQL ou PostgreSQL.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3', # le fichier sera créé à la racine du projet
    }
}


# ─── Langue et fuseau horaire ─────────────────────────────────────────────────

LANGUAGE_CODE = 'fr-fr'         # interface en français
TIME_ZONE     = 'Europe/Paris'  # important pour que les dates des alertes soient correctes
USE_I18N      = True            # internationalisation activée
USE_TZ        = True            # utiliser les timezones (recommandé)


# ─── Fichiers statiques ───────────────────────────────────────────────────────

# Les fichiers CSS, JS et images seront accessibles à /static/
STATIC_URL = '/static/'


# ─── Redirections login/logout ────────────────────────────────────────────────

# Quand on essaie d'accéder à une page protégée sans être connecté,
# Django redirige vers /login/ automatiquement
LOGIN_URL = '/login/'

# Après une connexion réussie → aller sur le dashboard
LOGIN_REDIRECT_URL = '/dashboard/'

# Après une déconnexion → retourner sur le login
LOGOUT_REDIRECT_URL = '/login/'

# Type d'ID auto-incrémenté par défaut pour les modèles
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
