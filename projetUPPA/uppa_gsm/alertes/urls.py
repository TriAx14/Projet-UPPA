"""
urls.py (alertes) — Routes de l'application alertes.

Ce fichier fait le lien entre les URLs que l'utilisateur tape dans
son navigateur et les fonctions Python de views.py qui les traitent.
C'est comme un annuaire : URL → fonction.
"""
from django.urls import path
from . import views

urlpatterns = [

    # La racine "/" redirige automatiquement vers le dashboard
    # Si quelqu'un tape juste l'IP sans préciser de page, il atterrit sur /dashboard/
    path('', lambda request: __import__(
        'django.shortcuts', fromlist=['redirect']
    ).redirect('dashboard'), name='index'),

    # ── Pages principales ────────────────────────────────────────────────────

    # /dashboard/ → vue dashboard (page d'accueil après login)
    path('dashboard/', views.dashboard, name='dashboard'),

    # /historique/ → vue historique (toutes les alertes avec filtres)
    path('historique/', views.historique, name='historique'),

    # /configuration/ → vue configuration (modifier les seuils)
    path('configuration/', views.configuration, name='configuration'),

    # ── Actions ──────────────────────────────────────────────────────────────

    # /test-appel/ → déclenche un appel de test (appelé en JavaScript)
    path('test-appel/', views.test_appel, name='test_appel'),

    # ── API interne ───────────────────────────────────────────────────────────

    # /api/alerte/ → reçoit les alertes depuis gsm_alertes.py (POST JSON)
    path('api/alerte/', views.api_alerte, name='api_alerte'),

    # /api/resoudre/42/ → marque l'alerte n°42 comme résolue
    # <int:alerte_id> → Django capture l'ID dans l'URL et le passe à la vue
    path('api/resoudre/<int:alerte_id>/', views.api_resoudre_alerte, name='api_resoudre'),
]
