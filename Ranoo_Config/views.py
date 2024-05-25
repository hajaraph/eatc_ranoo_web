from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from Clients.communes import Commune, Region
from Facturation.models import Tarif, Taxe
from Login.models import Utilisateur, Role, Initial
from Login.views import authentification_requis, role_requis


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def config_utilisateur(request):
    titre = 'Ranoo Config | Utilisateur'
    active = 'active'
    font = 'custom-font'
    data = Initial.objects.all()

    contexte = {
        'titre_ranoo_utilisateur': titre,
        'active_utilisateur': active,
        'font_rano': font,
        'utilisateur': data
    }
    return render(request, 'all_page/ranoo_config/content.html', contexte)


class NouvelUtilisateur(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        titre = 'Parametre | Utilisateur | Crée un compte'
        active = 'active'
        font = 'custom-font'
        # Pour exclure le role si ce n'est pas un administrateur qui creer le compte
        if request.session.get('role_utilisateur') == 'Administrateur':
            role = Role.objects.all()
        else:
            role = Role.objects.all().exclude(role='Administrateur')

        regions = Region.objects.all()
        contexte = {
            'titre_creation_utilisateur': titre,
            'active_utilisateur': active,
            'font_rano': font,
            'role': role,
            'regions': regions
        }
        return render(request, 'all_page/ranoo_config/content.html', contexte)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        nom_utilisateur = request.POST['nom_utilisateur']
        prenom_utilisateur = request.POST['prenom_utilisateur']
        num_utilisateur = request.POST['num_utilisateur']
        motpasse_utilisateur = request.POST['motpasse_utilisateur']
        confirm_motpasse_utilisateur = request.POST['confirm_motpasse_utilisateur']
        role_id = int(request.POST['role_id'])

        num_exist = Utilisateur.objects.filter(num_utilisateur=num_utilisateur).exists()
        if not num_exist:

            if motpasse_utilisateur == confirm_motpasse_utilisateur:

                if role_id == 1 or role_id == 2:
                    utilisateur_cree = Utilisateur.objects.create(
                        nom_utilisateur=nom_utilisateur,
                        prenom_utilisateur=prenom_utilisateur,
                        num_utilisateur=num_utilisateur,
                        password=make_password(motpasse_utilisateur),
                        role_id=role_id
                    )

                else:
                    cp_commune = request.POST['commune']
                    utilisateur_cree = Utilisateur.objects.create(
                        nom_utilisateur=nom_utilisateur,
                        prenom_utilisateur=prenom_utilisateur,
                        num_utilisateur=num_utilisateur,
                        password=make_password(motpasse_utilisateur),
                        cp_commune_id=cp_commune,
                        role_id=role_id
                    )
                Initial.objects.create(
                    utilisateur_createur_id=request.session.get('id_utilisateur'),
                    utilisateur_cree_id=utilisateur_cree.pk
                )

                messages.success(request, f"Utilisateur crée avec succès !")
                return redirect('config_utilisateur')

            else:
                messages.error(request, f'Votre mot de passe ne se correspond pas à la confirmation !')

        else:
            messages.error(request, f'Votre numéro est déjà utilisé !')
        return redirect('creation_compte')


class UtilisateurMod(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request, pk):
        active = 'active'
        font = 'custom-font'

        utilisateur = get_object_or_404(Utilisateur, pk=pk)
        if request.session.get('role_utilisateur') == 'Administrateur':
            role = Role.objects.all()
        else:
            role = Role.objects.all().exclude(role='Administrateur')

        regions = Region.objects.all()
        titre = f'Rano Config | Modifier | {utilisateur.nom_utilisateur} {utilisateur.prenom_utilisateur}'
        data = {
            'titre_mod_utilisateur': titre,
            'active_utilisateur': active,
            'font_rano': font,
            'utilisateur': utilisateur,
            'role': role,
            'regions': regions
        }
        return render(request, 'all_page/ranoo_config/content.html', data)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        nom_utilisateur = request.POST['nom_utilisateur']
        prenom_utilisateur = request.POST['prenom_utilisateur']
        num_utilisateur = request.POST['num_utilisateur']
        motpasse_utilisateur = request.POST['motpasse_utilisateur']
        confirm_motpasse_utilisateur = request.POST['confirm_motpasse_utilisateur']
        statut = True if request.POST.getlist('status_utilisateur') else False
        role_id = request.POST['role_id']
        utilisateur = get_object_or_404(Utilisateur, pk=pk)

        if request.session.get('role_utilisateur') == 'Administrateur':
            if motpasse_utilisateur and confirm_motpasse_utilisateur:
                if motpasse_utilisateur == confirm_motpasse_utilisateur:
                    utilisateur.password = make_password(motpasse_utilisateur)
                else:
                    messages.error(request, f'Votre mot de passe ne se correspond pas à la confirmation !')
                    return redirect('utilisateur_modifier', pk)

        utilisateur.nom_utilisateur = nom_utilisateur
        utilisateur.prenom_utilisateur = prenom_utilisateur
        utilisateur.num_utilisateur = num_utilisateur
        utilisateur.statut = statut
        utilisateur.role_id = role_id
        utilisateur.save()
        messages.success(request, f"L'utilisateur {nom_utilisateur} {prenom_utilisateur} a été modifier avec succès !")
        return redirect('config_utilisateur')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def sup_utilisateur(request, pk):
    utilisateur = Utilisateur.objects.get(pk=pk)
    utilisateur_supprimer = f"{utilisateur.nom_utilisateur} {utilisateur.prenom_utilisateur}"
    try:
        utilisateur.delete()
        messages.success(request, f"L'utilisateur {utilisateur_supprimer} a été supprimer avec succès !")
    except ProtectedError:
        messages.warning(request, f"Vous ne pouvez pas supprimer cette utilisateur car il a déjà fais des tâche !")
    return redirect('config_utilisateur')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def config_tarif(request):
    titre = 'Ranoo Config | Tarif'
    active = 'active'
    font = 'custom-font'
    tarif = Tarif.objects.all().order_by('cp_commune__region__region', 'cp_commune__commune')
    context = {
        'titre_config_tarif': titre,
        'active_config_constates': active,
        'font_rano': font,
        'tarif': tarif
    }
    return render(request, 'all_page/ranoo_config/content.html', context)


class TarifNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        titre = 'Ranoo Config | Tarif | Nouveau'
        active = 'active'
        font = 'custom-font'
        commune = Commune.objects.order_by('region', 'commune').exclude(communes__isnull=False)
        context = {
            'titre_new_tarif': titre,
            'active_config_constates': active,
            'font_rano': font,
            'communes': commune
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        cp_commune = request.POST['cp_commune']
        prix_m3 = float(request.POST['prix_m3'])
        nom_taxes = request.POST.getlist('nom_taxe')
        taux_taxes = [float(taux) for taux in request.POST.getlist('taux_taxe')]
        tva = float(request.POST['tva'])
        nb_jour_echeance_fct = int(request.POST['nb_jour_echeance_fct'])
        tarif = Tarif.objects.create(
            cp_commune_id=cp_commune,
            prix_m3=round(prix_m3, 2),
            tva=round(tva, 2),
            nb_jour_echeance_fct=nb_jour_echeance_fct,
        )
        for nom_taxe, taux_taxe in zip(nom_taxes, taux_taxes):
            Taxe.objects.create(
                nom_taxe=nom_taxe,
                taux_taxe=round(float(taux_taxe), 2),
                tarif_id=tarif.pk
            )
        messages.success(request, f'Enregistré avec succès !')
        return redirect('config_tarif')


class TarifMod(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request, pk):
        titre = 'Ranoo Config | Tarif Modifier'
        active = 'active'
        font = 'custom-font'
        tarif = Tarif.objects.get(pk=pk)
        taxes = tarif.taxes.all()
        context = {
            'titre_mod_tarif': titre,
            'active_config_constates': active,
            'font_rano': font,
            'tarif': tarif,
            'taxes': taxes
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        prix_m3 = float(request.POST['prix_m3'])
        nom_taxes = request.POST.getlist('nom_taxe')
        taux_taxes = request.POST.getlist('taux_taxe')
        nb_jour_echeance_fct = int(request.POST['nb_jour_echeance_fct'])
        tva = float(request.POST['tva'])

        tarif = Tarif.objects.get(pk=pk)
        tarif.prix_m3 = round(prix_m3, 2)
        tarif.tva = round(tva, 2)
        tarif.nb_jour_echeance_fct = nb_jour_echeance_fct
        tarif.save()

        exist_taxes = {taxe.nom_taxe: taxe for taxe in tarif.taxes.all()}
        new_taxes = []

        for nom, taux in zip(nom_taxes, taux_taxes):
            taux = round(float(taux), 2)
            if nom in exist_taxes:
                taxe = exist_taxes[nom]
                taxe.taux_taxe = taux
                taxe.save()
            else:
                taxe = Taxe.objects.create(nom_taxe=nom, taux_taxe=taux, tarif=tarif)
            new_taxes.append(taxe)

        # Supprimer les taxes qui ne sont plus présentes dans le formulaire
        for nom in exist_taxes:
            if nom not in nom_taxes:
                exist_taxes[nom].delete()

        messages.success(request, f'Mofication de Tarif enregistré avec succès !')
        return redirect('config_tarif')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def region(request):
    titre = 'Ranoo Config | Région'
    active = 'active'
    font = 'custom-font'
    commune = Commune.objects.all()
    context = {
        'titre_region': titre,
        'active_region': active,
        'font_rano': font,
        'communes': commune
    }
    return render(request, 'all_page/ranoo_config/content.html', context)


class CommuneNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        titre = 'Ranoo Config | Région | Nouveau Département'
        active = 'active'
        font = 'custom-font'
        regions = Region.objects.order_by('region').all()
        context = {
            'titre_departement': titre,
            'active_region': active,
            'font_rano': font,
            'regions': regions
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        regions = request.POST['region']
        commune = request.POST['commune']
        cp_commune = request.POST['cp_commune']
        code = Commune.objects.filter(pk=cp_commune)
        if code.exists():
            code = Commune.objects.get(pk=cp_commune)
            messages.warning(request, f'Le code postal {code.cp_commune} est déjà utilisé !')
            return redirect('commune_new')
        else:
            Commune.objects.create(
                cp_commune=cp_commune,
                commune=commune,
                region_id=regions
            )
            messages.success(request, f'Enregistrer avec succès !')
            return redirect('region')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def supp_commune(request, pk):
    commune = Commune.objects.get(pk=pk)
    commune.delete()
    messages.success(request, 'Supprimer avec succès !')
    return redirect('region')
