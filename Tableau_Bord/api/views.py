"""
Vues API REST pour le Tableau de Bord (Dashboard) Admin/Gestionnaire.

Ces endpoints utilisent les fonctions utilitaires existantes de views.py
et fournissent des réponses standardisées via ApiResponse pour l'application mobile.

Contrairement aux endpoints existants (JsonResponse simples), ces APIs utilisent
DRF avec authentification JWT et permissions par rôle.

Endpoints:
    GET /api/admin/dashboard/kpi/ - KPI globaux
    GET /api/admin/dashboard/evo-conso/ - Évolution consommation
    GET /api/admin/dashboard/factures-statut/ - Statut factures
    GET /api/admin/dashboard/anomalies-statut/ - Statut anomalies
"""

import logging
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.db.models.functions import ExtractYear, ExtractMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes

from Rel_Compteur.api_utils import ApiResponse
from Tenants.middleware import schema_use_api
from Login.permissions import IsAdminOuGestionnaire

from Facturation.models import Facture, Paiement
from Clients.models import Client
from Compteurs.models import ReleveCompteur, Compteur
from Main_Courante.models import MainCourante, StatutMC
from Depense.models import Transactions as Depense
from Recette.models import Recette

# Import des fonctions utilitaires existantes de views.py
from Tableau_Bord.views import _get_filtered_queryset

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAdminOuGestionnaire])
@schema_use_api
def dashboard_kpi(request):
    """
    Récupère les KPI globaux du tableau de bord.
    
    Pour Administrateur : Données globales (toutes communes)
    Pour Gestionnaire : Données limitées à sa commune
    
    Query Params:
        - date_deb: Date de début (YYYY-MM-DD, optionnel)
        - date_fin: Date de fin (YYYY-MM-DD, optionnel)
    
    Returns:
        {
            "chiffre_affaires": float,
            "nombre_clients": int,
            "nombre_compteurs": int,
            "total_recettes": float,
            "total_depenses": float,
            "resultat_net": float,
            "taux_recouvrement": float,
            "nombre_factures_impayees": int,
            "nombre_anomalies_en_cours": int,
            "periode": {"debut": str, "fin": str}
        }
    """
    try:
        # Déterminer la période (mois courant par défaut)
        date_deb_str = request.GET.get('date_deb')
        date_fin_str = request.GET.get('date_fin')
        
        if date_deb_str and date_fin_str:
            try:
                date_deb = datetime.strptime(date_deb_str, '%Y-%m-%d').date()
                date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            except ValueError:
                return ApiResponse.error(
                    "Format de date invalide. Utilisez YYYY-MM-DD.",
                    code="INVALID_DATE_FORMAT",
                    http_status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Mois courant
            now = timezone.now()
            date_deb = now.replace(day=1)
            if now.month == 12:
                date_fin = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_fin = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
        
        # Utiliser la fonction utilitaire existante pour le filtrage
        # 1. Chiffre d'affaires (total des paiements encaissés)
        chiffres_query = _get_filtered_queryset(
            request, 
            Paiement, 
            'facture__num_contrat__cp_commune_id', 
            'facture__num_contrat__cp_commune', 
            'date_paiement',
            default_to_year=False
        )
        chiffres_query = chiffres_query.filter(date_paiement__range=[date_deb, date_fin])
        chiffre_affaires = chiffres_query.aggregate(total=Sum('montant_payer'))['total'] or 0
        
        # 2. Nombre de clients actifs
        clients_query = _get_filtered_queryset(
            request,
            Client,
            'cp_commune_id',
            'cp_commune',
            None
        )
        nombre_clients = clients_query.filter(compte_actif=True).count()
        
        # 3. Nombre de compteurs
        compteurs_query = _get_filtered_queryset(
            request,
            Compteur,
            'contrats__cp_commune_id',
            'contrats__cp_commune',
            None
        )
        nombre_compteurs = compteurs_query.distinct().count()
        
        # 4. Total recettes
        recettes_query = _get_filtered_queryset(
            request,
            Recette,
            'facture__num_contrat__cp_commune_id',
            'facture__num_contrat__cp_commune',
            'date_encaissement',
            default_to_year=False
        )
        recettes_query = recettes_query.filter(date_encaissement__range=[date_deb, date_fin])
        total_recettes = recettes_query.aggregate(total=Sum('montant'))['total'] or 0
        
        # 5. Total dépenses
        depenses_query = _get_filtered_queryset(
            request,
            Depense,
            'utilisateur__cp_commune_id',
            'utilisateur__cp_commune',
            'date_transaction',
            default_to_year=False
        )
        depenses_query = depenses_query.filter(date_transaction__range=[date_deb, date_fin])
        total_depenses = depenses_query.aggregate(total=Sum('montant'))['total'] or 0
        
        # 6. Résultat net
        resultat_net = total_recettes - total_depenses
        
        # 7. Taux de recouvrement (factures payées / total factures)
        factures_query = _get_filtered_queryset(
            request,
            Facture,
            'num_contrat__cp_commune_id',
            'num_contrat__cp_commune',
            'date_facture'
        )
        total_factures = factures_query.count()
        factures_payees = factures_query.filter(statut=True).count()
        taux_recouvrement = (factures_payees / total_factures * 100) if total_factures > 0 else 0
        
        # 8. Nombre de factures impayées (en retard)
        factures_impayees_query = _get_filtered_queryset(
            request,
            Facture,
            'num_contrat__cp_commune_id',
            'num_contrat__cp_commune',
            'date_echeance'
        )
        nombre_factures_impayees = factures_impayees_query.filter(
            statut=False,
            date_echeance__lt=timezone.now().date()
        ).count()
        
        # 9. Nombre d'anomalies en cours
        anomalies_query = _get_filtered_queryset(
            request,
            StatutMC,
            'main_courante__cp_commune_id',
            'main_courante__cp_commune',
            'date_status'
        )
        nombre_anomalies_en_cours = anomalies_query.filter(
            en_cours=True,
            main_courante__is_deleted=False
        ).distinct().count()
        
        return ApiResponse.success(
            data={
                'chiffre_affaires': round(chiffre_affaires, 2),
                'nombre_clients': nombre_clients,
                'nombre_compteurs': nombre_compteurs,
                'total_recettes': round(total_recettes, 2),
                'total_depenses': round(total_depenses, 2),
                'resultat_net': round(resultat_net, 2),
                'taux_recouvrement': round(taux_recouvrement, 2),
                'nombre_factures_impayees': nombre_factures_impayees,
                'nombre_anomalies_en_cours': nombre_anomalies_en_cours,
                'periode': {
                    'debut': date_deb.isoformat(),
                    'fin': date_fin.isoformat(),
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Erreur dashboard KPI: {str(e)}")
        return ApiResponse.server_error(f"Erreur lors de la récupération des KPI: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAdminOuGestionnaire])
@schema_use_api
def dashboard_evo_conso(request):
    """
    Récupère l'évolution de la consommation sur les 6 derniers mois.
    
    Query Params:
        - commune: ID de la commune (optionnel, automatique pour Gestionnaire)
    
    Returns:
        {
            "mois": ["Juillet", "Août", ...],
            "consommations": [volume_m3, ...],
            "evolution_pourcentage": [%, ...]
        }
    """
    try:
        # 6 derniers mois
        now = timezone.now()
        mois_data = []
        
        for i in range(5, -1, -1):
            if now.month - i <= 0:
                mois = now.month - i + 12
                annee = now.year - 1
            else:
                mois = now.month - i
                annee = now.year
            
            # Nom du mois en français
            noms_mois = {
                1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
                5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
                9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
            }
            
            # Utiliser la fonction utilitaire pour le filtrage
            conso_query = _get_filtered_queryset(
                request,
                ReleveCompteur,
                'num_compteur__contrats__cp_commune_id',
                'num_compteur__contrats__cp_commune',
                'date_releve',
                default_to_year=False
            )
            
            # Filtrer par mois et exclure les rejetés
            conso_query = conso_query.filter(
                date_releve__month=mois,
                date_releve__year=annee
            ).exclude(
                statut_validation='REJETE'
            ).filter(
                is_deleted=False
            )
            
            # Consommation du mois
            conso = conso_query.aggregate(total=Sum('conso'))['total'] or 0
            
            mois_data.append({
                'mois': noms_mois[mois],
                'annee': annee,
                'consommation': conso,
            })
        
        # Calculer l'évolution en pourcentage
        consommations = [m['consommation'] for m in mois_data]
        evolution = [0]  # Premier mois : pas d'évolution
        for i in range(1, len(consommations)):
            if consommations[i-1] > 0:
                evol = ((consommations[i] - consommations[i-1]) / consommations[i-1]) * 100
                evolution.append(round(evol, 2))
            else:
                evolution.append(0)
        
        return ApiResponse.success(
            data={
                'mois': [m['mois'] for m in mois_data],
                'consommations': consommations,
                'evolution_pourcentage': evolution,
            }
        )
    
    except Exception as e:
        logger.error(f"Erreur évolution conso: {str(e)}")
        return ApiResponse.server_error(f"Erreur lors de la récupération de l'évolution: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAdminOuGestionnaire])
@schema_use_api
def dashboard_factures_statut(request):
    """
    Récupère la répartition des factures par statut (payées/impayées).
    
    Query Params:
        - date_deb: Date de début (YYYY-MM-DD, optionnel)
        - date_fin: Date de fin (YYYY-MM-DD, optionnel)
    
    Returns:
        {
            "total_factures": int,
            "payees": {"nombre": int, "montant": float},
            "impayees": {"nombre": int, "montant": float},
            "en_retard": {"nombre": int, "montant": float},
            "par_mois": [...]
        }
    """
    try:
        # Déterminer la période (6 derniers mois par défaut)
        date_deb_str = request.GET.get('date_deb')
        date_fin_str = request.GET.get('date_fin')
        
        if date_deb_str and date_fin_str:
            date_deb = datetime.strptime(date_deb_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        else:
            # 6 derniers mois
            now = timezone.now()
            date_fin = now.date()
            date_deb = date_fin - timedelta(days=180)
        
        # Utiliser la fonction utilitaire pour le filtrage
        factures_query = _get_filtered_queryset(
            request,
            Facture,
            'num_contrat__cp_commune_id',
            'num_contrat__cp_commune',
            'date_facture',
            default_to_year=False
        )
        factures_query = factures_query.filter(date_facture__range=[date_deb, date_fin])
        
        # Total factures
        total_factures = factures_query.count()
        
        # Factures payées
        payees_data = factures_query.filter(statut=True).aggregate(
            nombre=Count('id_facture'),
            montant=Sum('montant_total_ttc')
        )
        
        # Factures impayées
        impayees_data = factures_query.filter(statut=False).aggregate(
            nombre=Count('id_facture'),
            montant=Sum('montant_total_ttc')
        )
        
        # Factures en retard (échéance dépassée)
        en_retard_data = factures_query.filter(
            statut=False,
            date_echeance__lt=timezone.now().date()
        ).aggregate(
            nombre=Count('id_facture'),
            montant=Sum('montant_total_ttc')
        )
        
        # Répartition par mois
        par_mois_query = factures_query.annotate(
            mois=ExtractMonth('date_facture'),
            annee=ExtractYear('date_facture'),
        ).values('mois', 'annee').annotate(
            total=Count('id_facture'),
            payees=Count('id_facture', filter=Q(statut=True)),
            impayees=Count('id_facture', filter=Q(statut=False)),
            montant_total=Sum('montant_total_ttc')
        ).order_by('annee', 'mois')
        
        par_mois = []
        for item in par_mois_query:
            par_mois.append({
                'mois': f"{item['annee']}-{item['mois']:02d}",
                'total': item['total'],
                'payees': item['payees'],
                'impayees': item['impayees'],
                'montant_total': item['montant_total'] or 0,
            })
        
        return ApiResponse.success(
            data={
                'total_factures': total_factures,
                'payees': {
                    'nombre': payees_data['nombre'] or 0,
                    'montant': payees_data['montant'] or 0,
                },
                'impayees': {
                    'nombre': impayees_data['nombre'] or 0,
                    'montant': impayees_data['montant'] or 0,
                },
                'en_retard': {
                    'nombre': en_retard_data['nombre'] or 0,
                    'montant': en_retard_data['montant'] or 0,
                },
                'par_mois': par_mois,
            }
        )
    
    except Exception as e:
        logger.error(f"Erreur statut factures: {str(e)}")
        return ApiResponse.server_error(f"Erreur lors de la récupération des statuts: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAdminOuGestionnaire])
@schema_use_api
def dashboard_anomalies_statut(request):
    """
    Récupère le statut des anomalies (main courante).
    
    Query Params:
        - date_deb: Date de début (YYYY-MM-DD, optionnel)
        - date_fin: Date de fin (YYYY-MM-DD, optionnel)
    
    Returns:
        {
            "total": int,
            "non_traite": {"nombre": int, "pourcentage": float},
            "en_cours": {"nombre": int, "pourcentage": float},
            "realise": {"nombre": int, "pourcentage": float},
            "par_type": [...],
            "recentes": [...]
        }
    """
    try:
        # Déterminer la période (mois courant par défaut)
        date_deb_str = request.GET.get('date_deb')
        date_fin_str = request.GET.get('date_fin')
        
        if date_deb_str and date_fin_str:
            date_deb = datetime.strptime(date_deb_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        else:
            # Mois courant
            now = timezone.now()
            date_deb = now.replace(day=1)
            if now.month == 12:
                date_fin = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_fin = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
        
        # Utiliser la fonction utilitaire pour le filtrage
        anomalies_query = _get_filtered_queryset(
            request,
            MainCourante,
            'cp_commune_id',
            'cp_commune',
            'date_mc',
            default_to_year=False
        )
        anomalies_query = anomalies_query.filter(
            date_mc__range=[date_deb, date_fin],
            is_deleted=False
        )
        
        # Compter par statut (en utilisant prefetch_related pour éviter N+1)
        anomalies_query = anomalies_query.prefetch_related('statuts')
        
        non_traite = 0
        en_cours = 0
        realise = 0
        
        for mc in anomalies_query:
            statut = mc.statuts.first()
            if statut:
                if statut.non_traite:
                    non_traite += 1
                elif statut.en_cours:
                    en_cours += 1
                elif statut.realise:
                    realise += 1
        
        total = non_traite + en_cours + realise
        
        # Par type d'anomalie
        par_type = anomalies_query.values(
            'type_anomalie'
        ).annotate(
            nombre=Count('id_mc')
        ).order_by('-nombre')
        
        # Anomalies récentes (7 derniers jours)
        recentes = anomalies_query.filter(
            date_mc__gte=timezone.now().date() - timedelta(days=7)
        ).order_by('-date_mc')[:5].values(
            'id_mc',
            'type_anomalie',
            'date_mc',
            'description_mc',
        )
        
        # Calculer les pourcentages
        def pourcentage(valeur):
            return round((valeur / total * 100), 2) if total > 0 else 0
        
        return ApiResponse.success(
            data={
                'total': total,
                'non_traite': {
                    'nombre': non_traite,
                    'pourcentage': pourcentage(non_traite),
                },
                'en_cours': {
                    'nombre': en_cours,
                    'pourcentage': pourcentage(en_cours),
                },
                'realise': {
                    'nombre': realise,
                    'pourcentage': pourcentage(realise),
                },
                'par_type': list(par_type),
                'recentes': list(recentes),
            }
        )
    
    except Exception as e:
        logger.error(f"Erreur statut anomalies: {str(e)}")
        return ApiResponse.server_error(f"Erreur lors de la récupération des anomalies: {str(e)}")
