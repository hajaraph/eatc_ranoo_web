import base64
import gc
import logging
from datetime import timedelta, datetime
from io import BytesIO
import qrcode
from django.db import transaction, models
from django.db.models import Q, Sum
from django.template.loader import get_template
from django.utils import timezone
import json

from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from xhtml2pdf import pisa

from Clients.models import Contrat
from Clients.views import generate_pdf
from Compteurs.models import ReleveCompteur, Compteur
from Facturation.models import Facture, MontantHT, Tarif, Avoir, Paiement, Restant, MontantTTC, Taxe
from Login.views import role_requis
from Parametre.views import exporter_en_excel, enregistre_historique
from Acommune.models import Province
from Ranoo_Config.models import ConfigBranchement
from Rel_Compteur.utils import get_previous_month, get_month_range, get_default_month_range, filter_by_user_role, \
    filter_by_client_number
from Tenants.middleware import schema_use
from Tenants.models import Entreprise
from Recette.views import enregistrer_recette_paiement

logger = logging.getLogger(__name__)


def date_range(request, model, datedeb, datefin, date_field, statut=None):
    if datedeb and datefin and datedeb > datefin:
        messages.warning(request, 'La Date Début ne doit pas être supérieure à la Date Fin !')
        return model.objects.all().order_by(f'-{date_field}')

    filters = Q()
    if datedeb and datefin:
        filters &= Q(**{f"{date_field}__range": [datedeb, datefin]})

    if statut == 'paye':
        filters &= Q(statut=True)
    elif statut == 'impaye':
        filters &= Q(statut=False)

    return model.objects.filter(filters).order_by(f'-{date_field}')


def date_range_fact_pdf(date_deb, date_fin, commune, model):
    filters = Q()

    if date_deb and date_fin:
        filters &= Q(date_facture__range=[date_deb, date_fin])
    elif date_deb or date_fin:
        filters &= Q(date_facture=date_deb or date_fin)

    if commune:
        filters &= Q(num_contrat__cp_commune_id=commune)

    return model.filter(filters)

