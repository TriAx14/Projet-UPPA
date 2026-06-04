"""
models.py — Structure de la base de données SQLite pour les alertes GSM.

Dans Django, un "modèle" c'est une classe Python qui correspond à une table
dans la base de données. Quand on lance "python3 manage.py migrate", Django
lit ce fichier et crée automatiquement la table correspondante dans db.sqlite3.

Ici on a une seule table : AlerteGSM, qui garde un historique de toutes
les alertes déclenchées par le module GSM.
"""
from django.db import models


class AlerteGSM(models.Model):
    """
    Une ligne dans cette table = une alerte GSM déclenchée.

    Chaque fois que gsm_alertes.py détecte un dépassement de seuil
    et passe les appels, il envoie les infos à Django qui les stocke ici.
    On peut ensuite les voir dans le dashboard et l'historique.
    """

    # Le code court du capteur tel qu'il est dans config.json
    # ex: "frigo1", "frigo2", "ambiance"
    capteur = models.CharField(max_length=50)

    # Le nom lisible du capteur pour l'affichage dans l'interface
    # ex: "Réfrigérateur 1", "Température ambiante"
    nom_capteur = models.CharField(max_length=100)

    # La température mesurée au moment où l'alerte s'est déclenchée
    # FloatField = nombre décimal, parfait pour des températures comme -75.3°C
    temperature = models.FloatField()

    # Description de ce qui s'est passé
    # ex: "SEUIL MAX DÉPASSÉ (mesure : -55.0°C / seuil : -60.0°C)"
    type_alerte = models.CharField(max_length=200)

    # Date et heure exacte de l'alerte
    # auto_now_add=True → Django remplit cette valeur automatiquement
    # à la création, on n'a pas besoin de la passer manuellement
    date_alerte = models.DateTimeField(auto_now_add=True)

    # Combien d'appels ont été passés pour cette alerte (max 3 par défaut)
    tentatives = models.IntegerField(default=0)

    # L'alerte est-elle encore en cours ou a-t-elle été résolue ?
    # On utilise une liste de choix pour éviter les valeurs incorrectes
    STATUTS = [
        ('active', 'Active'),   # température encore anormale ou non acquittée
        ('resolue', 'Résolue'), # l'opérateur a marqué l'alerte comme traitée
    ]
    statut = models.CharField(max_length=20, choices=STATUTS, default='active')

    class Meta:
        # Par défaut, les alertes sont triées du plus récent au plus ancien
        # Le "-" devant date_alerte signifie "ordre décroissant"
        ordering = ['-date_alerte']

        # Noms affichés dans l'interface d'administration Django
        verbose_name        = "Alerte GSM"
        verbose_name_plural = "Alertes GSM"

    def __str__(self):
        # Ce que Django affiche quand il représente une alerte en texte
        # Utile dans l'interface /admin/ par exemple
        return f"{self.nom_capteur} — {self.temperature}°C — {self.date_alerte}"
