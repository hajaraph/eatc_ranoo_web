from datetime import timedelta, datetime

from django.db import connection
from django.db.models import Sum, Value, Count, Q, F
from django.db.models.functions import Coalesce, ExtractYear, ExtractMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from Clients.models import Contrat
from Compteurs.models import ReleveCompteur
from Depense.models import Transactions
from Facturation.models import Paiement, Facture
from Login.views import role_requis
from Main_Courante.models import StatutMC
from Acommune.models import Region, Commune
from Recette.models import Recette
from Rubrique.models import DebitEau, Marnage
from Tenants.middleware import schema_use
from Rel_Compteur.utils import filter_by_user_role


# FONCTION D'ASSISTANCE POUR LE FILTRAGE
# =================================================
def _get_filtered_queryset(request, model, role_filter_path, region_filter_path, date_filter_path, default_to_year=True):
    """
    Applique les filtres communs (rôle, région, date) à un queryset.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    queryset = model.objects.all()
    if role_filter_path:
        queryset = filter_by_user_role(request, queryset, role_filter_path)

    if region and region_filter_path:
        queryset = queryset.filter(**{f'{region_filter_path}': region})

    if date_filter_path:
        if date_deb and date_fin:
            queryset = queryset.filter(**{f'{date_filter_path}__range': [date_deb, date_fin]})
        elif default_to_year:
            annee_actuelle = timezone.now().year
            queryset = queryset.filter(**{f'{date_filter_path}__year': annee_actuelle})

    return queryset


# VUE PRINCIPALE : CHARGE UNIQUEMENT LE TEMPLATE
# =================================================
@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def tableau_bord(request):
    font = 'custom-font'
    regions = Region.objects.all()
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    context = {
        'font_tableau': font,
        'regions': regions,
        'datedeb': date_deb if date_deb else '',
        'datefin': date_fin if date_fin else '',
    }
    return render(request, 'all_page/tableau_bord.html', context)


# VUES API : FOURNISSENT LES DONNÉES AU FORMAT JSON
# ==================================================

@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_kpi_globaux(request):
    date_actuelle = timezone.now()
    annee_actuelle = date_actuelle.year
    annee_precedente = annee_actuelle - 1

    # --- Chiffre d'affaires ---
    chiffres_query = _get_filtered_queryset(request, Paiement, 'facture__num_contrat__cp_commune_id', 'facture__num_contrat__cp_commune__region', 'facture__relevecompteur__date_releve', default_to_year=False)
    chiffres = chiffres_query.aggregate(Sum('montant_payer'))['montant_payer__sum'] or 0

    # --- Nombre de clients ---
    contrats_actuels_query = _get_filtered_queryset(request, Contrat, 'cp_commune_id', 'cp_commune__region', 'date_debut')
    contrats_prec_query = _get_filtered_queryset(request, Contrat, 'cp_commune_id', 'cp_commune__region', 'date_debut', default_to_year=False).filter(date_debut__year=annee_precedente)

    # --- Recettes et Dépenses ---
    recettes_query = _get_filtered_queryset(request, Recette, 'facture__num_contrat__cp_commune_id', 'facture__num_contrat__cp_commune__region', 'date_encaissement')
    depenses_query = _get_filtered_queryset(request, Transactions, 'utilisateur__cp_commune_id', 'utilisateur__cp_commune__region', 'date_transaction')

    total_recettes = recettes_query.aggregate(total=Sum('montant'))['total'] or 0
    total_depenses = depenses_query.aggregate(total=Sum('montant'))['total'] or 0
    resultat_net = total_recettes - total_depenses

    data = {
        'chiffres': round(chiffres, 2),
        'nb_client_actuelle': contrats_actuels_query.count(),
        'annee_contrat_prec': annee_precedente,
        'nb_client_prec': contrats_prec_query.count(),
        'annee_contrat_actuelle': annee_actuelle,
        'total_recettes': total_recettes,
        'total_depenses': total_depenses,
        'resultat_net': resultat_net,
    }
    return JsonResponse(data)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_evo_conso_commune(request):
    # Cette vue a une logique de filtrage plus spécifique, on ne la refactorise pas avec l'helper.
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    commune_query = filter_by_user_role(request, Commune.objects.all(), 'id')
    if region:
        commune_query = commune_query.filter(region_id=region)

    conso_filters = Q()
    if date_deb and date_fin:
        conso_filters &= Q(contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin])
    else:
        conso_filters &= Q(contrat__num_compteur__relevecompteurs__date_releve__year=timezone.now().year)

    commune_query = commune_query.annotate(
        total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso', filter=conso_filters), Value(0))
    ).exclude(total_conso=0)

    resultats = []
    for communes in commune_query:
        evo_conso_commune = communes.contrat_set.annotate(
            mois_releve=ExtractMonth('num_compteur__relevecompteurs__date_releve'),
            annee_releve=ExtractYear('num_compteur__relevecompteurs__date_releve')
        ).values('mois_releve', 'annee_releve').annotate(
            total_conso=Coalesce(Sum('num_compteur__relevecompteurs__conso'), Value(0))
        ).order_by('annee_releve', 'mois_releve').exclude(total_conso=0)

        resultats.append({
            'commune': f'{communes.region.region} {communes.commune}',
            'data': list(evo_conso_commune)
        })

    return JsonResponse(resultats, safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_statut_factures(request):
    factures_query = _get_filtered_queryset(request, Facture, 'num_contrat__cp_commune_id', 'num_contrat__cp_commune__region', 'date_facture')
    factures_data = factures_query.annotate(
        mois=ExtractMonth('date_facture'),
        annee=ExtractYear('date_facture'),
    ).values('mois', 'annee').annotate(
        nombre_factures_payees=Count('id_facture', filter=Q(statut=True)),
        nombre_factures_impayees=Count('id_facture', filter=Q(statut=False))
    ).order_by('annee', 'mois')
    return JsonResponse(list(factures_data), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_statut_main_courante(request):
    mc_query = _get_filtered_queryset(request, StatutMC, 'main_courante__cp_commune_id', 'main_courante__cp_commune__region', 'date_status')
    mc_data = mc_query.annotate(
        mois=ExtractMonth('main_courante__date_mc'),
        annee=ExtractYear('main_courante__date_mc'),
    ).values('mois', 'annee').annotate(
        nb_non_traite=Count('main_courante_id', filter=Q(non_traite=True)),
        nb_realise=Count('main_courante_id', filter=Q(realise=True)),
        nb_en_cours=Count('main_courante_id', filter=Q(en_cours=True))
    ).order_by('annee', 'mois')
    return JsonResponse(list(mc_data), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_factures_par_type_client(request):
    base_query = _get_filtered_queryset(request, Facture, 'num_contrat__cp_commune_id', 'num_contrat__cp_commune__region', 'relevecompteur__date_releve')
    factures_par_type_client = (
        base_query
        .annotate(
            mois=ExtractMonth('relevecompteur__date_releve'),
            annee=ExtractYear('relevecompteur__date_releve'),
            type_client=Coalesce('num_contrat__client__type_client__designation_client', Value('Non spécifié')),
            commune_nom=F('num_contrat__cp_commune__commune')
        )
        .values('mois', 'annee', 'type_client', 'commune_nom')
        .annotate(
            total=Count('id_facture'),
            montant_total=Coalesce(Sum('montant_total_ttc'), Value(0.0)),
            payees=Count('id_facture', filter=Q(statut=True)),
            impayees=Count('id_facture', filter=Q(statut=False)),
            montant_total_payees=Coalesce(Sum('paiements__montant_payer'), Value(0.0)) - Coalesce(Sum('montantht__tarif__prix_location_compteur', filter=Q(statut=True)), Value(0.0)),
            montant_total_impayees=(Coalesce(Sum('restant_nouvel'), Value(0.0)) + Coalesce(Sum('montant_total_ttc', filter=Q(statut=False)), Value(0.0))) - Coalesce(Sum('montantht__tarif__prix_location_compteur', filter=Q(statut=False)), Value(0.0)),
            volume_paye=Coalesce(Sum('relevecompteur__conso', filter=Q(statut=True)), Value(0)),
            volume_impaye=Coalesce(Sum('relevecompteur__conso', filter=Q(statut=False)), Value(0)),
            montant_paye=Coalesce(Sum('paiements__montant_payer'), Value(0.0))
        )
        .order_by('commune_nom', 'annee', 'mois', 'type_client')
    )
    return JsonResponse(list(factures_par_type_client), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_conso_par_type_client(request):
    conso_query = _get_filtered_queryset(request, ReleveCompteur, 'num_compteur__contrats__cp_commune_id', 'num_compteur__contrats__cp_commune__region', 'date_releve')
    types_client_conso = (
        conso_query
        .annotate(
            mois=ExtractMonth('date_releve'),
            annee=ExtractYear('date_releve'),
            designation_client=Coalesce('num_compteur__contrats__client__type_client__designation_client', Value('Non spécifié')),
            commune_nom=F('num_compteur__contrats__cp_commune__commune')
        )
        .values('designation_client', 'mois', 'annee', 'commune_nom')
        .annotate(conso_mensuelle=Sum('conso'))
        .filter(conso_mensuelle__gt=0)
        .order_by('commune_nom', 'annee', 'mois', 'designation_client')
    )
    return JsonResponse(list(types_client_conso), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_debit_par_commune(request):
    debit_query = _get_filtered_queryset(request, DebitEau, None, 'cp_commune__region', 'date_creation', default_to_year=False)
    debit_par_commune = debit_query.values(
        'cp_commune_id', 'cp_commune__commune', 'date_creation__month', 'date_creation__year', 'debit'
    ).order_by('cp_commune__commune', 'date_creation__year', 'date_creation__month', 'date_creation')

    communes_debit = {}
    for item in debit_par_commune:
        commune_id = item['cp_commune_id']
        commune_nom = item['cp_commune__commune']
        mois = item['date_creation__month']
        annee = item['date_creation__year']
        cle_periode = f'{annee}-{mois:02d}'
        if commune_id not in communes_debit:
            communes_debit[commune_id] = {'nom': commune_nom, 'donnees': {}}
        communes_debit[commune_id]['donnees'][cle_periode] = {'valeur': float(item['debit']), 'mois': mois, 'annee': annee}

    periodes = sorted(list(set(f'{item["date_creation__year"]}-{item["date_creation__month"]:02d}' for item in debit_par_commune)))
    periodes_display = [datetime.strptime(p, '%Y-%m').strftime('%m/%Y') for p in periodes]

    communes_list = []
    for data in communes_debit.values():
        valeurs = [data['donnees'].get(p, {}).get('valeur', 0.0) for p in periodes]
        communes_list.append({'nom': str(data['nom']), 'valeurs': valeurs})

    debit_data = {'periodes': periodes_display, 'communes': communes_list}
    return JsonResponse(debit_data)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_marnage_par_commune(request):
    # Cette vue a une logique de filtrage de date trop spécifique (semaine par défaut)
    # pour utiliser l'helper générique.
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    marnage_query = Marnage.objects.all()
    if region:
        marnage_query = marnage_query.filter(cp_commune__region=region)

    if date_deb and date_fin:
        debut_plage = datetime.strptime(date_deb, '%Y-%m-%d')
        fin_plage = datetime.strptime(date_fin, '%Y-%m-%d')
    else:
        aujourd_hui = timezone.now().date()
        debut_plage = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        fin_plage = debut_plage + timedelta(days=6)

    marnage_query = marnage_query.filter(date_creation__range=[
        timezone.make_aware(datetime.combine(debut_plage, datetime.min.time())),
        timezone.make_aware(datetime.combine(fin_plage, datetime.max.time()))
    ])

    marnage_data_raw = marnage_query.values(
        'cp_commune__commune', 'marnage', 'date_creation'
    ).order_by('cp_commune__commune', 'date_creation')

    communes_marnage = {}
    for item in marnage_data_raw:
        commune_nom = item['cp_commune__commune']
        if commune_nom not in communes_marnage:
            communes_marnage[commune_nom] = {'nom': str(commune_nom), 'mesures': []}
        
        try:
            date_creation = datetime.fromisoformat(item['date_creation'])
            communes_marnage[commune_nom]['mesures'].append({
                'timestamp': date_creation.strftime('%d/%m/%Y'),
                'valeur': float(item['marnage']) if item['marnage'] is not None else 0.0
            })
        except (ValueError, TypeError):
            continue

    marnage_data = {
        'communes': list(communes_marnage.values()),
        'date_debut': debut_plage.strftime('%d/%m/%Y'),
        'date_fin': fin_plage.strftime('%d/%m/%Y')
    }
    return JsonResponse(marnage_data)


def importe(request):
    if request.method == "POST":
        try:
            sql_file = request.FILES.get("sql_file")
            sql_content = sql_file.read().decode("utf-8")
            with connection.cursor() as cursor:
                cursor.execute(sql_content)
            return JsonResponse({"success": "Importation réussie."})
        except Exception as e:
            error_message = f"Erreur lors de l'importation du fichier SQL : {str(e)}"
            return JsonResponse({"error": error_message}, status=500)

    return render(request, 'bdd_upload.html')
