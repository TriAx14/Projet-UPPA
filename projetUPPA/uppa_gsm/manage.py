#!/usr/bin/env python3
"""
Point d'entrée de Django — c'est ce fichier qu'on appelle
quand on tape "python3 manage.py runserver" ou "python3 manage.py migrate".
On ne le modifie jamais, il sert juste à lancer les commandes Django.
"""
import os
import sys


def main():
    # On dit à Django quel fichier de configuration utiliser
    # ici c'est uppa_gsm/settings.py
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uppa_gsm.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Si Django n'est pas installé, on affiche un message clair
        raise ImportError(
            "Django n'est pas installé. Lance : "
            "pip install django --break-system-packages"
        ) from exc

    # Exécute la commande passée en argument (runserver, migrate, etc.)
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
