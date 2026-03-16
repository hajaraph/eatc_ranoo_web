from collections import defaultdict
from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.db import models
from django.db.models import OuterRef, Subquery
from django.http import HttpResponse, JsonResponse
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from Acommune.models import Province, Commune
from Compteurs.models import Compteur, ReleveCompteur, CompteurPrincipale, ReleveCompteurPrincipale, AlerteConsommation, ParametreAlerte
from Clients.models import Contrat
from Facturation.models import Facture
from Facturation.views import facture_creation
from Login.views import role_requis
from Parametre.views import enregistre_historique, exporter_en_excel
from Tenants.middleware import schema_use, SchemaAwareView
from Rel_Compteur.utils import get_month_name_fr, filter_by_user_role, \
    get_3_months_range, get_month_range, filter_by_client_number
from Compteurs.models import ParametreAlerte


@schema_use
def compteur_liste(request):
    title = 'Compteurs | Liste'
    active = 'active'
    header = 'Liste Compteurs'
    font = 'custom-font'

    # Récupération des derniers relevés (hors rejetés)
    derniers_releves = ReleveCompteur.objects.filter(
        num_compteur_id=OuterRef('pk')
    ).exclude(statut_validation='REJETE').order_by('-date_releve')

    # Récupération des compteurs avec leurs contrats et clients associés
    compteurs_query = Compteur.objects.prefetch_related(
        models.Prefetch('contrats', queryset=Contrat.objects.select_related('client'))
    ).annotate(
        dernier_releve=Subquery(derniers_releves.values('date_releve')[:1])
    )

    # Application du filtre par rôle
    compteurs = filter_by_user_role(request, compteurs_query, 'contrats__cp_commune_id')
    
    # Conversion en liste et tri
    compteurs = list(compteurs.order_by('num_compteur'))

    compteurs.sort(key=lambda x: int(x.num_compteur))

    provinces = Province.objects.all().order_by('province')

    context = {
        'title_liste': title,
        'header_text': header,
        'active_li_co': active,
        'font_compteur': font,
        'compteur': compteurs,
        'client': Contrat.objects.all().order_by('client__num_client'),
        'provinces': provinces,
    }
    return render(request, 'all_page/compteurs/compteurs.html', context)


