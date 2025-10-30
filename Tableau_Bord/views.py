from datetime import timedelta, datetime
import json
from asyncio.log import logger

from django.db import connection
from django.db.models import Sum, Value, Count, Case, When, IntegerField, Q
from django.db.models.functions import Coalesce, ExtractYear, ExtractMonth
from django.http.response import HttpResponse
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
    font = 'custom-font'
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    date_actuelle = timezone.now()
    annee_actuelle = date_actuelle.year
    regions = Region.objects.all()

    # Requêtes initiales avec filtre par rôle
    commune = Commune.objects.filter(
        contrat__num_compteur__relevecompteurs__date_releve__year=annee_actuelle
    ).annotate(
        total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
    ).exclude(total_conso=0)
    factures = Facture.objects.filter(date_facture__year=annee_actuelle)
    main_courante = StatutMC.objects.filter(date_status__year=annee_actuelle)
    chiffres = Paiement.objects.all()

    # Application du filtre par rôle sur TOUS les querysets
    factures = filter_by_user_role(request, factures, 'num_contrat__cp_commune_id')
    chiffres = filter_by_user_role(request, chiffres, 'facture__num_contrat__cp_commune_id')
    main_courante = filter_by_user_role(request, main_courante, 'main_courante__cp_commune_id')
    commune = filter_by_user_role(request, commune, 'contrat__cp_commune_id')

    if region:
        # Filtrage par région avec filtre par rôle
        commune = Commune.objects.filter(
            region_id=region
        ).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )
        factures = Facture.objects.filter(num_contrat__cp_commune__region=region)
        main_courante = StatutMC.objects.filter(main_courante__cp_commune__region=region)
        chiffres = Paiement.objects.filter(facture__num_contrat__cp_commune__region=region)

        # Application du filtre par rôle sur TOUS les querysets
        factures = filter_by_user_role(request, factures, 'num_contrat__cp_commune_id')
        chiffres = filter_by_user_role(request, chiffres, 'facture__num_contrat__cp_commune_id')
        main_courante = filter_by_user_role(request, main_courante, 'main_courante__cp_commune_id')
        commune = filter_by_user_role(request, commune, 'contrat__cp_commune_id')

    elif date_deb and date_fin:
        # Filtrage par date avec filtre par rôle
        commune = Commune.objects.filter(
            contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin]
        ).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )
        factures = Facture.objects.filter(date_facture__range=[date_deb, date_fin])
        main_courante = StatutMC.objects.filter(date_status__range=[date_deb, date_fin])
        chiffres = Paiement.objects.filter(facture__relevecompteur__date_releve__range=[date_deb, date_fin])

        # Application du filtre par rôle sur TOUS les querysets
        factures = filter_by_user_role(request, factures, 'num_contrat__cp_commune_id')
        chiffres = filter_by_user_role(request, chiffres, 'facture__num_contrat__cp_commune_id')
        main_courante = filter_by_user_role(request, main_courante, 'main_courante__cp_commune_id')
        commune = filter_by_user_role(request, commune, 'contrat__cp_commune_id')

    elif region and date_deb and date_fin:
        # Filtrage par région et date avec filtre par rôle
        date_deb = datetime.strptime(date_deb, '%Y-%m-%d').date() if isinstance(date_deb, str) else date_deb
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date() if isinstance(date_fin, str) else date_fin
        date_fin_plus_one = date_fin + timedelta(days=1)

        # Filtrage par région et date
        commune = Commune.objects.filter(
            region_id=region,
            contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin_plus_one]
        ).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )
        factures = Facture.objects.filter(
            num_contrat__cp_commune__region=region,
            date_facture__range=[date_deb, date_fin]
        )
        main_courante = StatutMC.objects.filter(
            main_courante__cp_commune__region=region,
            date_status__range=[date_deb, date_fin]
        )
        chiffres = Paiement.objects.filter(
            facture__num_contrat__cp_commune__region=region,
            facture__relevecompteur__date_releve__range=[date_deb, date_fin]
        )

        # Application du filtre par rôle sur TOUS les querysets
        factures = filter_by_user_role(request, factures, 'num_contrat__cp_commune_id')
        chiffres = filter_by_user_role(request, chiffres, 'facture__num_contrat__cp_commune_id')
        main_courante = filter_by_user_role(request, main_courante, 'main_courante__cp_commune_id')
        commune = filter_by_user_role(request, commune, 'contrat__cp_commune_id')

    commune = commune.annotate(
        total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
    )
    commune = commune.exclude(total_conso=0)
    chiffres = chiffres.aggregate(Sum('montant_payer'))['montant_payer__sum'] or 0
    chiffres = round(chiffres, 2)

    resultats = []

    for communes in commune:
        # Filtrer par département
        evo_conso_commune = communes.contrat_set.annotate(
            mois_releve=ExtractMonth('num_compteur__relevecompteurs__date_releve'),
            annee_releve=ExtractYear('num_compteur__relevecompteurs__date_releve')
        ).values('mois_releve', 'annee_releve').annotate(
            total_conso=Coalesce(Sum('num_compteur__relevecompteurs__conso'), Value(0))
        ).order_by('annee_releve', 'mois_releve').exclude(total_conso=0)

        # Ajouter les résultats au tableau
        resultats.append(
            {
                'commune': f'{communes.region.region} {communes.commune}',
                'data': [
                    {
                        'mois_releve': entry['mois_releve'],
                        'annee_releve': entry['annee_releve'],
                        'total_conso': entry['total_conso']
                    }
                    for entry in evo_conso_commune
                ]
            }
        )

    # Requête de base avec filtres appliqués AVANT le groupement
    factures_par_type_base = Facture.objects.filter(date_facture__year=annee_actuelle)

    # Appliquer le filtre par rôle
    factures_par_type_base = filter_by_user_role(request, factures_par_type_base, 'num_contrat__cp_commune_id')

    # Appliquer les filtres région/date
    if region:
        factures_par_type_base = factures_par_type_base.filter(num_contrat__cp_commune__region=region)
    if date_deb and date_fin:
        factures_par_type_base = factures_par_type_base.filter(date_facture__range=[date_deb, date_fin])

    # Effectuer le groupement et l'agrégation
    factures_par_type_client = (
        factures_par_type_base
        .annotate(
            mois=ExtractMonth('date_facture'),
            annee=ExtractYear('date_facture'),
            type_client=Coalesce('num_contrat__client__type_client__designation_client', Value('Non spécifié')),
        )
        .values('mois', 'annee', 'type_client')
        .annotate(
            total=Count('id_facture'),
            montant_total=Coalesce(
                Sum('montant_total_ttc'),
                Value(0.0)
            ),
            payees=Count('id_facture', filter=Q(statut=True)),
            impayees=Count('id_facture', filter=Q(statut=False)),
            # Montant réellement payé = somme de tous les paiements effectués
            montant_total_payees=Coalesce(
                Sum('paiements__montant_payer'),
                Value(0.0)
            ) - Coalesce(Sum('montantht__tarif__prix_location_compteur', filter=Q(statut=True)), Value(0.0)),
            # Montant impayé = restants (partiellement payées) + factures complètement impayées
            montant_total_impayees=(Coalesce(
                Sum('restant_nouvel'),
                Value(0.0)
            ) + Coalesce(
                Sum('montant_total_ttc', filter=Q(statut=False)),
                Value(0.0)
            )) - Coalesce(Sum('montantht__tarif__prix_location_compteur', filter=Q(statut=False)), Value(0.0)),
            volume_paye=Coalesce(
                Sum('relevecompteur__conso', filter=Q(statut=True)),
                Value(0)
            ),
            volume_impaye=Coalesce(
                Sum('relevecompteur__conso', filter=Q(statut=False)),
                Value(0)
            ),
            montant_paye=Coalesce(Sum('paiements__montant_payer'), Value(0.0))
        )
        .order_by('annee', 'mois', 'type_client')
    )

    factures = factures.annotate(
        mois=ExtractMonth('date_facture'),
        annee=ExtractYear('date_facture'),
        statut_facture=Case(
            When(statut=True, then=1),
            default=0,
            output_field=IntegerField()
        )
    ).values('mois', 'annee').annotate(
        nombre_factures_payees=Count('statut_facture', filter=Q(statut_facture=1)),
        nombre_factures_impayees=Count('statut_facture', filter=Q(statut_facture=0))
    ).order_by('annee', 'mois')

    main_courante = main_courante.annotate(
        mois=ExtractMonth('main_courante__date_mc'),
        annee=ExtractYear('main_courante__date_mc'),
    ).values('mois', 'annee').annotate(
        nb_non_traite=Count('main_courante_id', filter=Q(non_traite=True)),
        nb_realise=Count('main_courante_id', filter=Q(realise=True)),
        nb_en_cours=Count('main_courante_id', filter=Q(en_cours=True))
    ).order_by('annee', 'mois')

    # Nouveau graphique : Consommation par type de client par mois
    types_client_conso = (
        ReleveCompteur.objects
        .filter(date_releve__year=annee_actuelle)
        .annotate(
            mois=ExtractMonth('date_releve'),
            annee=ExtractYear('date_releve'),
            designation_client=Coalesce(
                'num_compteur__contrats__client__type_client__designation_client',
                Value('Non spécifié')
            )
        )
        .values('designation_client', 'mois', 'annee')
        .annotate(conso_mensuelle=Sum('conso'))
        .filter(conso_mensuelle__gt=0)
        .order_by('annee', 'mois', 'designation_client')
    )

    # Appliquer le filtre par rôle sur types_client_conso
    types_client_conso = filter_by_user_role(request, types_client_conso, 'num_compteur__contrats__cp_commune_id')

    # Appliquer les mêmes filtres que pour les autres données
    if region:
        types_client_conso = types_client_conso.filter(
            num_compteur__contrats__cp_commune__region=region
        )
    if date_deb and date_fin:
        types_client_conso = types_client_conso.filter(
            date_releve__range=[date_deb, date_fin]
        )

    # Filtrage de main courante non traité
    date_precedant = date_actuelle - timedelta(days=365)

    # pour recuperé les nombres de client lié à un contrat pour l'année actuelle
    contrats_annee_actuelle = Contrat.objects.filter(
        date_debut__year=date_actuelle.year
    ).annotate(
        annee_contrat_actuelle=ExtractYear('date_debut')
    ).values('annee_contrat_actuelle').annotate(
        nb_client_actuelle=Count('client')
    )

    # Appliquer le filtre par rôle sur contrats_annee_actuelle
    contrats_annee_actuelle = filter_by_user_role(request, contrats_annee_actuelle, 'cp_commune_id')

    # pour recuperé les nombres de client lié à un contrat pour l'année precedant
    contrats_annee_prec = Contrat.objects.filter(
        date_debut__year=date_precedant.year
    ).annotate(
        annee_contrat_prec=ExtractYear('date_debut')
    ).values('annee_contrat_prec').annotate(
        nb_client_prec=Count('client')
    )

    # Appliquer le filtre par rôle sur contrats_annee_prec
    contrats_annee_prec = filter_by_user_role(request, contrats_annee_prec, 'cp_commune_id')

    # Appliquer les mêmes filtres que pour les autres données
    if region:
        contrats_annee_actuelle = contrats_annee_actuelle.filter(
            cp_commune__region=region
        )
        contrats_annee_prec = contrats_annee_prec.filter(
            cp_commune__region=region
        )
    if date_deb and date_fin:
        contrats_annee_actuelle = contrats_annee_actuelle.filter(
            date_debut__range=[date_deb, date_fin]
        )
        contrats_annee_prec = contrats_annee_prec.filter(
            date_debut__range=[date_precedant.replace(month=1, day=1), date_precedant.replace(month=12, day=31)]
        )

    # Pour obtenir seulement l'année precedant de notre requete precedant
    # annee_contrat_prec = contrats_annee_prec[0]['annee_contrat_prec'] if contrats_annee_prec else 0

    # Pour obtenir le nombre de contrats pour l'année precedant depuis notre requete precedanat
    nb_client_prec = contrats_annee_prec[0]['nb_client_prec'] if contrats_annee_prec else 0

    # Pour obtenir seulement l'année actuelle de notre requete precedant
    annee_contrat_actuelle = contrats_annee_actuelle[0]['annee_contrat_actuelle'] if contrats_annee_actuelle else 0
    annee_contrat_prec = 0 if annee_contrat_actuelle == 0 else annee_contrat_actuelle - 1

    # Pour obtenir le nombre de contrats pour l'année actuelle depuis notre requete precedanat
    nb_client_actuelle = contrats_annee_actuelle[0]['nb_client_actuelle'] if contrats_annee_actuelle else 0

    # Requête de base avec filtres
    debit_query = DebitEau.objects.all()
    marnage_query = Marnage.objects.all()

    # Application des filtres région/date pour le débit et le marnage
    if region:
        debit_query = debit_query.filter(cp_commune__region=region)
        marnage_query = marnage_query.filter(cp_commune__region=region)

    if date_deb and date_fin:
        date_fin_plus_one = date_fin + timedelta(days=1)
        date_range = [date_deb, date_fin_plus_one]
        debit_query = debit_query.filter(date_creation__range=date_range)
        marnage_query = marnage_query.filter(date_creation__range=date_range)

    # Données de débit brutes par commune
    debit_par_commune = debit_query.values(
        'cp_commune_id',
        'cp_commune__commune',
        'date_creation__month',
        'date_creation__year',
        'debit'
    ).order_by('cp_commune__commune', 'date_creation__year', 'date_creation__month', 'date_creation')

    # Préparer les données pour le graphique
    communes_debit = {}
    for item in debit_par_commune:
        commune_id = item['cp_commune_id']
        commune_nom = item['cp_commune__commune']
        mois = item['date_creation__month']
        annee = item['date_creation__year']

        if commune_id not in communes_debit:
            communes_debit[commune_id] = {
                'nom': commune_nom,
                'donnees': {}
            }

        # Stocker les données par année-mois pour cette commune
        cle_periode = f"{annee}-{mois:02d}"
        # Utiliser la dernière valeur de débit pour cette période
        communes_debit[commune_id]['donnees'][cle_periode] = {
            'valeur': float(item['debit']),
            'mois': mois,
            'annee': annee
        }

    # Créer la structure finale des données pour le template
    periodes = sorted(list(set(
        f"{item['date_creation__month']:02d}/{item['date_creation__year']}"
        for item in debit_par_commune
    )))

    communes_list = []
    for commune_id, data in communes_debit.items():
        valeurs = []
        for periode in periodes:
            if periode in data['donnees']:
                valeurs.append(data['donnees'][periode]['valeur'])
            else:
                valeurs.append(0.0)
        logger.info(valeurs)
        communes_list.append({
            'nom': str(data['nom']),  # S'assurer que le nom est une chaîne
            'valeurs': valeurs
        })

    debit_data = {
        'periodes': periodes,
        'communes': communes_list
    }

    # Obtenir la date du jour et calculer le lundi de la semaine en cours
    aujourd_hui = timezone.now().date()
    lundi_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    # Définir les dates de début et fin de la semaine
    debut_semaine = timezone.make_aware(datetime.combine(lundi_semaine, datetime.min.time()))
    fin_semaine = timezone.make_aware(datetime.combine(lundi_semaine + timedelta(days=6), datetime.max.time()))

    # Récupérer les données de marnage pour la semaine en cours
    marnage_semaine = []

    # Récupérer les données brutes
    marnage_data = marnage_query.filter(
        date_creation__isnull=False
    ).values(
        'cp_commune_id',
        'cp_commune__commune',
        'marnage',
        'date_creation'
    ).order_by('cp_commune__commune', 'date_creation')

    # Traiter manuellement les dates
    for item in marnage_data:
        try:
            # Convertir la chaîne en datetime (format: 2025-10-29T11:06)
            date_creation = timezone.make_aware(datetime.strptime(item['date_creation'], '%Y-%m-%dT%H:%M'))

            # Vérifier si la date est dans l'intervalle
            if debut_semaine <= date_creation <= fin_semaine:
                # weekday() retourne 0=Lundi, 1=Mardi, ..., 6=Dimanche
                jour_semaine = date_creation.weekday()

                marnage_semaine.append({
                    'cp_commune_id': item['cp_commune_id'],
                    'cp_commune__commune': item['cp_commune__commune'],
                    'marnage': item['marnage'],
                    'date_creation': date_creation,
                    'jour_semaine': jour_semaine
                })
        except (ValueError, TypeError):
            continue

    # Initialiser la structure des données - conserver toutes les mesures avec leurs heures
    communes_marnage = {}

    # Remplir les données pour chaque commune avec toutes les mesures et leurs heures
    for item in marnage_semaine:
        commune_id = item['cp_commune_id']
        commune_nom = item['cp_commune__commune']
        date_creation = item['date_creation']

        if commune_id not in communes_marnage:
            communes_marnage[commune_id] = {
                'nom': str(commune_nom),
                'mesures': []
            }

        # Stocker chaque mesure avec son timestamp complet et sa valeur
        communes_marnage[commune_id]['mesures'].append({
            'timestamp': date_creation.strftime('%d/%m/%Y %H:%M'),
            'valeur': float(item['marnage']) if item['marnage'] is not None else 0.0
        })

    # Préparer les données pour le template
    communes_marnage_list = []

    for commune_id, data in communes_marnage.items():
        communes_marnage_list.append({
            'nom': data['nom'],
            'mesures': data['mesures']
        })

    # Préparer les données pour le template
    marnage_data = {
        'communes': communes_marnage_list,
        'date_debut': lundi_semaine.strftime('%d/%m/%Y'),
        'date_fin': (lundi_semaine + timedelta(days=6)).strftime('%d/%m/%Y')
    }

    context = {
        'font_tableau': font,
        'regions': regions,
        'communes': commune,
        'chiffres': chiffres,
        'nb_client_actuelle': nb_client_actuelle,
        'annee_contrat_prec': annee_contrat_prec,
        'nb_client_prec': nb_client_prec,
        'evo_conso': resultats,
        'factures': factures,
        'main_courantes': main_courante,
        'types_client_conso': types_client_conso,
        'datedeb': date_deb if date_deb else '',
        'datefin': date_fin if date_fin else '',
        'factures_par_type_client': factures_par_type_client,
        'debit_data': json.dumps(debit_data),
        'marnage_data': json.dumps(marnage_data)
    }

    return render(request, 'all_page/tableau_bord.html', context)


def importe(request):
    if request.method == "POST":
        try:
            sql_file = request.FILES.get("sql_file")
            sql_content = sql_file.read().decode("utf-8")
            with connection.cursor() as cursor:
                cursor.execute(sql_content)
            return HttpResponse("Importation réussie.")
        except Exception as e:
            error_message = f"Erreur lors de l'importation du fichier SQL : {str(e)}"
            return HttpResponse(error_message, status=500)

    return render(request, 'bdd_upload.html')