@schema_use
def facture(request):
    title = 'Facturation | Etat Facture'
    font = 'custom-font'
    active = 'active'

    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')

    # Filtrage par date si spécifié
    if datedeb and datefin:
        debut_mois, _ = get_month_range(datedeb)
        _, fin_mois = get_month_range(datefin)
        factures = date_range(request, Facture, debut_mois, fin_mois, 'date_facture')
    else:
        debut_mois, fin_mois = get_default_month_range()
        factures = Facture.objects.all()

    # Application du filtre par rôle après le filtrage par date
    factures = filter_by_user_role(request, factures, 'num_contrat__cp_commune_id')

    # Total des montants impayés du mois courant
    total_impaye_mois = factures.filter(
        statut=False,
        date_facture__range=[debut_mois, fin_mois]
    ).aggregate(total=Sum('montant_total_ttc'))['total'] or 0

    total_paye_mois = factures.filter(
        statut=True,
        date_facture__range=[debut_mois, fin_mois]
    ).aggregate(total=Sum('montant_total_ttc'))['total'] or 0

    # Calculer le total des taxes par type pour le mois en cours
    factures_mois = factures.filter(date_facture__range=[debut_mois, fin_mois])
    total_taxes_par_type = {}

    for facture_items in factures_mois:
        if facture_items.taxes_appliquees and facture_items.statut:
            try:
                # Si c'est une chaîne JSON, on la désérialise
                if isinstance(facture_items.taxes_appliquees, str):
                    taxes = json.loads(facture_items.taxes_appliquees)
                else:
                    # Si c'est déjà une liste, on l'utilise directement
                    taxes = facture_items.taxes_appliquees

                for taxe in taxes:
                    nom_taxe = taxe['nom_taxe']
                    montant = float(taxe['montant_taxe'])
                    if nom_taxe in total_taxes_par_type:
                        total_taxes_par_type[nom_taxe] += montant
                    else:
                        total_taxes_par_type[nom_taxe] = montant
            except Exception as e:
                messages.error(request, f"Erreur lors du traitement des taxes pour la facture {facture_items.num_facture}: {str(e)}")
                continue

    pronvince = Province.objects.order_by('province').all()
    # Trier d'abord par date (décroissant) puis par numéro de compteur (croissant)
    factures = sorted(
        factures,
        key=lambda x: (-x.date_facture.toordinal(), int(x.num_contrat.num_compteur.num_compteur))
    )

    context = {
        'title_etat': title,
        'active_etat': active,
        'font_facture': font,
        'factures': factures,
        'total_impaye_mois': total_impaye_mois,
        'total_paye_mois': total_paye_mois,
        'total_taxes_par_type': total_taxes_par_type,
        'provinces': pronvince,
        'datedeb': debut_mois.strftime('%Y-%m'),
        'datefin': fin_mois.strftime('%Y-%m'),
        'client': Contrat.objects.all().order_by('client__num_client'),
        'mois_actuel': datetime.now(),
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@role_requis('Administrateur')
@schema_use
def facture_supprimer(request, num_facture):
    """
    Supprime une facture et le relevé associé (Option C).
    Uniquement pour les Administrateurs.
    """
    try:
        facture = get_object_or_404(Facture, num_facture=num_facture)
        releve = facture.relevecompteur
        
        # Suppression de la facture (cascade sur MontantHT, Paiements, etc.)
        facture.delete()
        
        # Suppression du relevé (cascade sur l'image)
        if releve:
            if releve.image_compteur:
                releve.image_compteur.delete()
            releve.delete()
            
        # Historique
        message = f"Suppression de la facture {num_facture} et du relevé associé par l'administrateur"
        enregistre_historique(message, request.session.get('id_utilisateur'))
        
        messages.success(request, f"Facture {num_facture} et relevé supprimés avec succès.")
        return redirect('facture')
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression : {str(e)}")
        return redirect('facture_etat_detail', num_facture=num_facture)


@schema_use
def facture_etat_detail(request, num_facture):
    title = 'Facturation | Etat Facture | Détail'
    font = 'custom-font'
    active = 'active'

    # Requete pour chaque detail
    factures = Facture.objects.get(num_facture=num_facture)

    # Récupérer tous les paiements pour la facture
    paiements = Paiement.objects.filter(facture__num_facture=num_facture)
    montant = MontantTTC.objects.get(montant_ht__facture__num_facture=num_facture)
    typeclient = factures.num_contrat.client.type_client_id

    # Calculer le total des paiements
    total_paiements = paiements.aggregate(total=models.Sum('montant_payer'))['total'] or 0
    dernier_paiement = paiements.order_by('-date_paiement').first() if paiements.exists() else None

    context = {
        'title_etat_detail': title,
        'active_etat': active,
        'font_facture': font,
        'factures': factures,
        'paiement': dernier_paiement,
        'total_paiements': total_paiements,
        'paiements': paiements,
        'montant': montant,
        'typeclient': typeclient,
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@schema_use
def facture_paye(request):
    title = 'Facturation | Payé'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    paye = date_range(request, Facture, datedeb, datefin, 'date_facture', 'paye')

    context = {
        'title_facture_paye': title,
        'active_facture_paye': active,
        'font_facture': font,
        'payes': paye,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@schema_use
def facture_impaye(request):
    title = 'Facturation | Impayé'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    impaye = date_range(request, Facture, datedeb, datefin, 'date_facture', 'impaye')
    context = {
        'title_facture_impaye': title,
        'active_facture_impaye': active,
        'font_facture': font,
        'impayes': impaye,
        'datedeb': datedeb,
        'datefin': datefin
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@schema_use
def facture_restant(request):
    title = 'Facturation | Facture'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    restants = date_range(request, Restant, datedeb, datefin, 'date_restant')
    context = {
        'title_facture': title,
        'active_facture': active,
        'font_facture': font,
        'restants': restants,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@schema_use
def facture_retard(request):
    title = 'Facturation | Retard'
    font = 'custom-font'
    active = 'active'
    context = {
        'title_retard': title,
        'active_retard': active, 'font_facture': font}
    return render(request, 'all_page/facturation/facturation.html', context)


@schema_use
def facture_avoir(request):
    title = 'Facturation | Avoir'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    avoir = date_range(request, Avoir, datedeb, datefin, 'date_avoir')
    context = {
        'title_avoir': title,
        'active_avoir': active,
        'font_facture': font,
        'avoirs': avoir,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


class Calcule:
    @staticmethod
    def get_prix_m3(tarif, config) -> float:
        """Récupère le prix correspondant à l'id_config_branchement dans le tarif.prix_m3."""
        prix_m3_list = tarif.prix_m3 or []
        return next((item["prix"] for item in prix_m3_list if item["id"] == config.id_config_branchement), 0)

    @staticmethod
    def calculate_total_conso_ht(tarif, consommation, config) -> float:
        """Calcule le montant HT total basé sur le tarif et la consommation."""
        try:
            prix_m3 = Calcule.get_prix_m3(tarif, config)
            return prix_m3 * consommation
        except Exception as e:
            raise ValueError(f"Erreur lors du calcul du montant HT: {e}")

    @staticmethod
    def montant_taxe(tarif, total_conso_ht) -> list:
        """Calcule les taxes appliquées sur le montant HT."""
        try:
            taxes = Taxe.objects.filter(tarif=tarif)
            return [total_conso_ht * (taxe.taux_taxe / 100) for taxe in taxes]
        except Exception as e:
            raise ValueError(f"Erreur lors du calcul des taxes: {e}")

    @staticmethod
    def montant_ht(total_conso_ht, tarif_id, factures) -> MontantHT:
        """Crée et retourne un objet MontantHT."""
        try:
            return MontantHT.objects.create(
                total_conso_ht=round(total_conso_ht, 0),
                tarif_id=tarif_id,
                facture=factures,
            )
        except Exception as e:
            raise ValueError(f"Erreur lors de la création de MontantHT: {e}")

    @staticmethod
    def montant_ttc(total_conso_ttc, montant_ht) -> MontantTTC:
        """Crée et retourne un objet MontantTTC."""
        try:
            return MontantTTC.objects.create(
                total_conso_ttc=total_conso_ttc,
                montant_ht=montant_ht
            )
        except Exception as e:
            raise ValueError(f"Erreur lors de la création de MontantTTC: {e}")

    @staticmethod
    def cree_montant(tarif, consommation, factures, config, appliquer_tva=False) -> MontantHT:
        """Crée les montants HT et TTC avec ou sans TVA."""
        try:
            total_conso_ht = Calcule.calculate_total_conso_ht(tarif, consommation, config)
            montant_taxe = sum(Calcule.montant_taxe(tarif, total_conso_ht))
            montant_ht = Calcule.montant_ht(total_conso_ht, tarif.pk, factures)

            # Verification du taxe si on va l'appliquer dans tout taxe compris ou pas
            if config.taxe_applique:
                total_conso_ttc = total_conso_ht + montant_taxe + tarif.prix_location_compteur
            else:
                total_conso_ttc = total_conso_ht + tarif.prix_location_compteur

            if appliquer_tva:
                tva = (total_conso_ht * tarif.tva) / 100
                total_conso_ttc += tva
                factures.tva_appliquer = tva

            if montant_ht:
                Calcule.montant_ttc(total_conso_ttc, montant_ht)
            return montant_ht
        except Exception as e:
            raise ValueError(f"Erreur lors de la création des montants: {e}")


def precess_avoir_restant(contrat, factures):
    try:
        montant = MontantTTC.objects.get(montant_ht__facture_id=factures.pk)
        montant_total_ttc = montant.total_conso_ttc

        # Check if there is a credit note (avoir)
        avoir = Avoir.objects.filter(num_contrat=contrat.num_contrat).first()
        if avoir:
            factures.avoir_avant = avoir.montant_avoir
            if montant_total_ttc >= avoir.montant_avoir:
                montant_total_ttc -= avoir.montant_avoir
                factures.avoir_utilise = avoir.montant_avoir
                factures.montant_total_ttc = round(montant_total_ttc, 0)
                avoir.delete()
            else:
                factures.avoir_utilise = round(montant_total_ttc, 0)
                avoir.montant_avoir -= montant_total_ttc
                montant_total_ttc = 0
                avoir.save()
                factures.montant_total_ttc = 0

        # Check if there is a remaining balance (restant)
        restant = Restant.objects.filter(num_contrat=contrat.num_contrat).first()
        if restant:
            montant_total_ttc += restant.restant
            factures.restant_precedant = round(restant.restant, 0)
            factures.montant_total_ttc = round(montant_total_ttc, 0)
            restant.delete()

        else:
            factures.montant_total_ttc = round(montant_total_ttc, 0)

        return None

    except Exception as e:
        return HttpResponse(f"Error processing credit and remaining balance: {e}")


def facture_creation(date_facture, num_compteur, releve):
    try:
        contrat = get_object_or_404(Contrat, num_compteur_id=num_compteur)
        tarif = get_object_or_404(Tarif, cp_commune_id=contrat.cp_commune_id)
        type_client_id = contrat.client.type_client_id
        config = get_object_or_404(ConfigBranchement, type_client_id=type_client_id)
        consommation = releve.conso

        # Récupérer les relevés
        relever = ReleveCompteur.objects.filter(num_compteur_id=num_compteur)
        dernier_releve = relever.order_by('-date_releve')[1]  # Avant-dernier relevé
        date_relever = relever.latest('date_releve').date_releve
        date_echeance = date_relever + timedelta(days=tarif.nb_jour_echeance_fct)

        # Calculer les taxes appliquées une seule fois
        total_conso_ht = Calcule.calculate_total_conso_ht(tarif, consommation, config)
        taxes_appliquees = [
            {"id_taxe": taxe.id_taxe, "nom_taxe": taxe.nom_taxe, "montant_taxe": total_conso_ht * (taxe.taux_taxe / 100)}
            for taxe in Taxe.objects.filter(tarif_id=tarif.id_tarif)
        ]

        # Générer le numéro de facture
        date_facture_str = date_facture.strftime("%Y%m%d")
        num_facture = f"FACT{date_facture_str}{num_compteur}"

        # Créer la facture avec ou sans taxes selon config
        facture_data = {
            "num_facture": num_facture,
            "date_facture_precedant": dernier_releve.date_releve,
            "date_facture": date_facture,
            "date_echeance": date_echeance,
            "num_contrat_id": contrat.num_contrat,
            "relevecompteur_id": releve.pk,
            "taxes_appliquees": taxes_appliquees
        }

        factures = Facture.objects.create(**facture_data)

        # Calcul des montants avec ou sans TVA
        appliquer_tva = config.tva_applique and consommation >= tarif.conso_tva_app
        Calcule.cree_montant(tarif, consommation, factures, config, appliquer_tva=appliquer_tva)

        precess_avoir_restant(contrat, factures)
        factures.save()
        return factures

    except Contrat.DoesNotExist:
        return HttpResponse(f"Pas de contrat trouvé pour le numéro de compteur: {num_compteur}", status=404)
    except ConfigBranchement.DoesNotExist:
        return HttpResponse(f"ConfigBranchement non trouvé pour ce contrat: {num_compteur}", status=404)
    except Exception as e:
        return HttpResponse(f"Erreur lors de la création de la facture: {e}", status=500)


def facture_context_pdf(request, factures):
    try:
        montant = MontantHT.objects.get(facture=factures.pk)
        typeclient = factures.num_contrat.client.type_client_id
        num_compteur = factures.num_contrat.num_compteur_id
        compteur = Compteur.objects.get(pk=num_compteur)
        reveler_precedant = get_object_or_404(compteur.relevecompteurs, date_releve=factures.date_facture_precedant)
        relever_actuel = get_object_or_404(compteur.relevecompteurs, date_releve=factures.date_facture)

        # Plus simple : utiliser directement la date de la facture pour le mois
        # Mais en reculant d'un mois pour chaque date
        date_facture_precedant = factures.date_facture_precedant
        date_facture_actuel = factures.date_facture

        # Reculer d'un mois pour les dates actuelles et précédentes
        date_facture_actuel = get_previous_month(date_facture_actuel)
        date_facture_precedant = get_previous_month(date_facture_precedant)

        from Rel_Compteur.utils import montant_en_lettres
        lettre = montant_en_lettres(factures.montant_total_ttc)

        qr_code = generate_qr_code(request, factures.num_facture)
        paiement_exist = Paiement.objects.filter(facture_id=factures.pk).exists()

        context = {
            'instance': factures,
            'montant': montant,
            'typeclient': typeclient,
            'lettre': lettre,
            'reveler_precedant': reveler_precedant,
            'relever_actuel': relever_actuel,
            'date_facture_precedant': date_facture_precedant,  # Date de la facture pour l'affichage du mois
            'date_facture_actuel': date_facture_actuel,
            'montant_ht_total': round(montant.total_conso_ht, 0),
            'paiement_exist': paiement_exist,
            'qr_code': qr_code
        }
        return context

    except MontantHT.DoesNotExist:
        return HttpResponse(f"MontantHT n'exist pas pour le facture {factures.num_facture}", content_type='text/plain')
    except ReleveCompteur.DoesNotExist:
        return HttpResponse(f"ReleveCompteur n'exist pas pour le numéro de compteur "
                            f"{factures.num_contrat.num_compteur_id}", content_type='text/plain')
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", content_type='text/plain')


def is_eatc_schema(request) -> bool:
    id_entreprise = request.session.get('entreprise')
    entreprise = Entreprise.objects.get(pk=id_entreprise)
    return entreprise.schema_name == "eatc"


def encode_entreprise_images(entreprise, context):
    """Encode le logo et la signature de l'entreprise en base64 et les ajoute au contexte"""
    if entreprise.logo_entreprise:
        buffer = BytesIO()
        with open(entreprise.logo_entreprise.path, 'rb') as img_file:
            buffer.write(img_file.read())
        buffer.seek(0)
        context['logo_entreprise'] = base64.b64encode(buffer.getvalue()).decode()

    if entreprise.signature_entreprise:
        buffer = BytesIO()
        with open(entreprise.signature_entreprise.path, 'rb') as img_file:
            buffer.write(img_file.read())
        buffer.seek(0)
        context['signature_entreprise'] = base64.b64encode(buffer.getvalue()).decode()

    return context


def get_prix_m3_client(fact):
    """Récupère le prix selon le type de client"""
    try:
        type_client_id = fact.num_contrat.client.type_client_id
        tarif = Tarif.objects.get(cp_commune=fact.num_contrat.cp_commune)

        # Utilisation de next() pour une recherche plus efficace
        prix_trouve = next(
            (item['prix'] for item in (tarif.prix_m3 or [])
             if item.get('id') == type_client_id),
            None
        )
        return prix_trouve

    except (Tarif.DoesNotExist, AttributeError) as e:
        logger.error(f"Erreur récupération prix: {e}")
        return None


def get_derniers_montants_impayees(num_contrat, date_facture_actuelle):
    """Récupère les 3 derniers mois de factures impayées — seulement le montant_total_ttc"""
    try:
        montants = []

        # Boucle pour les 3 derniers mois
        for i in range(1, 4):  # 1, 2, 3 mois précédents
            # Calculer le mois précédent (i mois en arrière)
            mois_precedent = date_facture_actuelle.replace(day=1)
            for _ in range(i):
                if mois_precedent.month == 1:
                    mois_precedent = mois_precedent.replace(year=mois_precedent.year - 1, month=12)
                else:
                    mois_precedent = mois_precedent.replace(month=mois_precedent.month - 1)

            # Définir la plage du mois
            debut_mois = mois_precedent.replace(day=1)
            if mois_precedent.month == 12:
                fin_mois = mois_precedent.replace(year=mois_precedent.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fin_mois = mois_precedent.replace(month=mois_precedent.month + 1, day=1) - timedelta(days=1)

            # Récupérer seulement le montant_total_ttc des factures impayées (statut=False)
            facture_impayee = Facture.objects.filter(
                num_contrat_id=num_contrat,
                statut=False,  # Factures impayées
                date_facture__range=[debut_mois, fin_mois],
                montant_total_ttc__isnull=False  # S'assurer que le montant existe
            ).values('num_facture', 'date_facture', 'montant_total_ttc').order_by('date_facture').first()

            # MODIFICATION : Toujours ajouter un élément, même si pas de facture impayée
            if facture_impayee:
                # Reculer d'un mois la date de la facture impayée pour l'affichage (cohérence avec la logique métier)
                date_facture_originale = facture_impayee['date_facture']
                if date_facture_originale.month == 1:
                    date_facture_moins_un_mois = date_facture_originale.replace(year=date_facture_originale.year - 1, month=12)
                else:
                    date_facture_moins_un_mois = date_facture_originale.replace(month=date_facture_originale.month - 1)

                montants.append({
                    'num_facture': facture_impayee['num_facture'],
                    'date_facture': date_facture_moins_un_mois,  # Date reculée d'un mois pour cohérence
                    'montant_total_ttc': facture_impayee['montant_total_ttc']
                })

        return montants

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des montants impayés: {e}")
        return []


def calculer_total_net_a_payer(montant_actuel, montants_impayees):
    """Calcule le total net à payer (montant actuel + impayés précédents)"""
    try:
        total_impayees = sum(factures['montant_total_ttc'] for factures in montants_impayees)
        total_net_a_payer = montant_actuel + total_impayees
        return total_net_a_payer
    except Exception as e:
        logger.error(f"Erreur lors du calcul du total net à payer: {e}")


@schema_use
def facture_genere_pdf(request, num_facture):
    try:
        factures = Facture.objects.get(num_facture=num_facture)

        # Utilisation de la fonction utilitaire pour préparer le contexte
        from Rel_Compteur.utils import prepare_facture_context
        context, error_response = prepare_facture_context(request, factures)

        if error_response:
            return error_response

        # Déterminer le template à utiliser
        template_path = 'all_page/facturation/facture/{}'.format(
            'templatepdf.html' if is_eatc_schema(request) else 'templatenoeatc.html'
        )

        filename_prefix = f"{factures.num_facture}-({datetime.now().strftime('%d/%m/%Y')})"
        return generate_pdf(request, context, template_path, filename_prefix)
    except Facture.DoesNotExist:
        messages.error(request, f"La facture {num_facture} n'existe pas")
        return redirect('facture')
    except Exception as e:
        messages.error(request, F"Erreur lors de la génération du PDF {e}")
        return redirect('facture')


def render_html_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    return html


@schema_use
def generate_multiple_pages_pdf(request):
    try:
        # Récupération des paramètres de requête
        date_deb = request.GET.get('date_deb')
        date_fin = request.GET.get('date_fin')
        commune = request.GET.get('commune')
        num_client_deb = request.GET.get('num_client_deb')
        num_client_fin = request.GET.get('num_client_fin')

        # Si aucune date n'est fournie, utiliser le mois actuel pour les factures impayées
        if not date_deb and not date_fin:
            date_deb, date_fin = get_default_month_range()

        # Configuration des paramètres de performance
        batch_size = 4  # Taille des lots alignée sur le nombre de factures par page

        # Préparation de la requête de base avec select_related et prefetch_related
        factures = Facture.objects.filter(statut=False).select_related(
            'num_contrat',
            'num_contrat__client',
            'relevecompteur'
        ).prefetch_related(
            'montantht_set',
            'montantht_set__montantttc'  # Relation OneToOneField vers MontantTTC
        ).order_by("num_contrat_id__adresse_contrat")

        factures = filter_by_client_number(
            queryset=factures,
            client_field='num_contrat__client__num_client',
            num_client_deb=num_client_deb,
            num_client_fin=num_client_fin
        )

        # Filtrage initial
        if date_deb and date_fin:
            date_deb, _ = get_month_range(date_deb)
            _, date_fin = get_month_range(date_fin)
            factures = factures.filter(date_facture__range=[date_deb, date_fin])

        # Vérifier si une commune valide est sélectionnée
        if not commune or commune.lower() == 'null':
            messages.warning(request, "Veuillez sélectionner une commune")
            return redirect('facture')

        # Appliquer le filtre de commune
        factures = factures.filter(num_contrat__cp_commune=commune)

        # Vérification des résultats
        factures = list(factures)  # Force l'évaluation de la requête
        if not factures:
            messages.warning(request, "Aucune facture trouvée pour les critères sélectionnés")
            return redirect('facture')

        # Initialisation des variables
        html_sections = []
        eatc = is_eatc_schema(request)
        template_name = 'all_page/facturation/facture/{}'.format(
            'templatepdf.html' if eatc else 'templatenoeatc.html'
        )
        template = get_template(template_name)

        # Import de la fonction utilitaire
        from Rel_Compteur.utils import prepare_facture_context

        # Traitement par lots
        for i in range(0, len(factures), batch_size):
            batch = factures[i:i + batch_size]
            temp_group = []

            for fact in batch:
                try:
                    # Utilisation de la fonction utilitaire pour préparer le contexte
                    context, error_response = prepare_facture_context(request, fact)
                    if error_response:
                        return error_response

                    # Rendu du template
                    html = template.render(context)
                    temp_group.append(html)

                    # Nettoyage de la mémoire
                    del context

                except Exception as e:
                    logger.error(
                        f"Erreur lors du traitement de la facture {getattr(fact, 'num_facture', 'inconnu')}: {str(e)}")
                    continue

            # Gestion uniforme des groupes de 4 pour tous les cas
            if temp_group:
                for j in range(0, len(temp_group), 4):
                    group = temp_group[j:j + 4]
                    html_sections.append(''.join(group))

            # Nettoyage de la mémoire après chaque lot
            del temp_group
            gc.collect()

        # Vérification des sections générées
        if not html_sections:
            messages.error(request, "Aucun contenu généré pour les factures sélectionnées")
            return redirect('facture')

        # Génération du PDF final avec gestion de la mémoire
        try:
            # Configuration de pisa
            pdf_options = {
                'quiet': True,
                'encoding': 'UTF-8',
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'load_file': False,
                'raise_exception': True,
                'default_font': 'Helvetica'
            }

            # Préparation du contenu HTML
            # Échapper les accolades dans le CSS en les doublant
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>@page {{ size: A4; margin: 1cm; }}</style>
            </head>
            <body>
                {0}
            </body>
            </html>
            """.format('<div style="page-break-after: always;"></div>'.join(html_sections))

            # Génération du PDF
            result = BytesIO()
            pdf = pisa.pisaDocument(
                BytesIO(html_content.encode('utf-8')),
                result,
                **pdf_options
            )

            if pdf.err:
                error_msg = ', '.join(str(err) for err in pdf.log if err.severity > 40)
                raise ValueError(f"Erreur Pisa: {error_msg}")

            if not result.getvalue():
                raise ValueError("Le PDF généré est vide")

            # Préparation de la réponse
            filename = f"Factures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            response = HttpResponse(
                result.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            # Nettoyage final
            del html_sections
            del html_content
            result.close()
            gc.collect()

            return response

        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF: {str(e)}", exc_info=True)
            messages.error(request, "Une erreur est survenue lors de la génération du PDF final")
            return redirect('facture')

    except Exception as e:
        logger.error(f"Erreur critique dans generate_multiple_pages_pdf: {str(e)}", exc_info=True)
        messages.error(request, "Une erreur est survenue lors du traitement de votre demande")
        return redirect('facture')


def paiement(id_releve, montant_payer, utilisateur):
    with transaction.atomic():
        fact_paiement = Facture.objects.select_for_update().get(relevecompteur_id=id_releve)
        num_contrat = fact_paiement.num_contrat_id

        # Vérifier le montant total déjà payé pour cette facture
        total_deja_paye = Paiement.objects.filter(facture_id=fact_paiement.pk).aggregate(
            total=models.Sum('montant_payer'))['total'] or 0

        # Créer un nouveau paiement
        Paiement.objects.create(
            montant_payer=montant_payer,
            facture_id=fact_paiement.pk,
            date_paiement=timezone.now()
        )

        # Calculer le nouveau total payé
        nouveau_total_paye = total_deja_paye + montant_payer

        # Enregistrer la recette
        enregistrer_recette_paiement(
            facture_id=fact_paiement.pk,
            montant=montant_payer,
            utilisateur_id=utilisateur,
            date_encaissement=timezone.now().date()
        )

        if nouveau_total_paye >= fact_paiement.montant_total_ttc:
            # Il y a un surplus
            surplus = nouveau_total_paye - fact_paiement.montant_total_ttc

            # Créer ou mettre à jour l'avoir avec le surplus
            avoir = Avoir.objects.filter(num_contrat=num_contrat).first()
            if avoir:
                avoir.montant_avoir += round(surplus, 0)
                avoir.save()
            else:
                Avoir.objects.create(
                    montant_avoir=round(surplus, 0),
                    utilisateur_id=utilisateur,
                    num_contrat_id=num_contrat
                )

            fact_paiement.avoir_nouveau = round(surplus, 0)
            fact_paiement.restant_nouvel = None

            # Supprimer le restant car tout est payé
            Restant.objects.filter(num_contrat=num_contrat).delete()

        else:
            # Il reste un montant à payer
            nouveau_restant = fact_paiement.montant_total_ttc - nouveau_total_paye

            # Mettre à jour ou créer le restant
            restant = Restant.objects.filter(num_contrat=num_contrat).first()
            if restant:
                restant.restant = round(nouveau_restant, 0)
                restant.date_restant = timezone.now()
                restant.utilisateur_id = utilisateur
                restant.save()
            else:
                Restant.objects.create(
                    restant=round(nouveau_restant, 0),
                    num_contrat_id=num_contrat,
                    utilisateur_id=utilisateur,
                    date_restant=timezone.now()
                )

            fact_paiement.restant_nouvel = round(nouveau_restant, 0)
            fact_paiement.avoir_nouveau = None

        # Marquer la facture comme payée dès qu'un paiement est effectué
        fact_paiement.statut = True
        fact_paiement.save()


@schema_use
def facture_paiement(request):
    try:
        id_releve = request.POST['id_releve']
        montant_payer = float(request.POST['paiement'])
        utilisateur = request.session.get('id_utilisateur')

        with transaction.atomic():
            fact = Facture.objects.select_for_update().get(relevecompteur_id=id_releve)

            # Vérifier s'il existe déjà un paiement pour cette facture
            paiement_existant = Paiement.objects.filter(facture=fact).first()
            if paiement_existant:
                # Si un paiement existe mais que le statut de la facture est False, on le met à jour
                if not fact.statut:
                    fact.statut = True
                    fact.save()
                    messages.success(request, 'Le statut de la facture a été mis à jour avec succès')
                    return redirect('facture_etat_detail', fact.num_facture)

            # On autorise toujours le paiement si la facture a un restant
            if fact.statut and not fact.restant_nouvel:
                messages.error(request, 'Cette facture est déjà totalement payée')
                return redirect('facture_etat_detail', fact.num_facture)

            # # Vérifier s'il existe une facture plus récente
            # existe_facture_recente = Facture.objects.filter(
            #     num_contrat=fact.num_contrat,
            #     date_facture__gt=fact.date_facture
            # ).exists()
            #
            # if existe_facture_recente and not fact.restant_nouvel:
            #     messages.error(request, 'Une facture plus récente existe déjà')
            #     return redirect('facture_etat_detail', fact.num_facture)

            paiement(id_releve, montant_payer, utilisateur)
            messages.success(request, 'Paiement effectué avec succès !')
            return redirect('facture_etat_detail', fact.num_facture)

    except Facture.DoesNotExist:
        messages.error(request, 'Facture introuvable')
        return redirect('facture')
    except Exception as e:
        logger.error(f"Erreur lors du paiement: {str(e)}", exc_info=True)
        messages.error(request, 'Une erreur est survenue lors du paiement')
        return redirect('facture')


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def facture_export_excel(request):
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    commune = request.GET.get('commune')

    factures = Facture.objects.all()
    nom_fichier = f"facture.xlsx"
    factures = date_range_fact_pdf(date_deb, date_fin, commune, factures)

    champs = [
        'num_facture',
        'date_facture',
        'montant_total_ttc',
        'avoir_avant',
        'avoir_utilise',
        'restant_precedant',
        'restant_nouvel',
        'statut',
        'num_contrat',
    ]

    nom_colonnes = [
        'Numéro Facture',
        'Date Facture',
        'Montant Total TTC',
        'Avoir avant',
        'Avoir Utilisé',
        'Restant Precedant',
        'Restant Nouvel',
        'Status',
        'Numéro Contrat'
    ]
    response = exporter_en_excel(factures, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout de facture"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response


def generate_qr_code(request, num_facture):
    data = num_facture

    # Création de l'objet QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Création de l'image QR code
    img = qr.make_image(fill_color="black", back_color="white")

    # Conversion de l'image en réponse HTTP
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()
