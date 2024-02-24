from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from Clients.communes import Region
from Clients.models import Client
from Login.views import authentification_requis
from Main_Courante.models import MainCourante, StatutMC, SuivieMC


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
            main_courante = StatutMC.objects.all()
        else:
            main_courante = StatutMC.objects.filter(main_courante__date_mc__range=[datedeb, datefin])
    else:
        main_courante = StatutMC.objects.all()
    context = {
        'title_main': title,
        'active': active,
        'font_main': font,
        'main': main_courante,
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
    main_courante = MainCourante.objects.get(statuts__id_statut=pk)
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

        messages.success(request, 'Anomalie Enregistré avec succès !')
        return redirect('main_liste_mc')


@authentification_requis
def lance_mc(request, pk):
    statut = StatutMC.objects.get(pk=pk)
    date_now = timezone.now()
    statut.date_status = date_now
    statut.en_cours = True
    statut.non_traite = False
    statut.save()
    messages.success(request, 'Traitement lancer avec succès !')
    return redirect('detail_mc', pk)


@authentification_requis
def valide_mc(request, pk):
    statut = StatutMC.objects.get(pk=pk)
    date_now = timezone.now()
    statut.date_status = date_now
    statut.realise = True
    statut.en_cours = False
    statut.save()
    messages.success(request, 'MC realisé avec succès !')
    return redirect('detail_mc', pk)


@authentification_requis
def supprimer_mc(request, pk):
    main = MainCourante.objects.get(pk=pk)
    if main.photomcs.exists():
        photos = main.photomcs.all()
        for photo in photos:
            photo.photo_anomalie.delete()
            photo.delete()
    main.delete()

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
    return redirect('detail_mc', main_courante_id)
