"""
apps.py — Configuration de l'application Django "alertes".

Ce fichier est requis par Django pour reconnaître notre application.
On ne le modifie presque jamais — il sert juste à déclarer que
l'application s'appelle "alertes" et à configurer quelques options
par défaut comme le type d'ID utilisé pour les clés primaires.
"""
from django.apps import AppConfig


class AlertesConfig(AppConfig):
    # Type de clé primaire auto-incrémentée par défaut pour tous les modèles
    # BigAutoField = entier 64 bits → peut stocker jusqu'à 9 milliards d'alertes
    default_auto_field = 'django.db.models.BigAutoField'

    # Nom de l'application — doit correspondre au dossier "alertes/"
    # et à ce qu'on a mis dans INSTALLED_APPS dans settings.py
    name = 'alertes'
