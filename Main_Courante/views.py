from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.utils import timezone

from Acommune.models import Province
from Clients.models import Client
from Main_Courante.models import MainCourante, StatutMC, SuivieMC
from Parametre.views import exporter_en_excel, enregistre_historique
from Rel_Compteur.utils import filter_by_month_range, get_default_month_range
from Tenants.middleware import schema_use, SchemaAwareView


@schema_use
def main_liste_mc(request):
    title = 'Main Courante | Liste MC'
    active = 'active'
    font = 'custom-font'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')

    # Définir le queryset de base en fonction du rôle de l'utilisateur
    base_mc_queryset = MainCourante.objects.select_related('cp_commune').all()
    user_role = request.session.get('role_utilisateur')
    user_commune_id = request.session.get('cp_commune')

    if user_role in ['Releveur', 'Gestionnaire'] and user_commune_id:
        base_mc_queryset = base_mc_queryset.filter(cp_commune_id=user_commune_id)

    # Calculer les statistiques sur le queryset filtré
    statistiques = base_mc_queryset.aggregate(
        count_non_traite=Count('pk', filter=Q(statuts__non_traite=True)),
        count_realise=Count('pk', filter=Q(statuts__realise=True)),
        count_en_cours=Count('pk', filter=Q(statuts__en_cours=True)),
    )
    non_traite = statistiques['count_non_traite']
    realise = statistiques['count_realise']
    en_cours = statistiques['count_en_cours']

    # Utiliser la fonction utilitaire pour filtrer par plage de dates
    main_courante, datedeb, datefin = filter_by_month_range(
        queryset=base_mc_queryset,
        date_field='date_mc',
        date_start=datedeb,
        date_end=datefin,
        default_month=timezone.now().month
    )
    
    # Si les dates sont None (cas où le mois par défaut est utilisé)
    if datedeb is None or datefin is None:
        datedeb, datefin = get_default_month_range()
        datedeb = datedeb.strftime('%Y-%m')
        datefin = datefin.strftime('%Y-%m')

    main_courante_statut = []
    for main_courantes in main_courante:
        statut = main_courantes.statuts.get()
        main_courante_statut.append((main_courantes, statut))

    context = {
        'title_main': title,
        'active': active,
        'font_main': font,
        'main_nb': main_courante.count(),
        'main': main_courante_statut,
        'non_traite': non_traite,
        'realise': realise,
        'en_cours': en_cours,
        'datedeb': datedeb,
        'datefin': datefin
    }
    return render(request, 'all_page/main_courante/main_courante.html', context)


@schema_use
def detail_mc(request, pk):
    title = 'Main Courante| Détail'
    active = 'active'
    font = 'custom-font'
    main_courante = MainCourante.objects.get(pk=pk)
    photos = main_courante.photomcs.all()
    suivies = main_courante.suiviemcs.all()
    statut = main_courante.statuts.get()
    context = {
        'title_main_liste_detail': title,
        'active': active,
        'font_main': font,
        'main': main_courante,
        'photos': photos,
        'suivies': suivies,
        'statut': statut
    }
    return render(request, 'all_page/main_courante/main_courante.html', context)


class MainCouranteNew(SchemaAwareView):

    template_name = 'all_page/main_courante/main_courante.html'

    def get(self, request):
        title = 'Main Courante | Nouvelle Anomalie'
        active = 'active'
        font = 'custom-font'
        province = Province.objects.order_by('province').all()
        client = Client.objects.all()

        context = {
            'title_nouvelle_anomalie': title,
            'active': active,
            'font_main': font,
            'provinces': province,
            'client': client
        }
        return render(request, self.template_name, context)

    @staticmethod
    def post(request):
        client = request.POST['client_id']
        cp_commune = request.POST['commune'] if 'commune' in request.POST else None
        date_mc = request.POST['date_mc']
        type_anomalie = request.POST['type_anomalie']
        longitude_mc = request.POST['longitude_mc']
        latitude_mc = request.POST['latitude_mc']
        description_mc = request.POST['description_mc']
        photo_anomalie = request.FILES.getlist('photo_anomalie')

        main_courante = MainCourante.objects.create(
            date_mc=date_mc,
            type_anomalie=type_anomalie,
            longitude_mc=longitude_mc,
            latitude_mc=latitude_mc,
            description_mc=description_mc,
            client_id=client,
            cp_commune_id=cp_commune,
            utilisateur_id=request.session.get('id_utilisateur')
        )
        main_courante.statuts.create(
            main_courante_id=main_courante.pk
        )

        for photos in photo_anomalie:
            main_courante.photomcs.create(
                photo_anomalie=photos,
                main_courante_id=main_courante.pk
            )
        message = f"Creation d'une main courante"
        enregistre_historique(message, request.session.get('id_utilisateur'))
        messages.success(request, 'Anomalie Enregistré avec succès !')
        return redirect('main_liste_mc')


