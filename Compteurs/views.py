from datetime import datetime
from django.contrib import messages
from django.db import models
from django.db.models import OuterRef, Subquery
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from Compteurs.models import Compteur, ReleveCompteur
from Clients.models import Contrat
from Facturation.models import Facture
from Facturation.views import facture_creation
from Login.views import authentification_requis, role_requis
from Parametre.views import enregistre_historique, exporter_en_excel
from Tenants.middleware import schema_use


@authentification_requis
@schema_use
def compteur_liste(request):
    title = 'Compteurs | Liste'
    active = 'active'
    header = 'Liste Compteurs'
    font = 'custom-font'
    # Pour recuperer tout les compteur et affciher leur dernier relever
    if request.session.get('role_utilisateur') != 'Releveur':
        # Récupération des derniers relevés
        derniers_releves = ReleveCompteur.objects.filter(
            num_compteur_id=OuterRef('pk')
        ).order_by('-date_releve')
        
        # Récupération des compteurs avec leurs contrats et clients associés
        compteurs = Compteur.objects.prefetch_related(
            models.Prefetch('contrats', queryset=Contrat.objects.select_related('client'))
        ).annotate(
            dernier_releve=Subquery(derniers_releves.values('date_releve')[:1])
        ).order_by('pk')

    else:
        cp_commune = request.session.get('cp_commune')

        derniers_releves = ReleveCompteur.objects.filter(
            num_compteur_id=OuterRef('pk')
        ).order_by('-date_releve')

        compteurs = Compteur.objects.annotate(
            dernier_releve=Subquery(derniers_releves.values('date_releve')[:1])
        ).filter(contrats__cp_commune_id=cp_commune).order_by('num_compteur')

    context = {
        'title_liste': title,
        'header_text': header,
        'active_li_co': active,
        'font_compteur': font,
        'compteur': compteurs,
    }
    return render(request, 'all_page/compteurs/compteurs.html', context)


class CompteurNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def get(request):
        title = 'Compteurs | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'title_new': title,
            'active_li_co': active,
            'font_compteur': font
        }
        return render(request, 'all_page/compteurs/compteurs.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def post(request):
        num_compteur = request.POST['num_compteur']
        marque_compteur = request.POST['marque_compteur']
        modele_compteur = request.POST['modele_compteur']
        dn_compteur = request.POST['DN_compteur']
        origin_compteur = request.POST['origin_compteur']
        date_releve = request.POST['date_releve']
        volume = request.POST['volume']

        numero = Compteur.objects.filter(num_compteur=num_compteur)
        if numero.exists():
            messages.warning(request, f"Le compteur avec le numéro {num_compteur} est déjà enregistrer !")
            return redirect('compteur_new')
        else:
            Compteur.objects.create(
                num_compteur=num_compteur,
                marque_compteur=marque_compteur,
                modele_compteur=modele_compteur,
                DN_compteur=dn_compteur,
                origin_compteur=origin_compteur
            )
            ReleveCompteur.objects.create(
                date_releve=date_releve,
                volume=volume,
                conso=0,
                num_compteur_id=num_compteur,
                utilisateur_id=request.session.get('id_utilisateur')
            )
            # Historique
            message = f"Creation d'un compteur numéro {num_compteur}"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, f"Compteur enregistrer avec succès !")
            return redirect('compteur_list')


