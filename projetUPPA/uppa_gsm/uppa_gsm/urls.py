"""
urls.py (principal) — C'est le routeur général du projet.

Quand une requête HTTP arrive sur le serveur, Django regarde ici
en premier pour savoir où l'envoyer. C'est comme un aiguillage.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect


def logout_view(request):
    """
    Vue de déconnexion personnalisée.

    On a dû la créer nous-mêmes car depuis Django 5, le logout
    nécessite une requête POST pour des raisons de sécurité.
    La vue par défaut de Django ne fonctionnait plus avec notre
    bouton de déconnexion dans la navbar.
    """
    logout(request)
    # Après déconnexion, on renvoie l'utilisateur vers la page de login
    return redirect('/login/')


urlpatterns = [

    # Interface d'administration Django intégrée
    # Accessible sur /admin/ — utile pour voir/modifier les données directement
    path('admin/', admin.site.urls),

    # Page de connexion — on utilise la vue intégrée de Django
    # mais on lui donne notre propre template HTML (login.html)
    path('login/', auth_views.LoginView.as_view(
        template_name='alertes/login.html'
    ), name='login'),

    # Page de déconnexion — notre vue personnalisée (voir ci-dessus)
    path('logout/', logout_view, name='logout'),

    # Toutes les autres URLs sont gérées par l'application "alertes"
    # Django va chercher dans alertes/urls.py pour la suite
    path('', include('alertes.urls')),
]
