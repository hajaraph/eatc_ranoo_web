import logging

import pandas as pd
from celery import shared_task
from django.core.files.base import ContentFile
from django.db.models import Max, Sum
from pandas.tseries.offsets import MonthEnd

from Clients.models import Contrat
from Compteurs.api_compteur.serializer import MissionSerializer
from Compteurs.views import relever, ReleveMod
from Facturation.views import facture_creation
from Parametre.views import enregistre_historique
from Compteurs.models import Compteur, ReleveCompteur
from django.db import transaction
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


@shared_task
def get_liste_mission(cp_commune, end_of_month):
    contrats_commune = (
        Contrat.objects
        .filter(cp_commune_id=cp_commune)
        .select_related('client', 'num_compteur')
        .annotate(
            conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
        )
    )

    liste_contrats_info = []
    for contrat in contrats_commune:
        dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
            max_date=Max('date_releve'))
        date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else end_of_month

        # Comparaison des mois pour définir le statut
        if date_releve and date_releve.month != end_of_month.month:
            statut = 0
        else:
            statut = 2

        dernier_releve_obj = contrat.num_compteur.relevecompteurs.order_by('id_releve').last()
        contrat_info = {
            'id': dernier_releve_obj.pk if dernier_releve_obj else '',
            'nom_client': contrat.client.nom_client,
            'prenom_client': contrat.client.prenom_client if contrat.client.prenom_client else '',
            'adresse_client': contrat.client.adresse_client,
            'num_compteur': contrat.num_compteur_id,
            'conso_dernier_releve': contrat.conso_dernier_releve,
            'volume_dernier_releve': dernier_releve_obj.volume if dernier_releve_obj else 0,
            'date_releve': dernier_releve_obj.date_releve if dernier_releve_obj else '',
            'statut': statut
        }
        liste_contrats_info.append(contrat_info)

    # Trier la liste par id_releve
    liste_contrats_info = sorted(liste_contrats_info, key=lambda x: x['id'])

    return liste_contrats_info


@shared_task
def process_releve(data, file, id_utilisateur):
    serializer = MissionSerializer(data=data)

    if not serializer.is_valid():
        return {'status': 'error', 'message': serializer.errors}

    try:
        with transaction.atomic():
            id_releve = serializer.validated_data.get('releve_id')
            compteur_id = serializer.validated_data.get('num_compteur')
            date_releve = serializer.validated_data.get('date_releve')
            volume = serializer.validated_data.get('volume')
            image_compteur = file.get('image_compteur')

            if image_compteur:
                image_compteur = ContentFile(image_compteur.read(), name=image_compteur.name)

            if id_releve is not None:
                compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

                if dernier_releve.volume >= volume:
                    return {'status': 'error', 'message': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"}

                if date_releve <= dernier_releve.date_releve:
                    return {'status': 'error', 'message': "Veuillez fournir une date valide"}

                mod_releve = ReleveMod.mod_relever_facture(id_releve, compteur, date_releve, volume, image_compteur,
                                                           dernier_releve)
                facture_creation(date_releve, compteur.num_compteur, mod_releve)

                return {'status': 'success', 'message': 'Mise à jour effectuée avec succès !'}

            else:
                if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exists():
                    return {'status': 'error', 'message': "La date de relevé existe déjà dans la base de données"}

                dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).latest('date_releve')

                if dernier_volume:
                    if date_releve <= dernier_volume.date_releve:
                        return {'status': 'error', 'message': "Veuillez fournir une date valide"}

                    if dernier_volume.volume > volume:
                        return {'status': 'error', 'message': "Assurez-vous de saisir les chiffres correctement et réessayez !"}

                    conso = volume - dernier_volume.volume
                else:
                    conso = volume

                releve = relever(data, dernier_volume.num_compteur_id, date_releve, volume, conso, image_compteur, id_utilisateur)
                facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

            historique = f"Relever et Facture d'un compteur {compteur_id}"
            enregistre_historique(historique, id_utilisateur)

            return {'status': 'success', 'message': 'Relevé enregistré avec succès !'}
    except ValueError as e:
        return {'status': 'error', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}