class CompteurNew(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Compteurs | Nouveau'
        active = 'active'
        font = 'custom-font'
        compteurs_principaux = CompteurPrincipale.objects.all()
        context = {
            'title_new': title,
            'active_li_co': active,
            'font_compteur': font,
            'compteurs_principaux': compteurs_principaux
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        num_compteur = request.POST['num_compteur']
        marque_compteur = request.POST['marque_compteur']
        modele_compteur = request.POST['modele_compteur']
        dn_compteur = request.POST['DN_compteur']
        origin_compteur = request.POST['origin_compteur']
        date_releve = request.POST['date_releve']
        volume = request.POST['volume']
        num_compteur_principale = request.POST.get('num_compteur_principale', '')

        # Vérifier si un compteur avec ce numéro existe déjà
        numero = Compteur.objects.filter(num_compteur=num_compteur)
        if numero.exists():
            messages.warning(request, f"Le compteur avec le numéro {num_compteur} est déjà enregistré !")
            return redirect('compteur_new')

        # Récupérer le compteur principal si sélectionné
        cp = None
        if num_compteur_principale:
            try:
                cp = CompteurPrincipale.objects.get(pk=num_compteur_principale)
            except CompteurPrincipale.DoesNotExist:
                pass
        
        Compteur.objects.create(
            num_compteur=num_compteur,
            marque_compteur=marque_compteur,
            modele_compteur=modele_compteur,
            DN_compteur=dn_compteur,
            origin_compteur=origin_compteur,
            num_compteur_principale=cp
        )
        ReleveCompteur.objects.create(
            date_releve=date_releve,
            volume=volume,
            conso=0,
            num_compteur_id=num_compteur,
            statut_validation='CONFIRME',
            valideur_id=request.session.get('id_utilisateur'),
            date_validation=timezone.now(),
            utilisateur_id=request.session.get('id_utilisateur')
        )
        # Historique
        message = f"Creation d'un compteur numéro {num_compteur}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, f"Compteur enregistré avec succès !")
        return redirect('compteur_list')


class CompteurDetail(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def get(self, request, pk):
        try:
            active = 'active'
            font = 'custom-font'
            compteur = Compteur.objects.get(pk=pk)
            releve = compteur.relevecompteurs.order_by('id_releve').all()
            contrat = compteur.contrats

            title = f'Compteurs | Detail de {compteur.num_compteur}'

            # Ajouter un champ image_exists pour chaque relevé
            for r in releve:
                r.image_exists = r.image_compteur and os.path.exists(r.image_compteur.path) if r.image_compteur else False

            compteurs_principaux = CompteurPrincipale.objects.all()

            context = {
                'title_detail': title,
                'active_li_co': active,
                'font_compteur': font,
                'detail': compteur,
                'releve': releve,
                'contrat': contrat.get().num_contrat if contrat.exists() else None,
                'client': contrat.get().client if contrat.exists() else None,
                'client_active': contrat.get().client.compte_actif if contrat.exists() else None,
                'compteurs_principaux': compteurs_principaux
            }
            return render(request, self.template_name, context)
        except Exception as e:
            messages.error(request, f"Une erreur est survenue sur le compteur : {e}")
            return redirect('compteur_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def post(request, pk):
        mod_compteur = Compteur.objects.get(pk=pk)
        marque_compteur = request.POST['marque_compteur']
        modele_compteur = request.POST['modele_compteur']
        dn_compteur = request.POST['DN_compteur']
        origin_compteur = request.POST['origin_compteur']
        num_compteur_principale = request.POST.get('num_compteur_principale', '')

        mod_compteur.marque_compteur = marque_compteur
        mod_compteur.modele_compteur = modele_compteur
        mod_compteur.DN_compteur = dn_compteur
        mod_compteur.origin_compteur = origin_compteur
        
        # Mettre à jour le compteur principal
        if num_compteur_principale:
            try:
                mod_compteur.num_compteur_principale = CompteurPrincipale.objects.get(pk=num_compteur_principale)
            except CompteurPrincipale.DoesNotExist:
                mod_compteur.num_compteur_principale = None
        else:
            mod_compteur.num_compteur_principale = None
        
        mod_compteur.save()
        # Historique
        message = f"Modification de compteur numéro {pk}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, f"Modification du Compteur numéro {mod_compteur.num_compteur} avec succès !")
        return redirect('compteur_list')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def compteur_supp(request, pk):
    compteur = Compteur.objects.get(pk=pk)

    # Vérifier si le compteur est lié à un contrat
    if compteur.contrats.exists():
        messages.error(request, f"Impossible de supprimer le compteur {pk} car il est lié à un contrat !")
        return redirect('compteur_list')

    # Hard delete du compteur (CASCADE supprime automatiquement les relevés liés)
    compteur.hard_delete()

    # Historique
    message = f"Suppression de compteur numéro {pk}"
    enregistre_historique(message, request.session.get('id_utilisateur'))

    messages.success(request, f'Compteur supprimé avec succès !')
    return redirect('compteur_list')


@role_requis('Administrateur', 'Gestionnaire', 'Releveur')
@schema_use
def compteur_releve(request):
    title = 'Compteurs | Relevé'
    active = 'active'
    font = 'custom-font'

    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    zero_releve = ReleveCompteur.objects.filter(conso=0).count()
    if datedeb and datefin:
        if datedeb > datefin:
            messages.warning(request, f'La Date Début ne doit pas être superieure à la Date Fin !')
            releve = ReleveCompteur.objects.order_by('-date_releve').all()
        else:
            releve = ReleveCompteur.objects.filter(date_releve__range=[datedeb, datefin])
    else:
        releve = ReleveCompteur.objects.order_by('-date_releve').all()
    context = {
        'title_releve': title,
        'active_releve': active,
        'font_compteur': font,
        'zero_releve': zero_releve,
        'releve': releve,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else '',
    }
    return render(request, 'all_page/compteurs/compteurs.html', context)


class ReleveNew(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def get(self, request, num_compteur):
        try:
            compteur = Compteur.objects.get(pk=num_compteur)

            title = f'Compteur Numéro : {compteur.num_compteur} | Relevé | Nouveau'
            active = 'active'
            font = 'custom-font'

            # Récupérer le dernier relevé (hors rejetés)
            dernier_releve = compteur.relevecompteurs.exclude(statut_validation='REJETE').order_by('-date_releve').first()

            context = {
                'title_releve_new': title,
                'active_releve_new': active,
                'font_compteur': font,
                'compteur': compteur,
                'dernier_releve': dernier_releve
            }
            return render(request, self.template_name, context)

        except Compteur.DoesNotExist:
            messages.error(request, "Le compteur spécifié n'existe pas.")
            return redirect('compteur_list')
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")
            return redirect('compteur_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def post(request, num_compteur):
        date_releve = request.POST.get('date_releve')
        date_releve = datetime.strptime(date_releve, '%Y-%m-%d').date()
        volume = int(request.POST['volume'])
        image_compteur = request.FILES.get('image_compteur')
        utilisateur = request.session.get('id_utilisateur')

        try:
            # Exclure les relevés rejetés pour le calcul de la consommation
            dernier_volume = ReleveCompteur.objects.filter(
                num_compteur_id=num_compteur
            ).exclude(statut_validation='REJETE').latest('date_releve')

            if dernier_volume:
                if date_releve <= dernier_volume.date_releve:
                    messages.error(request, f"Veuillez fournir une date valide !")
                    return redirect('releve_new', num_compteur)
                elif dernier_volume.volume > volume:
                    messages.error(request, f"Assurez-vous de saisir les chiffres correctement et réessayez !")
                    return redirect('releve_new', num_compteur)
                else:
                    conso = volume - dernier_volume.volume
            else:
                conso = volume

            # Si Admin ou Gestionnaire, le relevé est directement validé
            role_utilisateur = request.session.get('role_utilisateur')
            if role_utilisateur in ['Administrateur', 'Gestionnaire']:
                releve = relever(num_compteur, date_releve, volume, conso, image_compteur, utilisateur,
                                statut_validation='CONFIRME', valideur_id=utilisateur)
                # Créer la facture immédiatement
                facture_creation(date_releve, num_compteur, releve)
            else:
                # Pour les Releveurs, le relevé est en attente de validation
                releve = relever(num_compteur, date_releve, volume, conso, image_compteur, utilisateur,
                                statut_validation='EN_ATTENTE')
                # Pas de facture - sera créée lors de la confirmation
            
            # Vérifier l'alerte si lié à un compteur principal
            # Crée toujours une nouvelle alerte pour assurer l'historique
            try:
                compteur = Compteur.objects.get(pk=num_compteur)
                if compteur.num_compteur_principale:
                    alerte = AlerteConsommation.creer_alerte_si_necessaire(
                        compteur.num_compteur_principale, 
                        verifier_doublon=False
                    )
                    if alerte:
                        messages.warning(request, f"Alerte créée sur le compteur principal : {alerte.message}")
            except Exception as e:
                # Ne pas bloquer le flux principal pour une erreur d'alerte
                print(f"Erreur lors de la vérification d'alerte : {e}")

            # Historique
            message = f"Relever et Facture d'un compteur {num_compteur}"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, f"Relevé enregistrer avec succès !")
            return redirect('compteur_detail', num_compteur)

        except ReleveCompteur.DoesNotExist:
            messages.error(request, f"Date du dernier relevé inexistant dans la base !")
            return redirect('releve_new', num_compteur)


def relever(num_compteur, date_releve, volume, conso, image_compteur, utilisateur, 
            statut_validation='EN_ATTENTE', valideur_id=None):

    releve = ReleveCompteur.objects.create(
        num_compteur_id=num_compteur,
        date_releve=date_releve,
        volume=volume,
        conso=conso,
        image_compteur=image_compteur,
        utilisateur_id=utilisateur,
        statut_validation=statut_validation,
        valideur_id=valideur_id,
        date_validation=timezone.now() if statut_validation == 'CONFIRME' else None
    )
    return releve


class ReleveMod(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk):
        releve = ReleveCompteur.objects.get(pk=pk)
        title = f"Relevé | Détail | "
        active = 'active'
        font = 'custom-font'

        context = {
            'title_releve_detail': title,
            'active_releve_detail': active,
            'font_compteur': font,
            'releve': releve
        }
        return render(request, self.template_name, context)

    @staticmethod
    def mod_relever_facture(id_releve, date_releve, volume, image_compteur, dernier_releve, valideur_id=None):
        mod_releve = ReleveCompteur.objects.get(pk=id_releve)
        conso = volume - dernier_releve.volume
        mod_releve.date_releve = date_releve
        mod_releve.volume = volume
        mod_releve.conso = conso
        if image_compteur:
            mod_releve.image_compteur = image_compteur
            
        # Si modifié/corrigé par un gestionnaire, on le confirme et on efface les traces du rejet
        mod_releve.statut_validation = 'CONFIRME'
        if valideur_id:
            mod_releve.valideur_id = valideur_id
        mod_releve.date_validation = timezone.now()
        mod_releve.motif_rejet = None
        mod_releve.save()
        
        # La suppression de l'ancienne facture est maintenant gérée par facture_creation
        # mais on peut garder une sécurité ici au cas où
        Facture.objects.filter(relevecompteur_id=id_releve).delete()

        return mod_releve

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        date_releve = request.POST['date_releve']
        date_releve = datetime.strptime(date_releve, '%Y-%m-%d').date()
        volume = int(request.POST['volume'])
        image_compteur = request.FILES.get('image_compteur')
        releve_a_mod = ReleveCompteur.objects.get(pk=pk)
        compteur = releve_a_mod.num_compteur

        # Trouver le relevé chronologiquement précédent (hors rejetés)
        dernier_releve = compteur.relevecompteurs.filter(
            date_releve__lt=releve_a_mod.date_releve
        ).exclude(statut_validation='REJETE').order_by('-date_releve').first()

        if not dernier_releve:
            # Cas du premier relevé
            releve_a_mod.date_releve = date_releve
            releve_a_mod.volume = volume
            releve_a_mod.conso = 0  # Ou volume si c'est le cas
            if image_compteur:
                releve_a_mod.image_compteur = image_compteur
            
            # Forcer la confirmation car fait par un gestionnaire
            releve_a_mod.statut_validation = 'CONFIRME'
            releve_a_mod.valideur_id = request.session.get('id_utilisateur')
            releve_a_mod.date_validation = timezone.now()
            releve_a_mod.motif_rejet = None
            releve_a_mod.save()
            
            # Mise à jour de la facture si Admin
            if request.session.get('role_utilisateur') in ['Administrateur', 'Gestionnaire']:
                facture_creation(date_releve, compteur.pk, releve_a_mod)
                
            messages.success(request, "Relevé enregistré avec succès !")
            return redirect('compteur_detail', compteur.pk)

        # Validation par rapport au relevé précédent
        if date_releve <= dernier_releve.date_releve:
            messages.error(request, f"Veuillez fournir une date valide pour le relevé !")
            return redirect('releve_mod', pk)
        
        if volume < dernier_releve.volume:
            messages.warning(request, f"Vous ne pouvez pas enregistrer un relevé inférieur au précédent !")
            return redirect('releve_mod', pk)
        
        # Mise à jour via la méthode statique (inclut la confirmation automatique)
        mod_releve = ReleveMod.mod_relever_facture(
            pk, date_releve, volume, image_compteur, dernier_releve,
            valideur_id=request.session.get('id_utilisateur')
        )
        
        # Recréation de la facture si Admin
        if request.session.get('role_utilisateur') in ['Administrateur', 'Gestionnaire']:
            facture_creation(date_releve, compteur.pk, mod_releve)
            
        messages.success(request, f"Relevé enregistré avec succès !")
        return redirect('compteur_detail', compteur.pk)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def del_releve(request, pk):
    releve = get_object_or_404(ReleveCompteur, pk=pk)
    
    # Vérifier si une facture existe pour ce relevé
    facture = Facture.objects.filter(relevecompteur__id_releve=pk).first()
    
    # Si la facture existe et est déjà payée, empêcher la suppression
    if facture and facture.statut:
        messages.error(request, f"Impossible de supprimer ce relevé car la facture associée est déjà payée !")
        return redirect('compteur_detail', releve.num_compteur.pk)
    
    releve.image_compteur.delete()
    releve.delete()
    
    # Supprimer la facture associée si elle existe
    if facture:
        facture.delete()
    
    messages.success(request, f"Relevé supprimé avec succès !")
    return redirect('compteur_detail', releve.num_compteur.pk)


class ConfigurationAlertes(SchemaAwareView):
    """Classe pour la configuration des seuils d'alerte"""
    
    template_name = 'all_page/ranoo_config/content.html'
    
    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        params = ParametreAlerte.get_parametres_actifs()
        
        titre = 'Ranoo Config | Configuration des Alertes'
        active = 'active'
        font = 'custom-font'

        context = {
            'params': params,
            'titre_config_alertes': titre,
            'active_config_alertes': active,
            'font_rano': font,
        }
        return render(request, self.template_name, context)
    
    @role_requis('Administrateur', 'Gestionnaire')
    def post(self, request):
        params = ParametreAlerte.get_parametres_actifs()
        
        seuil_alerte = request.POST.get('seuil_alerte')
        seuil_critique = request.POST.get('seuil_critique')
        
        # Validation
        try:
            seuil_alerte = float(seuil_alerte)
            seuil_critique = float(seuil_critique)
            
            if seuil_alerte <= 0 or seuil_critique <= 0:
                messages.error(request, "Les seuils doivent être positifs.")
            elif seuil_alerte >= seuil_critique:
                messages.error(request, "Le seuil d'alerte doit être inférieur au seuil critique.")
            else:
                # Mise à jour
                params.seuil_alerte = seuil_alerte
                params.seuil_critique = seuil_critique
                params.utilisateur_modification_id = request.session.get('id_utilisateur')
                params.save()
                messages.success(request, "Paramètres d'alerte mis à jour avec succès !")
                return redirect('config_alertes')
        except ValueError:
            messages.error(request, "Veuillez entrer des valeurs numériques valides.")
        
        # Réafficher le formulaire avec les erreurs
        titre = 'Ranoo Config | Configuration des Alertes'
        active = 'active'
        font = 'custom-font'
        
        context = {
            'params': params,
            'titre_config_alertes': titre,
            'active_config_alertes': active,
            'font_rano': font,
        }
        return render(request, self.template_name, context)


@schema_use
def export_fiche_releve(request):
    commune_id = request.GET.get('commune')
    num_client_deb = request.GET.get('num_client_deb')
    num_client_fin = request.GET.get('num_client_fin')

    # Construire la requête de base pour les contrats actifs avec leurs relations
    contrats_query = Contrat.objects.select_related(
        'client',
        'client__type_client',
        'num_compteur',
        'cp_commune'  # Ajout de la jointure avec la commune
    ).prefetch_related(
        'num_compteur__relevecompteurs'
    )

    contrats_query = filter_by_client_number(
        queryset=contrats_query,
        client_field='client__num_client',
        num_client_deb=num_client_deb,
        num_client_fin=num_client_fin
    )

    # Appliquer le filtre par commune si spécifié
    if commune_id:
        contrats_query = contrats_query.filter(cp_commune_id=commune_id)

    # Exécuter la requête
    contrats = contrats_query.all().order_by('client__num_client')

    # Préparer les données pour le template
    aujourdhui = date.today()
    mois_precedent = aujourdhui - relativedelta(months=1)

    # Préparer les données pour le template
    data = []
    for contrat in contrats:
        compteur = contrat.num_compteur
        if not compteur:
            continue

        # Récupérer le relevé du mois actuel (hors rejetés)
        releve_actuel = compteur.relevecompteurs.filter(
            date_releve__year=aujourdhui.year,
            date_releve__month=aujourdhui.month
        ).exclude(statut_validation='REJETE').order_by('-date_releve').first()

        # Récupérer le DERNIER relevé connu (hors mois actuel et hors rejetés)
        # Cela gère le cas où il n'y a pas eu de relevé le mois précédent
        releve_precedent = compteur.relevecompteurs.exclude(
            date_releve__year=aujourdhui.year,
            date_releve__month=aujourdhui.month
        ).exclude(statut_validation='REJETE').order_by('-date_releve').first()

        # INFO : releve_actuel peut être None si pas encore fait
        # releve_precedent est le dernier index "sûr" connu du système

        # Si pas de relevé ce mois-ci, on prend le plus récent (si on veut afficher qqchose pour actuel)
        if not releve_actuel:
            # Ici on laisse releve_actuel à None pour signifier "Pas de relevé ce mois"
            pass

        # Calculer la consommation
        conso = 0
        if releve_actuel and releve_precedent:
            conso = releve_actuel.volume - releve_precedent.volume
        elif releve_actuel:
            conso = releve_actuel.volume

        data.append({
            'num_client': contrat.client.num_client,
            'nom_client': f"{contrat.client.nom_client} {contrat.client.prenom_client or ''}".strip(),
            'adresse': contrat.adresse_contrat,
            'ancien_releve': releve_precedent.volume if releve_precedent else 0,
            'date_ancien_releve': releve_precedent.date_releve if releve_precedent else None,
            'conso': conso,
            'type_client': contrat.client.type_client.designation_client if contrat.client and contrat.client.type_client else '',
            'date_releve': releve_actuel.date_releve if releve_actuel else 'N/A'
        })

    # Récupérer le nom de la commune pour le titre
    commune_nom = 'Toutes les communes'
    if commune_id:
        try:
            commune = Commune.objects.get(pk=commune_id)
            commune_nom = commune.commune
        except (Commune.DoesNotExist, Exception):
            pass

    # Préparer le contexte pour le template
    context = {
        'compteurs': data,
        'date_export': datetime.now(),
        'commune': commune_nom
    }

    # Rendre le template en chaîne HTML
    html_string = render_to_string(
        'all_page/compteurs/pdf/fiche_releve.html',
        context
    )

    # Créer une réponse HTTP avec le type MIME PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Fiche_de_releve_{commune_nom}({datetime.now()}).pdf"'

    # Générer le PDF
    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)

    # Enregistrer dans l'historique
    message = "Export PDF de la liste des compteurs"
    enregistre_historique(message, request.session.get('id_utilisateur'))

    return response


@schema_use
def export_recouvrement(request):
    # Récupérer les paramètres de requête
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    commune_id = request.GET.get('commune')
    num_client_deb = request.GET.get('num_client_deb')
    num_client_fin = request.GET.get('num_client_fin')

    # Définir les dates par défaut si non fournies (3 mois en arrière par défaut)
    today = timezone.now()
    if not date_debut:
        # Premier jour du mois il y a 3 mois
        if today.month > 3:
            date_debut = today.replace(month=today.month-3, day=1)
        else:
            date_debut = today.replace(year=today.year-1, month=12-(3-today.month), day=1)
    else:
        # Si date_debut est fournie, la convertir en datetime
        date_debut, _ = get_month_range(date_debut)

    if not date_fin:
        date_fin = today  # Aujourd'hui par défaut
    else:
        _, date_fin = get_month_range(date_fin)

    # Générer la liste des mois dans l'intervalle
    months = get_3_months_range(date_debut, date_fin)

    # Préparer la requête de base pour les factures impayées
    factures_query = Facture.objects.filter(
        statut=False,
        date_facture__range=[date_debut, date_fin]
    )

    # Filtrer par intervalle de numéros de client si spécifiés
    factures_query = filter_by_client_number(
        queryset=factures_query,
        client_field='num_contrat__client__num_client',
        num_client_deb=num_client_deb,
        num_client_fin=num_client_fin
    )

    # Filtrer par commune si spécifiée
    if commune_id:
        factures_query = factures_query.filter(
            num_contrat__cp_commune_id=commune_id
        )

    # Exécuter la requête avec les jointures nécessaires
    # Récupérer d'abord toutes les factures sans tri
    factures_impayees = factures_query.select_related(
        'num_contrat__client',
        'num_contrat__num_compteur',
        'num_contrat__cp_commune'
    )

    factures_impayees = sorted(
        factures_impayees,
        key=lambda x: int(x.num_contrat.num_compteur.num_compteur) if x.num_contrat.num_compteur and x.num_contrat.num_compteur.num_compteur.isdigit() else float('inf')
    )

    # Créer une structure pour stocker les données par client
    clients_data = defaultdict(dict)
    clients_info = {}

    # Remplir les données
    for facture in factures_impayees:
        client = facture.num_contrat.client
        # Ajuster la date pour afficher le mois précédent
        facture_date = facture.date_facture
        if facture_date.month == 1:
            adjusted_date = facture_date.replace(year=facture_date.year-1, month=12)
        else:
            adjusted_date = facture_date.replace(month=facture_date.month-1)

        month_key = adjusted_date.strftime('%Y-%m')

        if client.id_client not in clients_info:
            clients_info[client.id_client] = {
                'nom': f"{client.nom_client} {client.prenom_client or ''}".strip(),
                'adresse': facture.num_contrat.adresse_contrat or '',
                'compteur': facture.num_contrat.num_compteur.num_compteur if facture.num_contrat.num_compteur else '',
                'commune': facture.num_contrat.cp_commune.commune if hasattr(facture.num_contrat.cp_commune, 'commune') else 'Non spécifiée'
            }

        if month_key not in clients_data[client.id_client]:
            clients_data[client.id_client][month_key] = 0

        clients_data[client.id_client][month_key] += float(facture.montant_total_ttc or 0)

    # Préparer les données pour le template
    data = []
    for client_id, montants in clients_data.items():
        client_row = {
            'id': client_id,
            'nom': clients_info[client_id]['nom'],
            'adresse': clients_info[client_id]['adresse'],
            'compteur': clients_info[client_id]['compteur'],
            'mois': {}
        }

        # Ajouter les montants par mois
        for year, month in months:
            month_key = f"{year:04d}-{month:02d}"  # Clé pour la recherche dans les montants
            display_month = get_month_name_fr(month)  # Format d'affichage : nom du mois
            client_row['mois'][display_month] = montants.get(month_key, 0)

        data.append(client_row)

    # Préparer les en-têtes de colonnes avec le nom du mois
    mois_headers = [get_month_name_fr(month) for year, month in months]
    
    # Récupérer le nom de la commune pour le titre
    commune_nom = 'Toutes les communes'
    if commune_id:
        try:
            commune = Commune.objects.get(pk=commune_id)
            commune_nom = commune.commune
        except (Commune.DoesNotExist, Exception):
            pass

    context = {
        'clients': data,
        'mois_headers': mois_headers,
        'date_export': datetime.now(),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'commune': commune_nom
    }
    
    # Rendu du template
    html_string = render_to_string('all_page/compteurs/pdf/recouvrement.html', context)
    
    # Création du PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Recouvrement_{commune_nom}_{date_debut.strftime("%Y-%m-%d")}_au_{date_fin.strftime("%Y-%m-%d")}.pdf"'
    
    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)
    
    return response


@schema_use
def export_relever(request, num_compteur):
    # Récupérer le paramètre de filtre par commune
    commune_id = request.GET.get('commune')
    
    releves_query = ReleveCompteur.objects.filter(num_compteur_id=num_compteur)

    # Filtrer par commune si spécifiée
    if commune_id:
        releves_query = releves_query.filter(
            num_compteur__contrats__cp_commune_id=commune_id
        ).distinct()
    
    # Récupérer les relevés
    relevecompteur = releves_query.all()
    
    # Nom du fichier d'export
    nom_fichier = f"Relever_de_{num_compteur}.xlsx"
    
    # Champs à exporter
    champs = [
        'num_compteur_id',
        'date_releve',
        'volume',
        'conso',
    ]
    nom_colonnes = [
        'N° Compteur',
        'Date de Relevé',
        'volume',
        'Consommation'
    ]
    response = exporter_en_excel(relevecompteur, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout les compteurs"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response


# ========================== COMPTEUR PRINCIPALE ==========================

@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def compteur_principale_liste(request):
    """Liste tous les compteurs principaux avec l'écart de consommation"""
    title = 'Compteurs Principaux | Liste'
    active = 'active'
    font = 'custom-font'

    # Récupérer les paramètres de filtre
    date_filtre = request.GET.get('date_filtre')

    compteurs_principaux = CompteurPrincipale.objects.prefetch_related(
        'compteurs', 'releves'
    ).all()

    # Préparer les données avec l'écart calculé
    compteurs_data = []
    for cp in compteurs_principaux:
        dernier_releve = cp.releves.order_by('-date_releve').first()
        
        # Utiliser la date du dernier relevé pour le calcul du total sous-compteurs
        if date_filtre:
            date_calcul = date_filtre
        elif dernier_releve:
            date_calcul = dernier_releve.date_releve
        else:
            date_calcul = None
        
        # Calculer le total des sous-compteurs avec la même date
        total_sous_compteurs = cp.get_total_conso_sous_compteurs(date_calcul) if date_calcul else 0
        
        # Calculer l'écart
        conso_principal = dernier_releve.conso if dernier_releve and dernier_releve.conso else 0
        ecart = conso_principal - total_sous_compteurs if conso_principal > 0 else None
        
        compteurs_data.append({
            'compteur': cp,
            'dernier_releve': dernier_releve,
            'total_sous_compteurs': total_sous_compteurs,
            'ecart': ecart,
            'nb_sous_compteurs': cp.compteurs.count()
        })

    context = {
        'title_cp_liste': title,
        'active_cp_liste': active,
        'font_compteur': font,
        'compteurs_principaux': compteurs_data,
        'date_filtre': date_filtre
    }
    return render(request, 'all_page/compteurs/compteurs.html', context)


class CompteurPrincipaleNew(SchemaAwareView):
    """Création d'un nouveau compteur principal"""
    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Compteurs Principaux | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'title_cp_new': title,
            'active_cp_new': active,
            'font_compteur': font
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        num_compteur = request.POST.get('num_compteur_principale')
        marque = request.POST.get('marque_compteur_principale', '')
        modele = request.POST.get('modele_compteur_principale', '')
        dn = request.POST.get('DN_compteur_principale', '')
        origine = request.POST.get('origin_compteur_principale', '')
        date_releve = request.POST.get('date_releve')
        volume = request.POST.get('volume', 0)

        # Vérifier si le compteur existe déjà
        if CompteurPrincipale.objects.filter(pk=num_compteur).exists():
            messages.warning(request, f"Le compteur principal {num_compteur} existe déjà !")
            return redirect('compteur_principale_new')

        try:
            # Créer le compteur principal
            cp = CompteurPrincipale.objects.create(
                num_compteur_principale=num_compteur,
                marque_compteur_principale=marque,
                modele_compteur_principale=modele,
                DN_compteur_principale=dn,
                origin_compteur_principale=origine
            )

            # Créer le premier relevé (index initial)
            if date_releve and volume:
                ReleveCompteurPrincipale.objects.create(
                    date_releve=date_releve,
                    volume=int(volume),
                    conso=0,  # Premier relevé, pas de consommation
                    num_compteur_principale=cp,
                    utilisateur_id=request.session.get('id_utilisateur')
                )

            # Historique
            message = f"Création du compteur principal {num_compteur}"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, f"Compteur principal créé avec succès !")
            return redirect('compteur_principale_list')

        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {e}")
            return redirect('compteur_principale_new')


class CompteurPrincipaleDetail(SchemaAwareView):
    """Détail et modification d'un compteur principal"""
    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk):
        try:
            cp = CompteurPrincipale.objects.prefetch_related('compteurs', 'releves').get(pk=pk)
            releves = cp.releves.order_by('-date_releve')
            sous_compteurs = cp.compteurs.all()

            # Calculer les données pour l'affichage
            dernier_releve = releves.first()
            ecart = cp.get_ecart_consommation()
            total_sous_compteurs = cp.get_total_conso_sous_compteurs()

            title = f'Compteur Principal | {cp.num_compteur_principale}'
            active = 'active'
            font = 'custom-font'

            context = {
                'title_cp_detail': title,
                'active_cp_detail': active,
                'font_compteur': font,
                'compteur_principal': cp,
                'releves': releves,
                'sous_compteurs': sous_compteurs,
                'dernier_releve': dernier_releve,
                'ecart': ecart,
                'total_sous_compteurs': total_sous_compteurs
            }
            return render(request, self.template_name, context)

        except CompteurPrincipale.DoesNotExist:
            messages.error(request, "Ce compteur principal n'existe pas.")
            return redirect('compteur_principale_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk):
        try:
            cp = CompteurPrincipale.objects.get(pk=pk)
            cp.marque_compteur_principale = request.POST.get('marque_compteur_principale', '')
            cp.modele_compteur_principale = request.POST.get('modele_compteur_principale', '')
            cp.DN_compteur_principale = request.POST.get('DN_compteur_principale', '')
            cp.origin_compteur_principale = request.POST.get('origin_compteur_principale', '')
            cp.save()

            # Historique
            message = f"Modification du compteur principal {pk}"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, f"Compteur principal modifié avec succès !")
            return redirect('compteur_principale_detail', pk)

        except CompteurPrincipale.DoesNotExist:
            messages.error(request, "Ce compteur principal n'existe pas.")
            return redirect('compteur_principale_list')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def compteur_principale_supp(request, pk):
    """Suppression d'un compteur principal"""
    try:
        cp = CompteurPrincipale.objects.get(pk=pk)
        num = cp.num_compteur_principale
        cp.delete()

        # Historique
        message = f"Suppression du compteur principal {num}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, f"Compteur principal supprimé avec succès !")
    except CompteurPrincipale.DoesNotExist:
        messages.error(request, "Ce compteur principal n'existe pas.")

    return redirect('compteur_principale_list')


# ========================== RELEVE COMPTEUR PRINCIPALE ==========================

class ReleveCompteurPrincipaleNew(SchemaAwareView):
    """Création d'un nouveau relevé pour un compteur principal"""
    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, num_compteur):
        try:
            cp = CompteurPrincipale.objects.get(pk=num_compteur)
            dernier_releve = cp.releves.order_by('-date_releve').first()

            title = f'Relevé | Compteur Principal {cp.num_compteur_principale}'
            active = 'active'
            font = 'custom-font'

            context = {
                'title_cp_releve_new': title,
                'active_cp_releve': active,
                'font_compteur': font,
                'compteur_principal': cp,
                'dernier_releve': dernier_releve
            }
            return render(request, self.template_name, context)

        except CompteurPrincipale.DoesNotExist:
            messages.error(request, "Ce compteur principal n'existe pas.")
            return redirect('compteur_principale_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, num_compteur):
        try:
            cp = CompteurPrincipale.objects.get(pk=num_compteur)
            date_releve = request.POST.get('date_releve')
            date_releve = datetime.strptime(date_releve, '%Y-%m-%d').date()
            volume = int(request.POST.get('volume', 0))
            image = request.FILES.get('image_compteur')

            # Récupérer le dernier relevé
            dernier_releve = cp.releves.order_by('-date_releve').first()

            if dernier_releve:
                # Vérifier la date
                if date_releve <= dernier_releve.date_releve:
                    messages.error(request, "La date doit être postérieure au dernier relevé.")
                    return redirect('releve_cp_new', num_compteur)

                # Vérifier le volume
                if volume < dernier_releve.volume:
                    messages.error(request, "Le volume ne peut pas être inférieur au dernier relevé.")
                    return redirect('releve_cp_new', num_compteur)

                conso = volume - dernier_releve.volume
            else:
                conso = 0

            # Créer le relevé
            ReleveCompteurPrincipale.objects.create(
                date_releve=date_releve,
                volume=volume,
                conso=conso,
                image_compteur=image,
                num_compteur_principale=cp,
                utilisateur_id=request.session.get('id_utilisateur')
            )

            # Vérifier et créer une alerte si nécessaire
            # Crée toujours une nouvelle alerte pour assurer l'historique
            alerte = AlerteConsommation.creer_alerte_si_necessaire(cp, verifier_doublon=False)
            if alerte:
                messages.warning(request, f"Alerte créée : {alerte.message}")

            # Historique
            message = f"Relevé du compteur principal {num_compteur} - Volume: {volume} m³"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, "Relevé enregistré avec succès !")
            return redirect('compteur_principale_detail', num_compteur)

        except CompteurPrincipale.DoesNotExist:
            messages.error(request, "Ce compteur principal n'existe pas.")
            return redirect('compteur_principale_list')
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
            return redirect('releve_cp_new', num_compteur)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def releve_cp_supp(request, pk):
    """Suppression d'un relevé de compteur principal"""
    try:
        releve = ReleveCompteurPrincipale.objects.get(pk=pk)
        num_compteur = releve.num_compteur_principale.pk
        releve.delete()

        # Historique
        message = f"Suppression d'un relevé du compteur principal {num_compteur}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, "Relevé supprimé avec succès !")
        return redirect('compteur_principale_detail', num_compteur)

    except ReleveCompteurPrincipale.DoesNotExist:
        messages.error(request, "Ce relevé n'existe pas.")
        return redirect('compteur_principale_list')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def comparaison_consommation(request, pk):
    """Vue pour comparer la consommation du compteur principal avec ses sous-compteurs"""
    try:
        cp = CompteurPrincipale.objects.prefetch_related('compteurs__relevecompteurs').get(pk=pk)

        date_filtre = request.GET.get('date_filtre')

        # Données du compteur principal
        releve_principal = cp.releves.filter(date_releve=date_filtre).first() if date_filtre else cp.releves.order_by('-date_releve').first()

        # Données des sous-compteurs (exclure ceux sans contrat)
        sous_compteurs_data = []
        for compteur in cp.compteurs.all():
            # Exclure les compteurs sans contrat
            if not compteur.contrats.exists():
                continue
                
            # Définir la date de référence pour la recherche
            date_ref = date_filtre
            if not date_ref and releve_principal:
                date_ref = releve_principal.date_releve
                
            if date_ref:
                releve = compteur.relevecompteurs.filter(date_releve__lte=date_ref).order_by('-date_releve').first()
            else:
                releve = compteur.relevecompteurs.order_by('-date_releve').first()

            conso = releve.conso if releve and releve.conso else 0
            sous_compteurs_data.append({
                'compteur': compteur,
                'releve': releve,
                'conso': conso
            })

        total_sous_compteurs = sum(item['conso'] for item in sous_compteurs_data)
        conso_principal = releve_principal.conso if releve_principal and releve_principal.conso else 0
        ecart = conso_principal - total_sous_compteurs
        # Calcul du pourcentage avec le signe (négatif si sous-compteurs > principal)
        pourcentage_ecart = (ecart / conso_principal * 100) if conso_principal > 0 else 0

        # Récupérer les seuils configurés
        params_alerte = ParametreAlerte.get_parametres_actifs()

        title = f'Comparaison | {cp.num_compteur_principale}'
        context = {
            'title_comparaison': title,
            'font_compteur': 'custom-font',
            'active_cp_releve': 'active',
            'compteur_principal': cp,
            'releve_principal': releve_principal,
            'sous_compteurs': sous_compteurs_data,
            'total_sous_compteurs': total_sous_compteurs,
            'ecart': ecart,
            'pourcentage_ecart': round(pourcentage_ecart, 2),
            'date_filtre': date_filtre,
            'seuil_alerte': params_alerte.seuil_alerte,
            'seuil_critique': params_alerte.seuil_critique,
        }
        return render(request, 'all_page/compteurs/compteurs.html', context)

    except CompteurPrincipale.DoesNotExist:
        messages.error(request, "Ce compteur principal n'existe pas.")
        return redirect('compteur_principale_list')


# ========================== ALERTES DE CONSOMMATION ==========================

@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def alerte_marquer_lu(request, pk):
    """Marquer une alerte comme lue"""
    try:
        alerte = AlerteConsommation.objects.get(pk=pk)
        alerte.statut = 'LU'
        alerte.save()
        
        # Rediriger vers la page suivante ou la page de comparaison
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect(request.META.get('HTTP_REFERER', 'compteur_principale_list'))
    except AlerteConsommation.DoesNotExist:
        messages.error(request, "Cette alerte n'existe pas.")
        return redirect('compteur_principale_list')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def alerte_marquer_toutes_lues(request):
    """Marquer toutes les alertes comme lues"""
    AlerteConsommation.objects.filter(statut='NON_LU').update(statut='LU')
    messages.success(request, "Toutes les alertes ont été marquées comme lues.")
    return redirect(request.META.get('HTTP_REFERER', 'compteur_principale_list'))


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def alerte_supprimer(request, pk):
    """Supprimer définitivement une alerte"""
    try:
        alerte = AlerteConsommation.objects.get(pk=pk)
        alerte.delete()
        messages.success(request, "Alerte supprimée avec succès.")
        return redirect(request.META.get('HTTP_REFERER', 'liste_alertes'))
    except AlerteConsommation.DoesNotExist:
        messages.error(request, "Cette alerte n'existe pas.")
        return redirect('liste_alertes')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def alerte_traiter(request, pk):
    """Marquer une alerte comme traitée avec un commentaire"""
    try:
        alerte = AlerteConsommation.objects.get(pk=pk)
        
        if request.method == 'POST':
            commentaire = request.POST.get('commentaire', '')
            alerte.statut = 'TRAITE'
            alerte.commentaire = commentaire
            alerte.utilisateur_traitement_id = request.session.get('id_utilisateur')
            alerte.date_traitement = timezone.now()
            alerte.save()
            
            messages.success(request, "Alerte traitée avec succès.")
            return redirect('compteur_principale_detail', alerte.compteur_principal.pk)
        
        # Si GET, rediriger vers la page de comparaison
        return redirect('comparaison_consommation', alerte.compteur_principal.pk)
        
    except AlerteConsommation.DoesNotExist:
        messages.error(request, "Cette alerte n'existe pas.")
        return redirect('compteur_principale_list')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def alertes_liste(request):
    """Liste de toutes les alertes"""
    alertes = AlerteConsommation.objects.select_related('compteur_principal').all()
    
    # Filtre par statut
    statut_filtre = request.GET.get('statut')
    if statut_filtre:
        alertes = alertes.filter(statut=statut_filtre)
    
    context = {
        'title_alertes': 'Alertes de Consommation',
        'font_compteur': 'custom-font',
        'alertes': alertes,
        'statut_filtre': statut_filtre
    }
    return render(request, 'all_page/compteurs/alertes_liste.html', context)


# ========================== MISSIONS EN ATTENTE DE VALIDATION ==========================

@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def missions_en_attente(request):
    """Liste des relevés en attente de validation par les gestionnaires/admins"""
    title = 'Missions | En attente de validation'
    active = 'active'
    font = 'custom-font'
    
    # Récupérer les relevés en attente de validation
    qs = ReleveCompteur.objects.filter(statut_validation='EN_ATTENTE')
    
    # Si aucune mission en attente, redirection vers les factures
    if not qs.exists():
        messages.info(request, "Toutes les missions sont à jour !")
        return redirect('facture')

    releves_en_attente = qs.select_related(
        'num_compteur',
        'utilisateur'
    ).prefetch_related(
        'num_compteur__contrats__client'
    ).order_by('-date_releve')
    
    # Ajouter les informations client pour chaque relevé
    releves_data = []
    for releve in releves_en_attente:
        contrat = releve.num_compteur.contrats.first() if releve.num_compteur.contrats.exists() else None
        releves_data.append({
            'releve': releve,
            'client': contrat.client if contrat else None,
            'contrat': contrat,
            'agent': releve.utilisateur
        })
    
    context = {
        'title_missions': title,
        'active_missions': active,
        'font_missions': font,
        'releves_data': releves_data,
        'count': len(releves_data)
    }
    return render(request, 'all_page/compteurs/missions_en_attente.html', context)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def confirmer_mission(request, pk):
    """Confirme un relevé et génère la facture associée"""
    try:
        releve = ReleveCompteur.objects.get(pk=pk)
        
        if releve.statut_validation != 'EN_ATTENTE':
            messages.warning(request, "Ce relevé a déjà été traité.")
            return redirect('missions_en_attente')
        
        # Mettre à jour le statut
        releve.statut_validation = 'CONFIRME'
        releve.date_validation = timezone.now()
        releve.valideur_id = request.session.get('id_utilisateur')
        releve.save()
        
        # Vérifier si une facture existe déjà pour ce relevé
        facture_existante = Facture.objects.filter(relevecompteur_id=releve.id_releve).exists()
        
        if facture_existante:
            messages.success(request, f"Relevé confirmé pour le compteur {releve.num_compteur_id}. La facture existe déjà.")
        else:
            # Générer la facture seulement si elle n'existe pas
            try:
                facture_creation(releve.date_releve, releve.num_compteur_id, releve)
                messages.success(request, f"Relevé confirmé et facture générée pour le compteur {releve.num_compteur_id}.")
            except Exception as e:
                messages.warning(request, f"Relevé confirmé mais erreur lors de la génération de facture: {e}")
        
        # Enregistrer dans l'historique
        message = f"Confirmation du relevé {pk} pour le compteur {releve.num_compteur_id}"
        enregistre_historique(message, request.session.get('id_utilisateur'))
        
        # Vérifier l'alerte si lié à un compteur principal
        # Crée toujours une nouvelle alerte pour assurer l'historique
        try:
            compteur = releve.num_compteur
            if compteur.num_compteur_principale:
                # On utilise la date du relevé confirmé pour la vérification
                # Note: creer_alerte_si_necessaire attendra que TOUS les sous-compteurs soient relevés
                alerte = AlerteConsommation.creer_alerte_si_necessaire(
                    compteur.num_compteur_principale, 
                    verifier_doublon=False
                )
                if alerte:
                    messages.warning(request, f"Alerte créée sur le compteur principal : {alerte.message}")
        except Exception as e:
            # Ne pas bloquer le flux principal pour une erreur d'alerte
            messages.error(f"Erreur lors de la vérification d'alerte : {e}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message_html': render_to_string('message.html', request=request)
            })
            
        return redirect('missions_en_attente')
        
    except ReleveCompteur.DoesNotExist:
        messages.error(request, "Ce relevé n'existe pas.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message_html': render_to_string('message.html', request=request)
            })
        return redirect('missions_en_attente')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def rejeter_mission(request, pk):
    """Rejette un relevé avec un motif - l'agent devra refaire le relevé"""
    try:
        releve = ReleveCompteur.objects.get(pk=pk)
        
        if releve.statut_validation != 'EN_ATTENTE':
            messages.warning(request, "Ce relevé a déjà été traité.")
            return redirect('missions_en_attente')
        
        if request.method == 'POST':
            motif = request.POST.get('motif_rejet', '')
            
            # Mettre à jour le statut
            releve.statut_validation = 'REJETE'
            releve.date_validation = timezone.now()
            releve.valideur_id = request.session.get('id_utilisateur')
            releve.motif_rejet = motif
            releve.save()
            
            # Enregistrer dans l'historique
            message = f"Rejet du relevé {pk} pour le compteur {releve.num_compteur_id}. Motif: {motif}"
            enregistre_historique(message, request.session.get('id_utilisateur'))
            
            messages.success(request, f"Relevé rejeté. L'agent devra refaire le relevé.")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.template.loader import render_to_string
                return JsonResponse({
                    'success': True,
                    'message_html': render_to_string('message.html', request=request)
                })
                
            return redirect('missions_en_attente')
        
        # Si GET, rediriger vers la liste
        return redirect('missions_en_attente')
        
    except ReleveCompteur.DoesNotExist:
        messages.error(request, "Ce relevé n'existe pas.")
        return redirect('missions_en_attente')


@schema_use
def compter_missions_en_attente(request):
    """API endpoint pour compter les missions en attente (pour la navbar)"""
    from django.http import JsonResponse
    
    # Vérifier si l'utilisateur a le bon rôle
    role = request.session.get('role_utilisateur')
    if role not in ['Administrateur', 'Gestionnaire']:
        return JsonResponse({'count': 0})
    
    count = ReleveCompteur.objects.filter(statut_validation='EN_ATTENTE').count()
    return JsonResponse({'count': count})