def update_statut_mc(request, pk, en_cours=None, non_traite=None, realise=None,
                     success_message="Statut mis à jour avec succès !"):
    try:
        statut = StatutMC.objects.get(main_courante_id=pk)
        date_now = timezone.now()
        statut.date_status = date_now
        if en_cours is not None:
            statut.en_cours = en_cours
        if non_traite is not None:
            statut.non_traite = non_traite
        if realise is not None:
            statut.realise = realise
        statut.save()
        message = f"Statut de la main courante ID {pk} mis à jour"
        enregistre_historique(message, request.session.get('id_utilisateur'))
        messages.success(request, success_message)
    except StatutMC.DoesNotExist:
        messages.error(request, f"StatutMC avec ID {pk} n'existe pas")
        return redirect('detail_mc', pk)
    return redirect('detail_mc', pk)


@schema_use
def lance_mc(request, pk):
    return update_statut_mc(
        request,
        pk,
        en_cours=True,
        non_traite=False,
        success_message='Traitement lancé avec succès !'
    )


@schema_use
def valide_mc(request, pk):
    return update_statut_mc(
        request,
        pk,
        en_cours=False,
        realise=True,
        success_message='MC réalisé avec succès !'
    )


@schema_use
def supprimer_mc(request, pk):
    main = MainCourante.objects.get(pk=pk)
    if main.photomcs.exists():
        photos = main.photomcs.all()
        for photo in photos:
            photo.photo_anomalie.delete()
            photo.delete()
    main.delete()
    message = f"Suppression de la main courante ID {pk}"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    messages.success(request, 'Supprimer avec succès !')
    return redirect('main_liste_mc')


@schema_use
def suivie(request, pk):
    commentaire = request.POST['commentaire']
    SuivieMC.objects.create(
        commentaire_suivie=commentaire,
        main_courante_id=pk,
        date_suivie=timezone.now(),
        utilisateur_id=request.session.get('id_utilisateur')
    )
    return redirect('detail_mc', pk)


@schema_use
def supp_suivie(request, pk):
    suivies = SuivieMC.objects.get(pk=pk)
    main_courante_id = suivies.main_courante_id
    suivies.delete()
    message = f"Suppresion d'un suivie"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return redirect('detail_mc', main_courante_id)


@schema_use
def export_mc_excel(request):
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    statut = request.GET.get('statut')

    main_courante = MainCourante.objects.order_by('id_mc').all()
    if date_deb and date_fin:
        if statut:
            if statut == 1:
                main_courante = main_courante.filter(date_mc__range=[date_deb, date_fin], statuts__non_traite=True)
            if statut == 2:
                main_courante = main_courante.filter(date_mc__range=[date_deb, date_fin], statuts__en_cours=True)
            if statut == 3:
                main_courante = main_courante.filter(date_mc__range=[date_deb, date_fin], statuts__realise=True)
    elif date_deb or date_fin:
        if statut:
            if statut == 1:
                main_courante = main_courante.filter(date_mc__range=[date_deb or date_fin], statuts__non_traite=True)
            if statut == 2:
                main_courante = main_courante.filter(date_mc__range=[date_deb or date_fin], statuts__en_cours=True)
            if statut == 3:
                main_courante = main_courante.filter(date_mc__range=[date_deb or date_fin], statuts__realise=True)
    else:
        if statut:
            if statut == 1:
                main_courante = main_courante.filter(statuts__non_traite=True)
            if statut == 2:
                main_courante = main_courante.filter(statuts__en_cours=True)
            if statut == 3:
                main_courante = main_courante.filter(statuts__realise=True)

    nom_fichier = f'Main_courantes.xlsx'
    champs = [
        'id_mc',
        'date_mc',
        'type_anomalie',
        'longitude_mc',
        'latitude_mc',
        'description_mc',
        'client__nom_client',
        'client__prenom_client',
        'cp_commune__region__region',
        'cp_commune__commune',
        'cp_commune_id',
        'statuts__non_traite',
        'statuts__en_cours',
        'statuts__realise'
    ]

    nom_colonnes = [
        'ID',
        'Date de declaration',
        'Type anomalie',
        'Longitude',
        'Latitude',
        'Description',
        'Client Nom',
        'Client Prénom',
        'Region',
        'Commune',
        'Cp Commune',
        'Status non traitée',
        'Status en cours',
        'Status realisée'
    ]

    response = exporter_en_excel(main_courante, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout les mains courantes"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response
