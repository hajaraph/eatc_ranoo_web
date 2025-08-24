from datetime import timedelta, datetime

from django.db import connection
from django.db.models import Sum, Value, Count, Case, When, IntegerField, Q
from django.db.models.functions import Coalesce, ExtractYear, ExtractMonth
from django.http.response import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from Clients.models import Contrat, TypeClient
from Facturation.models import Paiement, Facture
from Login.views import role_requis
from Main_Courante.models import StatutMC
from Acommune.models import Region, Commune
from Tenants.middleware import schema_use


@role_requis('Administrateur', 'Gestionnaire', 'Autre')
@schema_use
def tableau_bord(request, *args, **kwargs):
    font = 'custom-font'
    region = request.GET.get('region')
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')

    date_actuelle = timezone.now()
    annee_actuelle = date_actuelle.year
    regions = Region.objects.all()

    commune = Commune.objects.filter(
        contrat__num_compteur__relevecompteurs__date_releve__year=annee_actuelle
    ).annotate(
        total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
    ).exclude(total_conso=0)
    factures = Facture.objects.filter(date_facture__year=annee_actuelle)
    main_courante = StatutMC.objects.filter(date_status__year=annee_actuelle)

    chiffres = Paiement.objects.all()

    if region:
        commune = Commune.objects.filter(
            region_id=region).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )

        factures = Facture.objects.filter(num_contrat__cp_commune__region=region)
        chiffres = Paiement.objects.filter(facture__num_contrat__cp_commune__region=region)

    elif date_deb and date_fin:
        commune = Commune.objects.filter(
            contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin]
        ).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )

        factures = Facture.objects.filter(date_facture__range=[date_deb, date_fin])
        main_courante = StatutMC.objects.filter(date_status__range=[date_deb, date_fin])
        chiffres = Paiement.objects.filter(facture__relevecompteur__date_releve__range=[date_deb, date_fin])

    elif region and date_deb and date_fin:
        date_deb = datetime.strptime(date_deb, '%Y-%m-%d').date() if isinstance(date_deb, str) else date_deb
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date() if isinstance(date_fin, str) else date_fin
        date_fin_plus_one = date_fin + timedelta(days=1)
        commune = Commune.objects.filter(
            region_id=region,
            contrat__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin_plus_one]).annotate(
            total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0))
        )

        factures = Facture.objects.filter(
            num_contrat__cp_commune__region=region,
            date_facture__range=[date_deb, date_fin]
        )

        chiffres = Paiement.objects.filter(
            facture__num_contrat__cp_commune__region=region,
            facture__relevecompteur__date_releve__range=[date_deb, date_fin]
        )

    commune = commune.annotate(
        total_conso=Coalesce(Sum('contrat__num_compteur__relevecompteurs__conso'), Value(0)))
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
    # Paiement
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
    types_client_conso = TypeClient.objects.annotate(
        mois=ExtractMonth('clients__contrats__num_compteur__relevecompteurs__date_releve'),
        annee=ExtractYear('clients__contrats__num_compteur__relevecompteurs__date_releve')
    ).filter(
        clients__contrats__num_compteur__relevecompteurs__date_releve__year=annee_actuelle
    ).values('designation_client', 'mois', 'annee').annotate(
        conso_mensuelle=Coalesce(Sum('clients__contrats__num_compteur__relevecompteurs__conso'), Value(0))
    ).exclude(conso_mensuelle=0).order_by('annee', 'mois', 'designation_client')

    # Appliquer les mêmes filtres que pour les autres données
    if region:
        types_client_conso = types_client_conso.filter(
            clients__contrats__cp_commune__region=region
        )
    elif date_deb and date_fin:
        types_client_conso = types_client_conso.filter(
            clients__contrats__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin]
        )
    elif region and date_deb and date_fin:
        types_client_conso = types_client_conso.filter(
            clients__contrats__cp_commune__region=region,
            clients__contrats__num_compteur__relevecompteurs__date_releve__range=[date_deb, date_fin]
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

    # pour recuperé les nombres de client lié à un contrat pour l'année precedant
    contrats_annee_prec = Contrat.objects.filter(
        date_debut__year=date_precedant.year
    ).annotate(
        annee_contrat_prec=ExtractYear('date_debut')
    ).values('annee_contrat_prec').annotate(
        nb_client_prec=Count('client')
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

    context = {
        'font_tableau': font,
        'regions': regions,
        'communes': commune,
        'chiffres': chiffres,
        'annee_contrat_actuelle': annee_contrat_actuelle,
        'nb_client_actuelle': nb_client_actuelle,
        'annee_contrat_prec': annee_contrat_prec,
        'nb_client_prec': nb_client_prec,
        'evo_conso': resultats,
        'factures': factures,
        'main_courantes': main_courante,
        'types_client_conso': types_client_conso,
        'datedeb': date_deb if date_deb else '',
        'datefin': date_fin if date_fin else ''
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