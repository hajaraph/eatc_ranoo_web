import re
from asyncio.log import logger

from asgiref.sync import sync_to_async
from django.core.cache import cache
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
    async def process_liste_mission(cp_commune, end_of_month, offset=0, limit=50):
        logger.info(f"Début process_liste_mission pour cp_commune={cp_commune}, offset={offset}, limit={limit}")
        cache_key = f"missions_liste_{cp_commune}_{end_of_month.strftime('%Y%m%d')}_{offset}_{limit}"

        try:
            # Essayer de récupérer depuis le cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("Données récupérées depuis le cache")
                return cached_result

            # Si pas dans le cache, calculer les données
            @sync_to_async
            def get_contrats():
                with transaction.atomic():
                    total_contrats = Contrat.objects.filter(cp_commune_id=cp_commune).count()
                    contrats_commune = (
                        Contrat.objects
                        .filter(cp_commune_id=cp_commune)
                        .select_related('client', 'num_compteur')
                        .prefetch_related('num_compteur__relevecompteurs')
                        .annotate(
                            conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
                        )
                    )

                    # S'assurer que offset et limit sont des entiers
                    try:
                        offset_int = int(offset)
                        limit_int = int(limit)
                    except (TypeError, ValueError):
                        return {'status': 'error', 'message': 'Les paramètres offset et limit doivent être des nombres valides'}

                    # Appliquer la pagination
                    contrats_commune = contrats_commune[offset_int:offset_int + limit_int]

                    liste_contrats_info = []
                    for contrat in contrats_commune:
                        dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
                            max_date=Max('date_releve')
                        )
                        date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else end_of_month

                        # Vérifier si date_releve est un objet date avant de comparer
                        statut = 0 if (date_releve and hasattr(date_releve, 'month') and date_releve.month != end_of_month.month) else 2

                        dernier_releve_obj = contrat.num_compteur.relevecompteurs.order_by('id_releve').last()
                        contrat_info = {
                            'id': int(dernier_releve_obj.pk) if dernier_releve_obj else 0,  # Utiliser 0 au lieu de chaîne vide
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

                    # Trier la liste en s'assurant que tous les IDs sont des entiers
                    liste_contrats_info = sorted(liste_contrats_info, key=lambda x: x['id'])
                    query_result = {
                        'liste': liste_contrats_info,
                        'has_more': offset_int + limit_int < total_contrats,
                        'next_offset': offset_int + limit_int if offset_int + limit_int < total_contrats else None
                    }
                    return query_result

            result = await get_contrats()

            # Mettre en cache avec un timeout de 5 minutes
            try:
                cache.set(cache_key, result, timeout=300)  # 5 minutes
                logger.info(f"Données mises en cache avec la clé: {cache_key}")
            except Exception as cache_error:
                logger.warning(f"Impossible de mettre en cache les résultats: {str(cache_error)}")

            return result

        except Exception as e:
            logger.error(f"Erreur inattendue dans process_liste_mission: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}


    @staticmethod
    async def process_releve(data, utilisateur):
        # Serializer reste synchrone, on l'encapsule
        serializer = await sync_to_async(MissionSerializer)(instance=None, data=data)

        # Valider le serializer dans un thread
        is_valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return {'status': 'error', 'message': errors}

        try:
            # Encapsuler la logique synchrone dans un thread
            @sync_to_async
            def process():
                with transaction.atomic():
                    validated_data = serializer.validated_data
                    compteur_id = validated_data.get('num_compteur')
                    date_releve = validated_data.get('date_releve')
                    volume = validated_data.get('volume')
                    image_compteur = validated_data.get('image_compteur')

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

                    releve = relever(dernier_volume.num_compteur_id, date_releve, volume, conso, image_compteur, utilisateur)
                    facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

                    historique = f"Relever et Facture d'un compteur {compteur_id}"
                    enregistre_historique(historique, utilisateur)

                    return {'status': 'success', 'message': 'Relevé enregistré avec succès !'}

            result = await process()
            return result
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}


async def process_compteur_details(compteur_id):
    try:
        # Encapsuler les opérations synchrones dans un thread
        @sync_to_async
        def get_details():
            with transaction.atomic():
                # Récupérer le compteur
                compteur = get_object_or_404(Compteur, num_compteur=compteur_id)
                compteur_info = {
                    'id': int(compteur.num_compteur),
                    'marque': compteur.marque_compteur,
                    'modele': compteur.modele_compteur,
                }

                # Récupérer le contrat
                contrat = get_object_or_404(Contrat, num_compteur=compteur_id)
                num_contrat_match = re.search(r'\d+', contrat.num_contrat)
                if not num_contrat_match:
                    raise ValueError("Numéro de contrat invalide : aucun chiffre trouvé")
                num_contrat = num_contrat_match.group()

                contrat_info = {
                    'id': int(num_contrat),
                    'numero_contrat': contrat.num_contrat,
                    'date_debut': contrat.date_debut,
                    'date_fin': contrat.date_fin,
                    'adresse_contrat': contrat.adresse_contrat,
                    'pays_contrat': contrat.pays_contrat,
                }

                # Récupérer le client
                client = contrat.client
                client_info = {
                    'id': client.num_client,
                    'nom': client.nom_client,
                    'prenom': client.prenom_client or '',
                    'adresse': client.adresse_client,
                    'commune': client.cp_commune.commune,
                    'region': client.cp_commune.region.region,
                    'telephone1': client.tel1_client,
                    'telephone2': client.tel2_client or '',
                    'actif': client.compte_actif
                }

                # Récupérer les relevés
                releves_data = ReleveCompteur.objects.filter(num_compteur=compteur).order_by('-date_releve')
                releves_list = [
                    {
                        'id': int(releve.id_releve),
                        'id_releve': int(releve.id_releve),
                        'compteur_id': int(compteur.num_compteur),
                        'contrat_id': int(num_contrat),
                        'client_id': int(client.num_client),
                        'date_releve': releve.date_releve,
                        'volume': releve.volume,
                        'conso': releve.conso,
                        'image_compteur': releve.image_compteur.url if releve.image_compteur else None,
                        'etatFacture': 'Payé' if (facture := Facture.objects.filter(relevecompteur=releve).first()) and facture.statut else 'Impayé' if facture else 'Pas de facture'
                    }
                    for releve in releves_data
                ]

                return {
                    'compteur': compteur_info,
                    'contrat': contrat_info,
                    'client': client_info,
                    'releves': releves_list
                }

        resultat = await get_details()
        return resultat

    except Compteur.DoesNotExist:
        raise ValueError('Compteur non trouvé')
    except Contrat.DoesNotExist:
        raise ValueError('Contrat non trouvé')
    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f"Erreur dans process_compteur_details pour compteur_id={compteur_id}: {str(e)}", exc_info=True)
        raise Exception(str(e))


