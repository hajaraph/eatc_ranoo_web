from django.contrib import messages
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from Acommune.models import Region, Province
from Clients.models import TypeClient
from Facturation.models import Tarif, Taxe
from Ranoo_Config.models import ConfigBranchement
from Tenants.middleware import schema_use, SchemaAwareView
from Tenants.models import Utilisateur, Role, Initial
from Login.views import role_requis


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


class NouvelUtilisateur(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
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
        return render(request, self.template_name, contexte)

    @staticmethod
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


class UtilisateurMod(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk):
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
        return render(request, self.template_name, data)

    @staticmethod
    @role_requis('Administrateur')
    def post(request, pk):
        utilisateur = get_object_or_404(Utilisateur, pk=pk)
        
        # Récupération des données du formulaire
        nom_utilisateur = request.POST.get('nom_utilisateur')
        prenom_utilisateur = request.POST.get('prenom_utilisateur')
        num_utilisateur = request.POST.get('num_utilisateur')
        motpasse_utilisateur = request.POST.get('motpasse_utilisateur')
        confirm_motpasse_utilisateur = request.POST.get('confirm_motpasse_utilisateur')
        statut = bool(request.POST.get('status_utilisateur', False))
        role_id = request.POST.get('role_id')

        # Gestion du mot de passe
        if motpasse_utilisateur and confirm_motpasse_utilisateur:
            if motpasse_utilisateur != confirm_motpasse_utilisateur:
                messages.error(request, 'Les mots de passe ne correspondent pas.')
                return redirect('utilisateur_modifier', pk)
                
            if len(motpasse_utilisateur) < 8:
                messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
                return redirect('utilisateur_modifier', pk)

            utilisateur.password = motpasse_utilisateur

        # Mise à jour des informations de l'utilisateur
        utilisateur.nom_utilisateur = nom_utilisateur
        utilisateur.prenom_utilisateur = prenom_utilisateur
        utilisateur.num_utilisateur = num_utilisateur
        utilisateur.statut = statut
        utilisateur.role_id = role_id
        
        try:
            utilisateur.save()
            messages.success(request, f"L'utilisateur {nom_utilisateur} {prenom_utilisateur} a été modifié avec succès !")
            return redirect('config_utilisateur')
            
        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de la modification : {str(e)}")
            return redirect('utilisateur_modifier', pk)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def sup_utilisateur(request, pk):
    try:
        utilisateur = Utilisateur.objects.get(pk=pk)
        utilisateur_supprimer = f"{utilisateur.nom_utilisateur} {utilisateur.prenom_utilisateur}"
        utilisateur.delete()

        messages.success(request, f"L'utilisateur {utilisateur_supprimer} a été supprimer avec succès !")
    except ProtectedError:
        messages.warning(request, f"Vous ne pouvez pas supprimer cette utilisateur car il a déjà fais des tâche !")
    return redirect('config_utilisateur')


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


class BranchementConfig(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        titre = 'Ranoo Config | Branchement | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'titre_new_branchement': titre,
            'active_branchement': active,
            'font_rano': font,
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        nom_branchement = request.POST['branchement']
        tva_applique = request.POST.get('tva_applique') == 'on'
        taxe_applique = request.POST.get('taxe_applique') == 'on'

        if not TypeClient.objects.filter(designation_client=nom_branchement).exists():
            type_client = TypeClient.objects.create(
                designation_client=nom_branchement
            )
            ConfigBranchement.objects.create(
                type_client=type_client,
                tva_applique=tva_applique,
                taxe_applique=taxe_applique,
            )
            messages.success(request, f'Enregistré avec succès !')
            return redirect('branchement')
        else:
            messages.warning(request, f'Ce branchement exist déjà !')
            return redirect('branchement_nouveau')



@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def get_branchement_list(request):
    configs = (ConfigBranchement.objects.all().order_by('type_client__designation_client')
               .values('id_config_branchement', 'type_client__designation_client'))

    return JsonResponse({'configs': list(configs)})


class BranchementMod(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk):
        try:
            branchement_obj = get_object_or_404(ConfigBranchement, pk=pk)
            titre = f'Ranoo Config | Branchement | Modification de {branchement_obj.type_client.designation_client}'
            active = 'active'
            font = 'custom-font'
            context = {
                'titre_branchement_mod': titre,
                'active_branchement': active,
                'font_rano': font,
                'branchement': branchement_obj
            }
            return render(request, self.template_name, context)
        except ConfigBranchement.DoesNotExist:
            messages.error(request, f"Ce branchement n'exist pas !")
            return redirect('branchement')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        designation_client = request.POST['branchement']
        tva_applique = request.POST.get('tva_applique') == 'on'
        taxe_applique = request.POST.get('taxe_applique') == 'on'

        try:
            branchement_obj = get_object_or_404(ConfigBranchement, pk=pk)
            branchement_obj.type_client.designation_client = designation_client
            branchement_obj.type_client.save()
            branchement_obj.tva_applique = tva_applique
            branchement_obj.taxe_applique = taxe_applique
            branchement_obj.save()

            messages.success(request, f"{branchement_obj.type_client.designation_client} modifié avec succès !")
            return redirect('branchement')
        except ConfigBranchement.DoesNotExist:
            messages.error(request, f"Ce branchement n'exist pas !")
            return redirect('branchement')


@role_requis('Administrateur')
def branchement_supp(request, pk):
    try:
        branchement_obj = get_object_or_404(TypeClient, pk=pk)
        designation_client = branchement_obj.designation_client
        branchement_obj.delete()

        messages.success(request, f"{designation_client} supprimé avec succès !")
    except ProtectedError:
        messages.warning(request, f"Ce branchement est déjà utilise par des clients !")

    return redirect('branchement')


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


class TarifNew(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
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
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
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


class TarifMod(SchemaAwareView):

    template_name = 'all_page/ranoo_config/content.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk):
        titre = 'Ranoo Config | Tarif Modifier'
        active = 'active'
        font = 'custom-font'
        tarif = Tarif.objects.get(pk=pk)
        taxes = tarif.taxes.all()
        branchements = ConfigBranchement.objects.all()
        
        # Créer un dictionnaire des prix par type de branchement pour un accès facile
        prix_par_branchement = {}
        for item in tarif.prix_m3:
            try:
                branchementc = ConfigBranchement.objects.get(pk=item['id'])
                prix_par_branchement[branchementc.id_config_branchement] = item['prix']
            except ConfigBranchement.DoesNotExist:
                continue
        
        context = {
            'titre_mod_tarif': titre,
            'active_config_constates': active,
            'font_rano': font,
            'tarif': tarif,
            'taxes': taxes,
            'branchements': branchements,
            'prix_par_branchement': prix_par_branchement
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        try:
            # Récupération des données du formulaire
            conso_tva_app = float(request.POST.get('conso_tva_app', 0)) or 0
            tva = float(request.POST.get('tva', 0)) or 0
            nom_taxes = request.POST.getlist('nom_taxe')
            taux_taxes = [taux for taux in request.POST.getlist('taux_taxe') if taux]
            nb_jour_echeance_fct = int(request.POST.get('nb_jour_echeance_fct', 15))
            prix_location_compteur = request.POST.get('prix_location_compteur', 0) or 0

            # Récupérer les prix par type de branchement
            prix_m3 = []
            for branchementc in ConfigBranchement.objects.all():
                prix = request.POST.get(f'prix_m3_{branchementc.id_config_branchement}')
                if prix is not None:  # Vérifier si le champ existe
                    try:
                        prix_float = float(prix)
                        prix_m3.append({
                            "id": branchementc.id_config_branchement,
                            "prix": round(prix_float, 2)
                        })
                    except (ValueError, TypeError):
                        # En cas d'erreur de conversion, on utilise 0 comme valeur par défaut
                        prix_m3.append({
                            "id": branchementc.id_config_branchement,
                            "prix": 0.0
                        })

            # Mise à jour du tarif
            tarif = Tarif.objects.get(pk=pk)
            tarif.prix_m3 = prix_m3
            tarif.tva = round(tva, 2)
            tarif.conso_tva_app = round(conso_tva_app, 2)
            tarif.nb_jour_echeance_fct = nb_jour_echeance_fct
            tarif.prix_location_compteur = prix_location_compteur
            tarif.save()

            # Gestion des taxes existantes
            exist_taxes = {taxe.id_taxe: taxe for taxe in tarif.taxes.all()}
            updated_tax_ids = []

            # Mise à jour ou création des taxes
            for nom, taux_str in zip(nom_taxes, taux_taxes):
                if not nom:  # Ignorer les champs vides
                    continue
                    
                try:
                    taux = round(float(taux_str), 2)
                    # Vérifier si une taxe avec ce nom existe déjà
                    existing_tax = next((t for t in exist_taxes.values() if t.nom_taxe == nom), None)
                    
                    if existing_tax:
                        # Mise à jour de la taxe existante
                        existing_tax.taux_taxe = taux
                        existing_tax.save()
                        updated_tax_ids.append(existing_tax.id_taxe)
                    else:
                        # Création d'une nouvelle taxe
                        new_tax = Taxe.objects.create(
                            nom_taxe=nom,
                            taux_taxe=taux,
                            tarif=tarif
                        )
                        updated_tax_ids.append(new_tax.id_taxe)
                except (ValueError, TypeError) as e:
                    # Ignorer les valeurs de taxe invalides
                    print(f"Erreur lors de la gestion de la taxe: {str(e)}")
                    continue

            # Supprimer les taxes qui ne sont plus dans le formulaire
            for taxe_id, taxe in exist_taxes.items():
                if taxe_id not in updated_tax_ids:
                    taxe.delete()

            messages.success(request, 'Modification du tarif enregistrée avec succès !')
            return redirect('config_tarif')
            
        except Tarif.DoesNotExist:
            messages.error(request, 'Le tarif spécifié n\'existe pas.')
            return redirect('config_tarif')
        except Exception as e:
            messages.error(request, f'Une erreur est survenue lors de la modification du tarif: {str(e)}')
            return redirect('config_tarif')
