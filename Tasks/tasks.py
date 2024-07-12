import re

from celery import shared_task
from django.db.models import Max, Sum

from Clients.models import Contrat
from Compteurs.api_compteur.serializer import MissionSerializer
from Compteurs.views import relever
from Facturation.models import Facture, Tarif, MontantHT
from Facturation.views import facture_creation, paiement
from Parametre.views import enregistre_historique
from Compteurs.models import Compteur, ReleveCompteur
from django.db import transaction
from django.shortcuts import get_object_or_404


class TaskMission:
    @staticmethod
    @shared_task()
    def process_liste_mission(cp_commune, end_of_month):
        try:
            with transaction.atomic():
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
                        'id': str(dernier_releve_obj.pk) if dernier_releve_obj else '',
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

        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}

    @staticmethod
    @shared_task
    def process_releve(data, utilisateur):
        serializer = MissionSerializer(data=data)

        if not serializer.is_valid():
            return {'status': 'error', 'message': serializer.errors}

        try:
            with transaction.atomic():
                compteur_id = serializer.validated_data.get('num_compteur')
                date_releve = serializer.validated_data.get('date_releve')
                volume = serializer.validated_data.get('volume')
                image_compteur = serializer.validated_data.get('image_compteur')

                # if id_releve is not None:
                #     compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                #     dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]
                #
                #     if dernier_releve.volume >= volume:
                #         return {'status': 'error', 'message': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"}
                #
                #     if date_releve <= dernier_releve.date_releve:
                #         return {'status': 'error', 'message': "Veuillez fournir une date valide"}
                #
                #     mod_releve = ReleveMod.mod_relever_facture(id_releve, compteur, date_releve, volume, image_compteur,
                #                                                dernier_releve)
                #     facture_creation(date_releve, compteur.num_compteur, mod_releve)
                #
                #     return {'status': 'success', 'message': 'Mise à jour effectuée avec succès !'}
                #
                # else:
                if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exists():
                    return {'status': 'error', 'message': "La date de relevé existe déjà dans la base de données"}

                dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).latest('date_releve')

                if dernier_volume:
                    if date_releve <= dernier_volume.date_releve:
                        return {'status': 'error', 'message': "Veuillez fournir une date valide"}

                    if dernier_volume.volume > volume:
                        return {'status': 'error', 'message': "Assurez-vous de saisir les chiffres correctement et "
                                                              "réessayez !"}

                    conso = volume - dernier_volume.volume
                else:
                    conso = volume

                releve = relever(dernier_volume.num_compteur_id, date_releve, volume, conso, image_compteur, utilisateur)
                facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

                historique = f"Relever et Facture d'un compteur {compteur_id}"
                enregistre_historique(historique, utilisateur)

                return {'status': 'success', 'message': 'Relevé enregistré avec succès !'}
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}


@shared_task
def process_compteur_details(compteur_id):
    try:
        with transaction.atomic():
            compteur = get_object_or_404(Compteur, num_compteur=compteur_id)

            # Récupérer les informations sur le compteur
            compteur_info = {
                'id': int(compteur.num_compteur),
                'marque': compteur.marque_compteur,
                'modele': compteur.modele_compteur,
            }

            contrat = get_object_or_404(Contrat, num_compteur=compteur_id)

            # Extraire le numéro du contrat
            contrat_nums = contrat.num_contrat
            num_contrat = re.search(r'\d+', contrat_nums).group()

            # Récupérer les informations sur le contrat
            contrat_info = {
                'id': int(num_contrat),
                'numero_contrat': contrat.num_contrat,
                'date_debut': contrat.date_debut,
                'date_fin': contrat.date_fin,
                'adresse_contrat': contrat.adresse_contrat,
                'pays_contrat': contrat.pays_contrat,
            }

            client = contrat.client
            client_info = {
                'id': client.id_client,
                'nom': client.nom_client,
                'prenom': client.prenom_client if client.prenom_client else '',
                'adresse': client.adresse_client,
                'commune': client.cp_commune.commune,
                'region': client.cp_commune.region.region,
                'tephone1': client.tel1_client,
                'tephone2': client.tel2_client,
                'actif': client.compte_actif
            }

            releves_data = ReleveCompteur.objects.filter(num_compteur=compteur).order_by('-date_releve')

            releves_list = []
            for releve in releves_data:
                releve_dict = {
                    'id': int(releve.id_releve),
                    'id_releve': int(releve.id_releve),
                    'compteur_id': int(compteur.num_compteur),
                    'contrat_id': int(num_contrat),
                    'client_id': int(client.id_client),
                    'date_releve': releve.date_releve,
                    'volume': releve.volume,
                    'conso': releve.conso,
                    'image_compteur': releve.image_compteur.url if releve.image_compteur else 'null',
                }

                # Récupérer la facture associée au relevé
                facture = Facture.objects.filter(relevecompteur=releve).first()
                if facture:
                    releve_dict['etatFacture'] = 'Payé' if facture.statut else 'Impayé'
                else:
                    releve_dict['etatFacture'] = 'Pas de facture'

                releves_list.append(releve_dict)

            return {
                'compteur': compteur_info,
                'contrat': contrat_info,
                'client': client_info,
                'releves': releves_list
            }
    except Compteur.DoesNotExist:
        raise ValueError('Compteur non trouvé')
    except Contrat.DoesNotExist:
        raise ValueError('Contrat non trouvé')
    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise Exception(str(e))


