from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.views import View
from openpyxl.workbook import Workbook

from Login.models import Utilisateur
from Login.views import authentification_requis, role_requis, deconnexion
from Parametre.models import Historique


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def para_utilisateur(request):
    titre = 'Parametre | Profile'
    active = 'active'
    font = 'custom-font'
    contexte = {
        'titre_utilisateur': titre,
        'active_utilisateur': active,
        'font_parametre': font
    }
    return render(request, 'all_page/parametre/parametre.html', contexte)


class ProfileModifier(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        titre = 'Parametre | Profile'
        active = 'active'
        font = 'custom-font'
        contexte = {
            'titre_profile': titre,
            'active_utilisateur': active,
            'font_parametre': font
        }
        return render(request, 'all_page/parametre/parametre.html', contexte)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        utilisateur = Utilisateur.objects.get(pk=request.session.get('id_utilisateur'))
        num_utilisateur = utilisateur.num_utilisateur

        utilisateur.nom_utilisateur = request.POST.get('nom_utilisateur')
        utilisateur.prenom_utilisateur = request.POST.get('prenom_utilisateur')
        utilisateur.num_utilisateur = request.POST.get('num_utilisateur')

        if request.FILES.get('photo_utilisateur'):
            utilisateur.photo_utilisateur = request.FILES.get('photo_utilisateur')
        else:
            utilisateur.photo_utilisateur.delete()

        if num_utilisateur != request.POST.get('num_utilisateur'):
            if Utilisateur.objects.filter(num_utilisateur=request.POST.get('num_utilisateur')).exists():
                messages.error(request, 'Numéro déjà utilisé par un autre utilisateur !')
                return redirect('profile_modifier')
            else:
                utilisateur.save()
                deconnexion(request)
        else:
            utilisateur.save()
            request.session['nom_utilisateur'] = request.POST.get('nom_utilisateur')
            request.session['prenom_utilisateur'] = request.POST.get('prenom_utilisateur')
            request.session['photo_utilisateur'] = utilisateur.photo_utilisateur.url if utilisateur.photo_utilisateur else None
            messages.success(request, 'Modification de Profile effectuer avec succès !')

        return redirect('para_utilisateur')


@authentification_requis
@role_requis('Administrateur')
def historique(request):
    titre = 'Parametre | Historique'
    active = 'active'
    font = 'custom-font'
    histo = Historique.objects.all()
    contexte = {
        'titre_historique': titre,
        'active_historique': active,
        'font_parametre': font,
        'historique': histo
    }
    return render(request, 'all_page/parametre/parametre.html', contexte)


class ChangerMotdePasse(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        titre = 'Parametre | Profile | Changer Mot de Passe'
        active = 'active'
        font = 'custom-font'
        contexte = {
            'titre_motde_passe': titre,
            'active_motde_passe': active,
            'font_parametre': font
        }
        return render(request, 'all_page/parametre/parametre.html', contexte)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        ancien_motpasse = request.POST.get('ancien_motpasse')
        nouveau_motpasse = request.POST.get('nouveau_motpasse')
        confirmer_motpasse = request.POST.get('confirmer_motpasse')

        utilisateur = Utilisateur.objects.get(pk=request.session.get('id_utilisateur'))
        if check_password(ancien_motpasse, utilisateur.motpasse_utilisateur):
            if nouveau_motpasse == confirmer_motpasse:
                utilisateur.password = make_password(nouveau_motpasse)
                utilisateur.save()
                messages.success(request, 'Mot de passe changer avec succès !')
                return redirect('para_utilisateur')
            else:
                messages.error(request, f'Votre mot de passe ne se correspond pas à la confirmation !')
                return redirect('changer_motde_passe')
        else:
            messages.error(request, 'Ancien mot de passe incorrect !')
            return redirect('changer_motde_passe')


def enregistre_historique(request, contexte, utilisateur_id):
    Historique.objects.create(
        type_historique=contexte,
        utilisateur_id=utilisateur_id
    )


def exporter_en_excel(queryset, nom_fichier, champs, nom_colonnes):
    # Récupérer les données
    data = queryset.values_list(*champs)

    # Créer le classeur et la feuille de calcul
    wb = Workbook()
    ws = wb.active

    # Ajouter les données à la feuille de calcul
    ws.append(nom_colonnes)
    for row in data:
        ws.append(row)

    # Enregistrer le classeur dans un buffer
    import io
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Renvoyer le buffer en tant que réponse HTTP
    response = FileResponse(buffer, as_attachment=True, filename=nom_fichier)
    return response
