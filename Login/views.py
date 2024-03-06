from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views import View


from Login.models import Utilisateur, Initial


# Fonction decorateur pour verifie si un utilisateur et connecté ou pas avant d'acceder a un url
def authentification_requis(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('num_utilisateur'):
            messages.error(request, f"Veuillez vous connecté !")
            return redirect('authentification')
        return view_func(request, *args, **kwargs)

    return wrapper


# Fonction decorateur pour donné l'accès à un utilisateur
def role_requis(*role):
    def decorateur(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if request.session.get('role_utilisateur') in role:
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden("Vous n'avez pas la permission necessaire d'effectuer cette tâche !")

        return _wrapper_view

    return decorateur


class Authentification(View):
    @staticmethod
    def get(request):
        if request.session.get('num_utilisateur'):
            return redirect('tableau_bord')
        else:
            return render(request, 'login/login_page.html')

    @staticmethod
    def post(request):
        num_utilisateur = request.POST.get('num_utilisateur')
        motpasse_utilisateur = request.POST.get('motpasse_utilisateur')
        sauvegarder = request.POST.get('sauvegarder')

        try:
            utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
            if check_password(motpasse_utilisateur, utilisateur.password):
                if utilisateur.statut:
                    if utilisateur.role.role == 'Releveur':
                        messages.error(request, f"Vous n'avez pas l'autorisation de vous connecté ici !")
                        return redirect('authentification')
                    else:
                        initial = Initial.objects.get(utilisateur_cree=utilisateur.pk)

                        request.session['id_utilisateur'] = utilisateur.id_utilisateur
                        request.session['nom_utilisateur'] = utilisateur.nom_utilisateur
                        request.session['prenom_utilisateur'] = utilisateur.prenom_utilisateur
                        request.session['num_utilisateur'] = utilisateur.num_utilisateur
                        request.session['role_utilisateur'] = utilisateur.role.role
                        request.session['photo_utilisateur'] = utilisateur.photo_utilisateur.url \
                            if utilisateur.photo_utilisateur else None
                        request.session['initial_utilisateur'] = (initial.utilisateur_createur.nom_utilisateur +
                                                                  ' ' +
                                                                  initial.utilisateur_createur.prenom_utilisateur)
                        if sauvegarder:
                            # La session expirera lorsque l'utilisateur fermera son navigateur
                            request.session.set_expiry(None)
                        else:
                            # La session expirera immédiatement
                            request.session.set_expiry(0)

                    return redirect('tableau_bord')
                else:
                    messages.warning(request, f"Votre compte a été desactivé,"
                                              f" Veuillez contacter l'Administrateur !")
                    return redirect('authentification')
            else:
                messages.error(request, f'Mot de passe incorrect !')
                return redirect('authentification')
        except Utilisateur.DoesNotExist:
            messages.warning(request, f"Votre Compte n'exist pas !")
            return redirect('authentification')


def deconnexion(request):
    logout(request)
    return redirect('authentification')