class TaskFactureDetail:

    @staticmethod
    @shared_task
    def precess_facture_list(id_releve):
        try:
            with transaction.atomic():
                releve = get_object_or_404(Facture, relevecompteur_id=id_releve)

                if not releve:
                    return {'status': 'error', 'message': 'La facture n\'a pas été trouvée pour l\'ID de relevé spécifié'}

                montant_ht = get_object_or_404(MontantHT, facture_id=releve.id_facture)

                avoir_avant = releve.avoir_avant if releve.avoir_avant else 0.0
                avoir_utilise = releve.avoir_utilise if releve.avoir_utilise else 0.0
                restant_precedant = releve.restant_precedant if releve.restant_precedant else 0.0
                restant_nouvel = releve.restant_nouvel if releve.restant_nouvel else 0.0
                montant_total_ttc = releve.montant_total_ttc if releve.montant_total_ttc else 0.0

                if montant_total_ttc == 0.0 or restant_nouvel == 0.0 or restant_nouvel == 0.0:
                    montant_payer = 0.0
                else:
                    montant_payer = montant_total_ttc - restant_nouvel
                # Affiche le prix du selon le type de client
                typeclient = releve.num_contrat.client.type_client_id
                cp_commune = releve.num_contrat.cp_commune_id
                tarif = get_object_or_404(Tarif, cp_commune_id=cp_commune)
                if typeclient == 1:
                    tarif_m3 = tarif.prix_m3_bp
                elif typeclient == 2:
                    tarif_m3 = tarif.prix_m3_bs
                elif typeclient == 3:
                    tarif_m3 = tarif.prix_m3_k
                else:
                    tarif_m3 = 0.0

                facture = {
                    'id': int(releve.id_facture),
                    'relevecompteur_id': int(releve.relevecompteur_id),
                    'num_facture': releve.num_facture,
                    'num_compteur': int(releve.num_contrat.num_compteur_id),
                    'date_facture': releve.date_facture,
                    'total_conso_ht': montant_ht.total_conso_ht if montant_ht.total_conso_ht is not None else 0.0,
                    'tarif_m3': tarif_m3,
                    'avoir_avant': avoir_avant,
                    'avoir_utilise': avoir_utilise,
                    'restant_precedant': restant_precedant,
                    'montant_payer': montant_payer,
                    'montant_total_ttc': montant_total_ttc,
                    'statut': 'Payé' if releve.statut else 'Impayé',
                }
                return facture

        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(str(e))

    @staticmethod
    @shared_task
    def process_facture_paiement(id_releve, montant_payer, utilisateur_id):
        try:
            with transaction.atomic():

                # Vérifier si le paiement est supérieur ou égal à 0.1
                if montant_payer >= 0.1:
                    paiement(id_releve, montant_payer, utilisateur_id)
                    return {'status': 'success', 'message': 'Paiement effectué avec succès !'}
                else:
                    return {'status': 'error', 'message': 'Le montant du paiement doit être supérieur ou égal à 0.1.'}
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(str(e))