class TaskFactureDetail:
    @staticmethod
    async def process_facture_list(id_releve):
        try:
            @sync_to_async
            def get_facture_details():
                with transaction.atomic():
                    releve = Facture.objects.select_related(
                        'num_contrat__client',
                        'num_contrat__cp_commune'
                    ).get(relevecompteur_id=id_releve)

                    if not releve:
                        return {'status': 'error', 'message': 'La facture n\'a pas été trouvée pour l\'ID de relevé spécifié'}

                    montant_ht = MontantHT.objects.get(facture_id=releve.id_facture)

                    avoir_avant = releve.avoir_avant if releve.avoir_avant else 0.0
                    avoir_utilise = releve.avoir_utilise if releve.avoir_utilise else 0.0
                    restant_precedant = releve.restant_precedant if releve.restant_precedant else 0.0
                    restant_nouvel = releve.restant_nouvel if releve.restant_nouvel else 0.0
                    montant_total_ttc = releve.montant_total_ttc if releve.montant_total_ttc else 0.0

                    montant_payer = 0.0 if montant_total_ttc == 0.0 or restant_nouvel == 0.0 \
                        else montant_total_ttc - restant_nouvel

                    typeclient = releve.num_contrat.client.type_client_id
                    cp_commune = releve.num_contrat.cp_commune_id
                    tarif = Tarif.objects.filter(cp_commune_id=cp_commune).first()
                    tarif_m3 = {
                        1: tarif.prix_m3_bp,
                        2: tarif.prix_m3_bs,
                        3: tarif.prix_m3_k
                    }.get(typeclient, 0.0) if tarif else 0.0

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

            resultat = await get_facture_details()
            return resultat

        except Facture.DoesNotExist:
            return {'status': 'error', 'message': 'La facture n\'a pas été trouvée pour l\'ID de relevé spécifié'}
        except MontantHT.DoesNotExist:
            return {'status': 'error', 'message': 'Le montant HT n\'a pas été trouvé pour l\'ID de facture spécifié'}
        except Exception as e:
            logger.error(f"Erreur dans process_facture_list pour id_releve={id_releve}: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}

    @staticmethod
    async def process_facture_paiement(id_releve, montant_payer, utilisateur_id):
        try:
            @sync_to_async
            def process_payment():
                with transaction.atomic():
                    if montant_payer >= 0.1:
                        paiement(id_releve, montant_payer, utilisateur_id)  # Assurez-vous que paiement est synchrone
                        return {'status': 'success', 'message': 'Paiement effectué avec succès !'}
                    else:
                        return {'status': 'error', 'message': 'Le montant du paiement doit être supérieur ou égal à 0.1.'}

            resultat = await process_payment()
            return resultat

        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Erreur dans process_facture_paiement pour id_releve={id_releve}: {str(e)}", exc_info=True)
            raise Exception(str(e))

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
