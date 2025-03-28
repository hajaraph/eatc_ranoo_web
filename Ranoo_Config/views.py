from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from Acommune.models import Region, Province
from Clients.models import TypeClient
from Facturation.models import Tarif, Taxe
from Ranoo_Config.models import ConfigBranchement
from Tenants.middleware import schema_use
from Tenants.models import Utilisateur, Role, Initial
from Login.views import authentification_requis, role_requis


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def config_utilisateur(request):
    titre = 'Ranoo Config | Utilisateur'
    active = 'active'
    font = 'custom-font'
    data = Initial.objects.filter(utilisateur_cree__entreprise_id=request.session.get('entreprise'))

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
    @schema_use
    def get(request):
        titre = 'Parametre | Utilisateur | Crée un compte'
        active = 'active'
        font = 'custom-font'
        # Pour exclure le role si ce n'est pas un administrateur qui creer le compte
        if request.session.get('role_utilisateur') == 'Administrateur':
            role = Role.objects.all().order_by('role')
        else:
            role = Role.objects.all().order_by('role').exclude(role='Administrateur')

        provinces = Province.objects.all().order_by('province')
        contexte = {
            'titre_creation_utilisateur': titre,
            'active_utilisateur': active,
            'font_rano': font,
            'role': role,
            'provinces': provinces
        }
        return render(request, 'all_page/ranoo_config/content.html', contexte)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
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
                utilisateur_connecte = Utilisateur.objects.get(id_utilisateur=request.session.get('id_utilisateur'))
                utilisateur_data = {
                    'nom_utilisateur': nom_utilisateur,
                    'prenom_utilisateur': prenom_utilisateur,
                    'num_utilisateur': num_utilisateur,
                    'password': motpasse_utilisateur,  # On passe le mot de passe brut ici
                    'entreprise_id': request.session.get('entreprise'),
                    'role_id': role_id
                }
                if role_id not in [1, 2]:
                    utilisateur_data['cp_commune_id'] = request.POST['commune']

                utilisateur_cree = Utilisateur(**utilisateur_data)
                utilisateur_cree.save(utilisateur_createur=utilisateur_connecte)

                messages.success(request, f"Utilisateur créé avec succès !")
                return redirect('config_utilisateur')
            else:
                messages.error(request, f'Votre mot de passe ne correspond pas à la confirmation !')
        else:
            messages.error(request, f'Votre numéro est déjà utilisé !')
        return redirect('nouvel_utilisateur')


class UtilisateurMod(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
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
    @schema_use
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
@schema_use
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
@schema_use
def branchement(request):
    titre = 'Ranoo Config | Branchement'
    active = 'active'
    font = 'custom-font'
    branchement_list = ConfigBranchement.objects.all().order_by('type_client__designation_client')
    context = {
        'titre_branchement': titre,
        'active_branchement': active,
        'font_rano': font,
        'branchement': branchement_list
    }
    return render(request, 'all_page/ranoo_config/content.html', context)


class BrenchementConfig(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def get(request):
        titre = 'Ranoo Config | Branchement | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'titre_new_branchement': titre,
            'active_branchement': active,
            'font_rano': font,
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def post(request):
        nom_branchement = request.POST['branchement']
        tva_applique = request.POST.get('tva_applique') == 'on'

        if not TypeClient.objects.filter(designation_client=nom_branchement).exists():
            type_client = TypeClient.objects.create(
                designation_client=nom_branchement
            )
            ConfigBranchement.objects.create(
                type_client=type_client,
                tva_applique=tva_applique,
            )
            messages.success(request, f'Enregistré avec succès !')
            return redirect('branchement')
        else:
            messages.warning(request, f'Ce branchement exist déjà !')
            return redirect('branchement_nouveau')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def get_branchement_list(request):
    configs = (ConfigBranchement.objects.all().order_by('type_client__designation_client')
               .values('id_config_branchement', 'type_client__designation_client'))

    return JsonResponse({'configs': list(configs)})

@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def config_tarif(request):
    titre = 'Ranoo Config | Tarif'
    active = 'active'
    font = 'custom-font'
    tarif = Tarif.objects.all().order_by('cp_commune__region__province', 'cp_commune__region__region',
                                         'cp_commune__commune')

    # Créer un dictionnaire pour associer les ID de ConfigBranchement à leurs désignations
    config_dict = {config.id_config_branchement: config.type_client.designation_client
                   for config in ConfigBranchement.objects.all()}

    context = {
        'titre_config_tarif': titre,
        'active_config_constates': active,
        'font_rano': font,
        'tarif': tarif,
        'config_dict': config_dict  # Ajouter le dictionnaire au contexte
    }
    return render(request, 'all_page/ranoo_config/content.html', context)


class TarifNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def get(request):
        titre = 'Ranoo Config | Tarif | Nouveau'
        active = 'active'
        font = 'custom-font'
        provinces = Province.objects.all().order_by('province')
        context = {
            'titre_new_tarif': titre,
            'active_config_constates': active,
            'font_rano': font,
            'provinces': provinces
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def post(request):
        cp_commune = request.POST['commune']
        conso_tva_app = float(request.POST['conso_tva_app']) if request.POST['conso_tva_app'] else 0
        tva = float(request.POST['tva']) if request.POST['tva'] else 0
        nb_jour_echeance_fct = int(request.POST['nb_jour_echeance_fct'])
        prix_location_compteur = request.POST['prix_location_compteur']

        prix_m3 = [
            {
                "id": branchements.id_config_branchement,
                "prix": round(float(request.POST.get(f'prix_m3_{branchements.id_config_branchement}', 0)), 2)
            }
            for branchements in ConfigBranchement.objects.all()
        ]

        tarif = Tarif.objects.create(
            cp_commune_id=cp_commune,
            prix_m3=prix_m3,
            tva=round(tva, 2),
            conso_tva_app=round(conso_tva_app, 2),
            nb_jour_echeance_fct=nb_jour_echeance_fct,
            prix_location_compteur=prix_location_compteur,
        )

        nom_taxes = request.POST.getlist('nom_taxe')
        taux_taxes = [taux for taux in request.POST.getlist('taux_taxe')]
        if nom_taxes != [''] and taux_taxes != ['']:
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
    @schema_use
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
    @schema_use
    def post(request, pk):
        prix_m3_bs = float(request.POST['prix_m3_bs'])
        prix_m3_bp = float(request.POST['prix_m3_bp'])
        prix_m3_k = float(request.POST['prix_m3_k'])
        conso_tva_app = float(request.POST['conso_tva_app'])
        nom_taxes = request.POST.getlist('nom_taxe')
        taux_taxes = request.POST.getlist('taux_taxe')
        nb_jour_echeance_fct = int(request.POST['nb_jour_echeance_fct'])
        tva = float(request.POST['tva'])

        tarif = Tarif.objects.get(pk=pk)
        tarif.prix_m3_bs = round(prix_m3_bs, 2)
        tarif.prix_m3_bp = round(prix_m3_bp, 2)
        tarif.prix_m3_k = round(prix_m3_k, 2)
        tarif.tva = round(tva, 2)
        tarif.conso_tva_app = round(conso_tva_app, 2)
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
