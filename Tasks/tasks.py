from celery import shared_task
from django.core.files.base import ContentFile

from Compteurs.api_compteur.serializer import MissionSerializer
from Compteurs.views import relever, ReleveMod
from Facturation.views import facture_creation
from Parametre.views import enregistre_historique
from Compteurs.models import Compteur, ReleveCompteur
from django.db import transaction
from django.shortcuts import get_object_or_404


@shared_task
def process_releve(data, file_data, id_utilisateur):
    serializer = MissionSerializer(data=data)

    if not serializer.is_valid():
        return {'status': 'error', 'message': serializer.errors}

    try:
        with transaction.atomic():
            id_releve = serializer.validated_data.get('releve_id')
            compteur_id = serializer.validated_data.get('num_compteur')
            date_releve = serializer.validated_data.get('date_releve')
            volume = serializer.validated_data.get('volume')
            image_compteur = ContentFile(file_data['content'], file_data['name']) if file_data else None

            if id_releve is not None:
                compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

                if dernier_releve.volume >= volume:
                    return {'status': 'error', 'message': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"}

                if date_releve <= dernier_releve.date_releve:
                    return {'status': 'error', 'message': "Veuillez fournir une date valide"}

                # Process the modification and creation
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
