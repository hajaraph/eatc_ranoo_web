import re
import logging
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db.models import Max, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

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
    def process_liste_mission(cp_commune, end_of_month, limit=None, offset=0, status_filter=None, bypass_cache=False, modified_since=None):
        """
        Récupère la liste des missions (compteurs à relever) pour une commune.
        
        Args:
            cp_commune: ID de la commune
            end_of_month: Fin du mois en cours
            limit: Nombre max de résultats (None = tous)
            offset: Décalage pour la pagination
            status_filter: Filtrer par statut (0=non-relevé, 2=relevé)
            bypass_cache: Si True, force le recalcul sans utiliser le cache
            modified_since: Date de dernière synchronisation (Delta Sync)
        
        Returns:
            dict avec 'liste', 'total_count', 'has_more'
        """
        logger.info(f"Début process_liste_mission pour cp_commune={cp_commune}, limit={limit}, offset={offset}, bypass_cache={bypass_cache}, modified_since={modified_since}")
        
        # Clé de cache inclut les paramètres de pagination et de date
        date_str = modified_since.timestamp() if modified_since else '0'
        cache_key = f"missions_liste_{cp_commune}_{end_of_month.strftime('%Y%m%d')}_{limit}_{offset}_{status_filter}_{date_str}"

        try:
            # Essayer de récupérer depuis le cache si on ne le bypass pas
            if not bypass_cache and not modified_since:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info("Données récupérées depuis le cache")
                    return cached_result

            # Si pas dans le cache, calculer les données
            from django.db.models import OuterRef, Subquery, Max as DjangoMax, Q
            
            with transaction.atomic():
                # Sous-requête pour obtenir la dernière date de relevé (hors rejetés)
                dernier_releve_subquery = ReleveCompteur.objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).exclude(statut_validation='REJETE').order_by('-date_releve').values('date_releve')[:1]
                    
                # Sous-requête pour obtenir le dernier volume (hors rejetés)
                dernier_volume_subquery = ReleveCompteur.objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).exclude(statut_validation='REJETE').order_by('-date_releve').values('volume')[:1]
                
                # Sous-requête pour obtenir le dernier ID de relevé (hors rejetés)
                dernier_releve_id_subquery = ReleveCompteur.objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).exclude(statut_validation='REJETE').order_by('-date_releve').values('id_releve')[:1]
                
                # Sous-requête pour obtenir la dernière consommation (hors rejetés)
                dernier_conso_subquery = ReleveCompteur.objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).exclude(statut_validation='REJETE').order_by('-date_releve').values('conso')[:1]
                
                # Sous-requête pour obtenir le statut de validation du dernier relevé (y compris rejeté)
                # On trie par id_releve pour avoir l'état le plus récent de façon certaine
                dernier_statut_validation_subquery = ReleveCompteur.all_objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).order_by('-id_releve').values('statut_validation')[:1]

                # Sous-requête pour obtenir le motif de rejet du dernier relevé (y compris rejeté)
                dernier_motif_rejet_subquery = ReleveCompteur.all_objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).order_by('-id_releve').values('motif_rejet')[:1]

                # Sous-requête pour savoir si le dernier relevé créé est supprimé (soft deleted)
                dernier_is_deleted_subquery = ReleveCompteur.all_objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).order_by('-created_at').values('is_deleted')[:1]

                # Sous-requête pour obtenir la date de dernière modification (y compris supprimés) pour la sync
                dernier_updated_at_subquery = ReleveCompteur.all_objects.filter(
                    num_compteur=OuterRef('num_compteur')
                ).order_by('-updated_at').values('updated_at')[:1]
                
                # Requête principale optimisée avec sous-requêtes
                contrats_queryset = (
                    Contrat.objects
                    .filter(cp_commune_id=cp_commune)
                    .select_related('client', 'num_compteur')
                    .annotate(
                        dernier_releve_date=Subquery(dernier_releve_subquery),
                        dernier_volume=Subquery(dernier_volume_subquery),
                        dernier_releve_id=Subquery(dernier_releve_id_subquery),
                        dernier_conso=Subquery(dernier_conso_subquery),
                        dernier_statut_validation=Subquery(dernier_statut_validation_subquery),
                        dernier_motif_rejet=Subquery(dernier_motif_rejet_subquery),
                        dernier_is_deleted=Subquery(dernier_is_deleted_subquery),
                        dernier_updated_at=Subquery(dernier_updated_at_subquery),
                    )
                )
                
                # === OPTIMISATION MAJEURE DU DELTA SYNC ===
                if modified_since:
                    # Marge de sécurité de 1 seconde pour éviter les problèmes de précision
                    effective_since = modified_since - timezone.timedelta(seconds=1)
                    
                    # Demander uniquement les lignes modifiées à PostgreSQL
                    # On inclut num_compteur OR releve_updated_at (qui inclut les rejets)
                    contrats_queryset = contrats_queryset.filter(
                        Q(num_compteur__updated_at__gte=effective_since) |
                        Q(dernier_updated_at__gte=effective_since)
                    )
                
                # Exclure les compteurs déjà relevés ce mois-ci (sauf delta sync et sauf si on demande explicitement le statut 2)
                if not modified_since and status_filter != 2:
                    current_month = end_of_month.month
                    current_year = end_of_month.year
                    
                    # Sous-requête: compteurs ayant un relevé confirmé (non rejeté) dans le mois courant
                    compteurs_deja_releves = ReleveCompteur.objects.filter(
                        num_compteur=OuterRef('num_compteur'),
                        date_releve__month=current_month,
                        date_releve__year=current_year,
                    ).exclude(statut_validation='REJETE')
                    
                    from django.db.models import Exists
                    contrats_queryset = contrats_queryset.annotate(
                        a_releve_mois_courant=Exists(compteurs_deja_releves)
                    ).exclude(a_releve_mois_courant=True)
                
                # Compter le total avant pagination
                total_count = contrats_queryset.count()
                
                # Appliquer la pagination
                if limit is not None:
                    contrats_commune = list(contrats_queryset[offset:offset + limit])
                    has_more = (offset + limit) < total_count
                else:
                    contrats_commune = list(contrats_queryset)
                    has_more = False

                liste_contrats_info = []
                for contrat in contrats_commune:
                    # Déterminer si la mission est rejetée
                    statut_validation = contrat.dernier_statut_validation
                    
                    # LOGIQUE SPÉCIALE REJET : On transforme la mission en "Nouvelle" pour le mobile
                    if statut_validation == 'REJETE':
                        statut = 0
                        final_updated_at = timezone.now() # Force la visibilité dans le Delta Sync
                    else:
                        # Cas classique : calcul du statut selon la date du mois
                        date_releve = contrat.dernier_releve_date
                        if date_releve and hasattr(date_releve, 'month') and date_releve.month == end_of_month.month:
                            statut = 2  # Déjà fait
                        else:
                            statut = 0  # Nouveau
                            
                    # Récupérer l'ID du dernier relevé (celui du mois dernier si rejeté, ou 0)
                    releve_id = 0
                    if contrat.dernier_releve_id:
                        try:
                            releve_id = int(contrat.dernier_releve_id)
                        except (ValueError, TypeError):
                            releve_id = 0
                    
                    # Si c'était rejeté mais qu'on a un ID de relevé (celui du mois dernier), 
                    # le mobile verra id_local (rejeté) != id_serveur (précédent), ce qui est bon.
                    
                    if statut_validation != 'REJETE':
                        # Calcul du updated_at global classique
                        compteur_updated_at = contrat.num_compteur.updated_at
                        releve_updated_at = contrat.dernier_updated_at
                        final_updated_at = compteur_updated_at
                        if releve_updated_at and releve_updated_at > compteur_updated_at:
                            final_updated_at = releve_updated_at
                    
                    # Filtrer par statut si demandé
                    if status_filter is not None and statut != status_filter:
                        continue

                    # Récupérer les 3 derniers relevés pour ce compteur (hors rejetés)
                    derniers_releves_qs = ReleveCompteur.objects.filter(
                        num_compteur=contrat.num_compteur
                    ).exclude(statut_validation='REJETE').order_by('-date_releve')[:3]
                    
                    derniers_releves = [
                        {
                            'date_releve': str(r.date_releve) if r.date_releve else '',
                            'volume': r.volume or 0,
                            'conso': r.conso or 0,
                            'statut_validation': r.statut_validation,
                        }
                        for r in derniers_releves_qs
                    ]

                    contrat_info = {
                        'id': releve_id,
                        'nom_client': contrat.client.nom_client,
                        'prenom_client': contrat.client.prenom_client if contrat.client.prenom_client else '',
                        'adresse_client': contrat.client.adresse_client,
                        'num_compteur': contrat.num_compteur_id,
                        'conso_dernier_releve': contrat.dernier_conso or 0,
                        'volume_dernier_releve': contrat.dernier_volume or 0,
                        'date_releve': contrat.dernier_releve_date if contrat.dernier_releve_date else '',
                        'statut': statut,
                        'statut_validation': contrat.dernier_statut_validation,
                        'motif_rejet': contrat.dernier_motif_rejet,
                        'last_is_deleted': contrat.dernier_is_deleted,
                        'is_deleted': getattr(contrat.num_compteur, 'is_deleted', False),
                        'updated_at': final_updated_at.isoformat() if final_updated_at else None,
                        'derniers_releves': derniers_releves,
                    }
                    liste_contrats_info.append(contrat_info)

                # Trier la liste par ID
                liste_contrats_info = sorted(liste_contrats_info, key=lambda x: x['id'])
                
                # Si on a filtré par statut, recalculer has_more
                if status_filter is not None:
                    has_more = False  # On ne peut pas savoir facilement avec le filtre

            result = {
                'liste': liste_contrats_info,
                'total_count': total_count,
                'returned_count': len(liste_contrats_info),
                'has_more': has_more,
                'offset': offset,
                'limit': limit,
            }

            # Mettre en cache avec un timeout de 5 minutes (Seulement si ce n'est pas un delta_sync)
            if not bypass_cache and not modified_since:
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
    def process_releve(data, utilisateur):
        serializer = MissionSerializer(instance=None, data=data)

        if not serializer.is_valid(raise_exception=False):
            return {'status': 'error', 'message': serializer.errors}

        try:
            with transaction.atomic():
                validated_data = serializer.validated_data
                compteur_id = validated_data.get('num_compteur')
                date_releve = validated_data.get('date_releve')
                volume = validated_data.get('volume')
                image_compteur = validated_data.get('image_compteur')

                if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exclude(statut_validation='REJETE').exists():
                    return {'status': 'error', 'message': "La date de relevé existe déjà dans la base de données"}

                dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).exclude(statut_validation='REJETE').latest('date_releve')

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

        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}


def process_compteur_details(compteur_id):
    try:
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
    def process_facture_list(id_releve):
        try:
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

        except Facture.DoesNotExist:
            return {'status': 'error', 'message': 'La facture n\'a pas été trouvée pour l\'ID de relevé spécifié'}
        except MontantHT.DoesNotExist:
            return {'status': 'error', 'message': 'Le montant HT n\'a pas été trouvé pour l\'ID de facture spécifié'}
        except Exception as e:
            logger.error(f"Erreur dans process_facture_list pour id_releve={id_releve}: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f"Erreur du serveur: {str(e)}"}

    @staticmethod
    def process_facture_paiement(id_releve, montant_payer, utilisateur_id):
        try:
            with transaction.atomic():
                if montant_payer >= 0.1:
                    paiement(id_releve, montant_payer, utilisateur_id)  # Assurez-vous que paiement est synchrone
                    return {'status': 'success', 'message': 'Paiement effectué avec succès !'}
                else:
                    return {'status': 'error', 'message': 'Le montant du paiement doit être supérieur ou égal à 0.1.'}

        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(str(e))
