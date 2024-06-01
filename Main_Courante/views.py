from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from Clients.communes import Region
from Clients.models import Client
from Login.views import authentification_requis
from Main_Courante.models import MainCourante, StatutMC, SuivieMC
from Parametre.views import exporter_en_excel, enregistre_historique


@authentification_requis
def main_liste_mc(request):
    title = 'Main Courante | Liste MC'
    active = 'active'
    font = 'custom-font'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')

    statistiques = StatutMC.objects.aggregate(
        count_non_traite=Count('pk', filter=Q(non_traite=True)),
        count_realise=Count('pk', filter=Q(realise=True)),
        count_en_cours=Count('pk', filter=Q(en_cours=True)),
    )
    # Récupère les valeurs des compteurs
    non_traite = statistiques['count_non_traite']
    realise = statistiques['count_realise']
    en_cours = statistiques['count_en_cours']

    if datedeb and datefin:
        if datedeb > datefin:
            messages.warning(request, f'La Date Début ne doit pas être superieure à la Date Fin !')
            main_courante = MainCourante.objects.all()
        else:
            main_courante = MainCourante.objects.filter(date_mc__range=[datedeb, datefin])
    else:
        main_courante = MainCourante.objects.all()

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
        'en_cours': en_cours
    }
    return render(request, 'all_page/main_courante/main_courante.html', context)


@authentification_requis
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


class MainCouranteNew(View):
    @staticmethod
    @authentification_requis
    def get(request):
        title = 'Main Courante | Nouvelle Anomalie'
        active = 'active'
        font = 'custom-font'
        region = Region.objects.order_by('region').all()
        client = Client.objects.all()

        context = {
            'title_nouvelle_anomalie': title,
            'active': active,
            'font_main': font,
            'regions': region,
            'client': client
        }
        return render(request, 'all_page/main_courante/main_courante.html', context)

    @staticmethod
    @authentification_requis
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
        enregistre_historique(request, message, request.session.get('id_utilisateur'))
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
        enregistre_historique(request, message, request.session.get('id_utilisateur'))
        messages.success(request, success_message)
    except StatutMC.DoesNotExist:
        messages.error(request, f"StatutMC avec ID {pk} n'existe pas")
        return redirect('detail_mc', pk)
    return redirect('detail_mc', pk)


@authentification_requis
def lance_mc(request, pk):
    return update_statut_mc(
        request,
        pk,
        en_cours=True,
        non_traite=False,
        success_message='Traitement lancé avec succès !'
    )


@authentification_requis
def valide_mc(request, pk):
    return update_statut_mc(
        request,
        pk,
        en_cours=False,
        realise=True,
        success_message='MC réalisé avec succès !'
    )


@authentification_requis
def supprimer_mc(request, pk):
    main = MainCourante.objects.get(pk=pk)
    if main.photomcs.exists():
        photos = main.photomcs.all()
        for photo in photos:
            photo.photo_anomalie.delete()
            photo.delete()
    main.delete()
    message = f"Suppression de la main courante ID {pk}"
    enregistre_historique(request, message, request.session.get('id_utilisateur'))
    messages.success(request, 'Supprimer avec succès !')
    return redirect('main_liste_mc')


@authentification_requis
def suivie(request, pk):
    commentaire = request.POST['commentaire']
    SuivieMC.objects.create(
        commentaire_suivie=commentaire,
        main_courante_id=pk,
        utilisateur_id=request.session.get('id_utilisateur')
    )
    return redirect('detail_mc', pk)


@authentification_requis
def supp_suivie(request, pk):
    suivies = SuivieMC.objects.get(pk=pk)
    main_courante_id = suivies.main_courante_id
    suivies.delete()
    message = f"Suppresion d'un suivie"
    enregistre_historique(request, message, request.session.get('id_utilisateur'))
    return redirect('detail_mc', main_courante_id)


def export_mc_excel(request):
    main_courante = MainCourante.objects.order_by('id_mc').all()
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
    enregistre_historique(request, message, request.session.get('id_utilisateur'))
    return response
