from datetime import timedelta, datetime

from django.db import connection
from django.db.models import Sum, Value, Count, Q
from django.db.models.functions import Coalesce, ExtractYear, ExtractMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from Clients.models import Contrat
from Compteurs.models import ReleveCompteur
from Facturation.models import Paiement, Facture
from Login.views import role_requis
from Main_Courante.models import StatutMC
from Acommune.models import Region, Commune
from Rubrique.models import DebitEau, Marnage
from Tenants.middleware import schema_use
from Rel_Compteur.utils import filter_by_user_role


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def tableau_bord(request):
    """
    Charge la page principale du tableau de bord.
    Les données sont chargées de manière asynchrone via des appels AJAX aux vues API.
    """
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
    """
    Fournit les KPIs globaux :
    - Chiffre d'affaires total
    - Nombre de clients pour l'année actuelle et précédente
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    date_actuelle = timezone.now()

    # --- Chiffre d'affaires ---
    chiffres_query = Paiement.objects.all()
    chiffres_query = filter_by_user_role(request, chiffres_query, 'facture__num_contrat__cp_commune_id')
    if region:
        chiffres_query = chiffres_query.filter(facture__num_contrat__cp_commune__region=region)
    if date_deb and date_fin:
        chiffres_query = chiffres_query.filter(facture__relevecompteur__date_releve__range=[date_deb, date_fin])

    chiffres = chiffres_query.aggregate(Sum('montant_payer'))['montant_payer__sum'] or 0
    chiffres = round(chiffres, 2)

    # --- Nombre de clients ---
    date_precedant = date_actuelle - timedelta(days=365)
    contrats_actuels_query = Contrat.objects.filter(date_debut__year=date_actuelle.year)
    contrats_prec_query = Contrat.objects.filter(date_debut__year=date_precedant.year)

    contrats_actuels_query = filter_by_user_role(request, contrats_actuels_query, 'cp_commune_id')
    contrats_prec_query = filter_by_user_role(request, contrats_prec_query, 'cp_commune_id')

    if region:
        contrats_actuels_query = contrats_actuels_query.filter(cp_commune__region=region)
        contrats_prec_query = contrats_prec_query.filter(cp_commune__region=region)
    if date_deb and date_fin:
        contrats_actuels_query = contrats_actuels_query.filter(date_debut__range=[date_deb, date_fin])
        # Note: la logique de filtrage pour l'année précédente avec une plage de dates peut être complexe.
        # Maintenir la simplicité pour l'instant.

    nb_client_actuelle = contrats_actuels_query.count()
    nb_client_prec = contrats_prec_query.count()
    annee_contrat_prec = date_precedant.year

    data = {
        'chiffres': chiffres,
        'nb_client_actuelle': nb_client_actuelle,
        'annee_contrat_prec': annee_contrat_prec,
        'nb_client_prec': nb_client_prec,
    }
    return JsonResponse(data)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_evo_conso_commune(request):
    """
    Fournit les données d'évolution de la consommation par commune.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    annee_actuelle = timezone.now().year

    commune_query = Commune.objects.all()
    commune_query = filter_by_user_role(request, commune_query, 'id') # Filtrer les communes elles-mêmes

    if region:
        commune_query = commune_query.filter(region_id=region)

    # Annoter avec la consommation filtrée par date si nécessaire
    conso_filters = Q()
    if date_deb and date_fin:
        conso_filters &= Q(contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin])
    else:
        conso_filters &= Q(contrat__num_compteur__relevecompteurs__date_releve__year=annee_actuelle)

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
    """
    Fournit le nombre de factures payées et impayées par mois.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    annee_actuelle = timezone.now().year

    factures_query = Facture.objects.filter(date_facture__year=annee_actuelle)
    factures_query = filter_by_user_role(request, factures_query, 'num_contrat__cp_commune_id')

    if region:
        factures_query = factures_query.filter(num_contrat__cp_commune__region=region)
    if date_deb and date_fin:
        factures_query = Facture.objects.filter(date_facture__range=[date_deb, date_fin])

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
    """
    Fournit le nombre de mains courantes par statut et par mois.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    annee_actuelle = timezone.now().year

    mc_query = StatutMC.objects.filter(date_status__year=annee_actuelle)
    mc_query = filter_by_user_role(request, mc_query, 'main_courante__cp_commune_id')

    if region:
        mc_query = mc_query.filter(main_courante__cp_commune__region=region)
    if date_deb and date_fin:
        mc_query = StatutMC.objects.filter(date_status__range=[date_deb, date_fin])

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
    """
    Fournit les données détaillées de facturation par type de client.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    annee_actuelle = timezone.now().year

    base_query = Facture.objects.filter(relevecompteur__date_releve__year=annee_actuelle)
    base_query = filter_by_user_role(request, base_query, 'num_contrat__cp_commune_id')

    if region:
        base_query = base_query.filter(num_contrat__cp_commune__region=region)
    if date_deb and date_fin:
        base_query = base_query.filter(relevecompteur__date_releve__range=[date_deb, date_fin])

    factures_par_type_client = (
        base_query
        .annotate(
            mois=ExtractMonth('relevecompteur__date_releve'),
            annee=ExtractYear('relevecompteur__date_releve'),
            type_client=Coalesce('num_contrat__client__type_client__designation_client', Value('Non spécifié')),
        )
        .values('mois', 'annee', 'type_client')
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
        .order_by('annee', 'mois', 'type_client')
    )
    return JsonResponse(list(factures_par_type_client), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_conso_par_type_client(request):
    """
    Fournit la consommation mensuelle par type de client.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    annee_actuelle = timezone.now().year

    conso_query = ReleveCompteur.objects.filter(date_releve__year=annee_actuelle)
    conso_query = filter_by_user_role(request, conso_query, 'num_compteur__contrats__cp_commune_id')

    if region:
        conso_query = conso_query.filter(num_compteur__contrats__cp_commune__region=region)
    if date_deb and date_fin:
        conso_query = conso_query.filter(date_releve__range=[date_deb, date_fin])

    types_client_conso = (
        conso_query
        .annotate(
            mois=ExtractMonth('date_releve'),
            annee=ExtractYear('date_releve'),
            designation_client=Coalesce('num_compteur__contrats__client__type_client__designation_client', Value('Non spécifié'))
        )
        .values('designation_client', 'mois', 'annee')
        .annotate(conso_mensuelle=Sum('conso'))
        .filter(conso_mensuelle__gt=0)
        .order_by('annee', 'mois', 'designation_client')
    )
    return JsonResponse(list(types_client_conso), safe=False)


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def api_debit_par_commune(request):
    """
    Fournit les données de débit pour le graphique.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    debit_query = DebitEau.objects.all()
    # Note: Le filtrage par rôle n'était pas appliqué ici dans le code original.
    # debit_query = filter_by_user_role(request, debit_query, 'cp_commune_id')

    if region:
        debit_query = debit_query.filter(cp_commune__region=region)
    if date_deb and date_fin:
        debit_query = debit_query.filter(date_creation__range=[date_deb, date_fin])

    debit_par_commune = debit_query.values(
        'cp_commune_id', 'cp_commune__commune', 'date_creation__month', 'date_creation__year', 'debit'
    ).order_by('cp_commune__commune', 'date_creation__year', 'date_creation__month', 'date_creation')

    # Traitement des données pour le graphique
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
    """
    Fournit les données de marnage pour la semaine en cours.
    """
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    marnage_query = Marnage.objects.all()
    # Note: Le filtrage par rôle n'était pas appliqué ici dans le code original.
    # marnage_query = filter_by_user_role(request, marnage_query, 'cp_commune_id')

    if region:
        marnage_query = marnage_query.filter(cp_commune__region=region)

    # Définir la plage de dates (semaine en cours par défaut, sinon la plage spécifiée)
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
                'timestamp': date_creation.strftime('%d/%m/%Y %H:%M'),
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


# VUE EXISTANTE POUR L'IMPORTATION
# =================================
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
