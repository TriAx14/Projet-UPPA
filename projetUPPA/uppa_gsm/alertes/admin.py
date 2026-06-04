"""
admin.py — Enregistrement des modèles dans l'interface d'administration Django.

L'interface /admin/ est une interface web intégrée à Django qui permet de
voir et modifier directement les données en base sans écrire de code.
Accessible sur http://IP:8001/admin/ avec le compte uppaadmin.
"""
from django.contrib import admin
from .models import AlerteGSM


@admin.register(AlerteGSM)
class AlerteGSMAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des alertes dans /admin/.
    Sans cette classe, les alertes seraient accessibles dans /admin/
    mais avec un affichage par défaut peu lisible.
    """

    # Colonnes affichées dans la liste des alertes
    list_display = ['nom_capteur', 'temperature', 'type_alerte', 'date_alerte', 'statut']

    # Filtres disponibles dans la barre latérale droite
    # Permet de filtrer rapidement par statut ou par capteur
    list_filter = ['statut', 'capteur']

    # Champ de recherche — on peut chercher par nom de capteur ou type d'alerte
    search_fields = ['nom_capteur', 'type_alerte']