class CompteurDetail(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def get(request, pk):
        active = 'active'
        font = 'custom-font'
        compteur = Compteur.objects.get(pk=pk)
        releve = compteur.relevecompteurs.order_by('id_releve').all()
        contrat = compteur.contrats

        title = f'Compteurs | Detail de {compteur.num_compteur}'
        context = {
            'title_detail': title,
            'active_li_co': active,
            'font_compteur': font,
            'detail': compteur,
            'releve': releve,
            'contrat': contrat.get().num_contrat if contrat.exists() else None,
            'client': contrat.get().client if contrat.exists() else None
        }
        return render(request, 'all_page/compteurs/compteurs.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def post(request, pk):
        mod_compteur = Compteur.objects.get(pk=pk)
        marque_compteur = request.POST['marque_compteur']
        modele_compteur = request.POST['modele_compteur']
        dn_compteur = request.POST['DN_compteur']
        origin_compteur = request.POST['origin_compteur']

        mod_compteur.marque_compteur = marque_compteur
        mod_compteur.modele_compteur = modele_compteur
        mod_compteur.DN_compteur = dn_compteur
        mod_compteur.origin_compteur = origin_compteur
        mod_compteur.save()
        # Historique
        message = f"Modification de compteur numéro {pk}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, f"Modification du Compteur numéro {mod_compteur.num_compteur} avec succès !")
        return redirect('compteur_list')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def compteur_supp(request, pk):
    compteur = Compteur.objects.get(pk=pk)
    compteur.delete()
    # Historique
    message = f"Suppression de compteur numéro {pk}"
    enregistre_historique(message, request.session.get('id_utilisateur'))

    messages.success(request, f'Compteur supprimé avec succès !')
    return redirect('compteur_list')


@authentification_requis
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


class ReleveNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def get(request, num_compteur):
        compteur = Compteur.objects.get(pk=num_compteur)
        title = f'Compteur Numéro : {compteur.num_compteur} | Relevé | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'title_releve_new': title,
            'active_releve_new': active,
            'font_compteur': font,
            'compteur': compteur
        }
        return render(request, 'all_page/compteurs/compteurs.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def post(request, num_compteur):
        date_releve = request.POST.get('date_releve')
        date_releve = datetime.strptime(date_releve, '%Y-%m-%d').date()
        volume = int(request.POST['volume'])
        image_compteur = request.FILES.get('image_compteur')
        utilisateur = request.session.get('id_utilisateur')

        try:
            dernier_volume = ReleveCompteur.objects.filter(num_compteur_id=num_compteur).latest('date_releve')

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

            # Créer un nouvel objet ReleveCompteur avec l'image mise à jour
            releve = relever(num_compteur, date_releve, volume, conso, image_compteur, utilisateur)
            facture_creation(date_releve, num_compteur, releve)

            # Historique
            message = f"Relever et Facture d'un compteur {num_compteur}"
            enregistre_historique(message, request.session.get('id_utilisateur'))

            messages.success(request, f"Relevé enregistrer avec succès !")
            return redirect('compteur_detail', num_compteur)

        except ReleveCompteur.DoesNotExist:
            messages.error(request, f"Date du dernier relevé inexistant dans la base !")
            return redirect('releve_new', num_compteur)


def relever(num_compteur, date_releve, volume, conso, image_compteur, utilisateur):
    return ReleveCompteur.objects.create(
        num_compteur_id=num_compteur,
        date_releve=date_releve,
        volume=volume,
        conso=conso,
        image_compteur=image_compteur,
        utilisateur_id=utilisateur
    )


class ReleveMod(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def get(request, pk):
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
        return render(request, 'all_page/compteurs/compteurs.html', context)

    @staticmethod
    def mod_relever_facture(id_releve, compteur, date_releve, volume, image_compteur, dernier_releve):
        mod_releve = compteur.relevecompteurs.get(pk=id_releve)
        conso = volume - dernier_releve.volume
        mod_releve.date_releve = date_releve
        mod_releve.volume = volume
        mod_releve.conso = conso
        mod_releve.image_compteur = image_compteur
        mod_releve.save()
        Facture.objects.get(relevecompteur_id=id_releve).delete()

        return mod_releve

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    @schema_use
    def post(request, pk):
        date_releve = request.POST['date_releve']
        date_releve = datetime.strptime(date_releve, '%Y-%m-%d').date()
        volume = int(request.POST['volume'])
        image_compteur = request.FILES.get('image_compteur')
        compteur = Compteur.objects.get(relevecompteurs__id_releve=pk)
        dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

        if date_releve < dernier_releve.date_releve:
            messages.error(request, f"Veuillez fournir une date valide pour le relevé !")
            return redirect('releve_mod', pk)
        else:
            if volume < dernier_releve.volume:
                messages.warning(request, f"Vous ne pouvez pas enregistrer un relevé inferieure à la dernière !")
                return redirect('releve_mod', pk)
            else:
                mod_releve = ReleveMod.mod_relever_facture(pk, compteur, date_releve,
                                                           volume, image_compteur, dernier_releve)
                facture_creation(date_releve, compteur.pk, mod_releve)
                messages.success(request, f"Relevé enregistré avec succès !")
                return redirect('compteur_detail', compteur.pk)


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire', 'Releveur')
@schema_use
def del_releve(request, pk):
    releve = get_object_or_404(ReleveCompteur, pk=pk)
    releve.image_compteur.delete()
    releve.delete()
    messages.success(request, f"Relevé supprimé avec succès !")
    return redirect('compteur_detail', releve.num_compteur.pk)


@authentification_requis
@schema_use
def export_compteur(request):
    compteurs = Compteur.objects.all()
    nom_fichier = "compteurs.xlsx"
    champs = [
        'contrats__num_contrat',
        'num_compteur',
        'relevecompteurs__date_releve',
        'relevecompteurs__volume',
        'relevecompteurs__conso',
    ]
    nom_colonnes = [
        'N° Contrat',
        'N° Compteur',
        'Date de Relevé',
        'volume',
        'Consommation'
    ]
    response = exporter_en_excel(compteurs, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout les compteurs"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response


@authentification_requis
@schema_use
def export_relever(request, num_compteur):
    relevecompteur = ReleveCompteur.objects.filter(num_compteur_id=num_compteur)
    nom_fichier = f"Relever_de_{num_compteur}.xlsx"
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
