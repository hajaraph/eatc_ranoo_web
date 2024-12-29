import pandas as pd
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from Clients.models import Contrat
from Parametre.views import enregistre_historique

from .serializer import MissionSerializer
from Tasks.tasks import TaskMission, process_compteur_details, TaskFactureDetail
from Compteurs.models import Compteur, ReleveCompteur
from Facturation.models import Facture
from Facturation.views import facture_creation
from Main_Courante.models import MainCourante
from pandas.tseries.offsets import MonthEnd

from ..views import relever, ReleveMod


def calculer_nombre_relever_effectuer(cp_commune_id):
    # Calcul du nombre total de compteurs
    nombre_total_compteur = Compteur.objects.filter(contrats__cp_commune_id=cp_commune_id).count()

    # Calcul de la fin du mois actuel en utilisant pandas
    end_of_month = (
        pd.to_datetime('now')
        .to_period('M')
        .to_timestamp()
        + MonthEnd(0)
    )

    # Filtrer les contrats avec des relevés dans le mois actuel
    contrat_data = (
        Contrat.objects
        .filter(cp_commune_id=cp_commune_id)
        .annotate(releve_count=Count(
            'num_compteur__relevecompteurs',
            filter=Q(num_compteur__relevecompteurs__date_releve__month=end_of_month.month)))
        .distinct()
    )

    contrat_list = list(contrat_data)

    # Calculer le nombre_relever_effectuer
    nombre_relever_effectuer = sum(1 for contrat in contrat_list if contrat.releve_count > 0)

    nombre_facture = Facture.objects.filter(
        relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id
    ).count()

    nombre_total_facture_payer = Facture.objects.filter(
        relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id,
        statut=True
    ).count()

    nombre_total_facture_impayer = nombre_facture - nombre_total_facture_payer
    nombre_total_facture_payer = nombre_facture - nombre_total_facture_impayer

    # Soustraire le nombre de relevés effectués du nombre total de compteurs
    nombre_total_compteur -= nombre_relever_effectuer
    nombre_relever_effectuer -= nombre_relever_effectuer

    return nombre_total_compteur, nombre_relever_effectuer, nombre_total_facture_impayer, nombre_total_facture_payer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accueil(request):
    cp_commune_id = request.user.cp_commune_id
    non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
    realise = MainCourante.objects.filter(statuts__realise=True).count()
    en_cours = MainCourante.objects.filter(statuts__en_cours=True).count()
    total_anomalie = non_traite + en_cours

    nombre_total_compteur, nombre_relever_effectuer, nombre_total_facture_impayer, nombre_total_facture_payer\
        = calculer_nombre_relever_effectuer(cp_commune_id)

    return JsonResponse(
        {
            'non_traite': non_traite,
            'realise': realise,
            'en_cours': en_cours,
            'totale_anomalie': total_anomalie,
            'nombre_total_compteur': nombre_total_compteur,
            'nombre_relever_effectuer': nombre_relever_effectuer,
            'nombre_total_facture_impayer': nombre_total_facture_impayer,
            'nombre_total_facture_payer': nombre_total_facture_payer
        }
    )


@api_view(['GET'])
def relever_client(request):
    compteur_id = request.GET.get('num_compteur')

    try:
        # Lancer la tâche Celery et attendre son résultat
        tache = process_compteur_details.delay(compteur_id)
        resultat = tache.get(timeout=10)  # ajuster le timeout selon vos besoins
        tache.forget()

        return JsonResponse(resultat)
    except Compteur.DoesNotExist:
        return JsonResponse({'error': 'Compteur non trouvé'}, status=404)
    except Contrat.DoesNotExist:
        return JsonResponse({'error': 'Contrat non trouvé'}, status=404)
    except ValueError as e:
        return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Missions(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        cp_commune = request.user.cp_commune_id
        end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)

        try:
            tache = TaskMission.process_liste_mission.apply_async(args=[cp_commune, end_of_month])
            resultat = tache.get(timeout=10)
            tache.forget()

            return JsonResponse({'compteurs_liste': resultat})
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {'erreur': f"Erreur du serveur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        serializer = MissionSerializer(data=request.data)
        utilisateur = request.user.id_utilisateur

        if not serializer.is_valid():
            return JsonResponse({'erreur': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                id_releve = serializer.validated_data.get('releve_id')
                compteur_id = serializer.validated_data.get('num_compteur')
                date_releve = serializer.validated_data.get('date_releve')
                volume = serializer.validated_data.get('volume')
                image_compteur = request.FILES.get('image_compteur')

                if id_releve is not None:
                    compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                    dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

                    if dernier_releve.volume >= volume:
                        return JsonResponse({
                            'erreur': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    if date_releve <= dernier_releve.date_releve:
                        return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                            status=status.HTTP_400_BAD_REQUEST)

                    mod_releve = ReleveMod.mod_relever_facture(id_releve, compteur, date_releve, volume,
                                                               image_compteur, dernier_releve)
                    facture_creation(date_releve, compteur.num_compteur, mod_releve)

                    return JsonResponse({
                        'enregistre': 'Mise à jour effectuer avec succès !'
                    }, status=status.HTTP_201_CREATED)

                else:
                    if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exists():
                        return JsonResponse({'erreur': "La date de relevé existe déjà dans la base de données"},
                                            status=status.HTTP_400_BAD_REQUEST)

                    dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).latest('date_releve')

                    if dernier_volume:
                        if date_releve <= dernier_volume.date_releve:
                            return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                                status=status.HTTP_400_BAD_REQUEST)

                        if dernier_volume.volume > volume:
                            return JsonResponse({
                                'erreur': "Assurez-vous de saisir les chiffres correctement et réessayez !"
                            }, status=status.HTTP_400_BAD_REQUEST)

                        else:
                            conso = volume - dernier_volume.volume
                    else:
                        conso = volume

                    releve = relever(dernier_volume.num_compteur_id, date_releve,
                                     volume, conso, image_compteur, utilisateur)

                    facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

                historique = f"Relever et Facture d'un compteur {compteur_id}"
                enregistre_historique(historique, utilisateur)

                return JsonResponse({'enregistre': True}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Details Facture #


class FactureDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        id_releve = request.GET.get('id_releve')
        try:
            tache = TaskFactureDetail.precess_facture_list.apply_async(args=[id_releve])
            resultat = tache.get(timeout=10)
            tache.forget()

            return JsonResponse({'facture': resultat})
        except Facture.DoesNotExist:
            return JsonResponse({'error': 'Facture non trouvé'}, status=404)
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        id_releve = request.data.get('relevecompteur_id')
        montant_payer = float(request.data.get('paiement'))
        utilisateur = request.user.id_utilisateur

        try:
            tache = TaskFactureDetail.process_facture_paiement.delay(id_releve, montant_payer, utilisateur)
            tache.forget()

            return JsonResponse({'message': "tâche mis en attente !"})
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {'erreur': f"Erreur du serveur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_missions_details(toutes_missions):
    missions_details = []
    for mission in toutes_missions:
        compteur_id = mission['num_compteur__num_compteur']
        compteur = get_object_or_404(Compteur, num_compteur=compteur_id)
        contrat = get_object_or_404(Contrat, num_compteur=compteur)
        client = contrat.client
        releves_data = ReleveCompteur.objects.filter(num_compteur=compteur).order_by('-date_releve')
        releves_list = []
        for releve in releves_data:
            releves_list.append({
                'id_relelve': releve.pk,
                'date_releve': releve.date_releve,
                'volume': releve.volume,
                'conso': releve.conso,
            })
        missions_details.append({
            'compteur': {
                'id': compteur.num_compteur,
                'marque': compteur.marque_compteur,
                'modele': compteur.modele_compteur,
            },
            'contrat': {
                'id': contrat.num_contrat,
                'numero_contrat': contrat.num_contrat,
                'date_debut': contrat.date_debut,
                'date_fin': contrat.date_fin,
                'adresse_contrat': contrat.adresse_contrat,
                'pays_contrat': contrat.pays_contrat,
            },
            'client': {
                'id': client.id_client,
                'nom': client.nom_client,
                'prenom': client.prenom_client,
                'adresse': client.adresse_client,
                'commune': client.cp_commune.commune,
                'region': client.cp_commune.region.region,
                'tephone1': client.tel1_client,
                'tephone2': client.tel2_client,
                'actif': client.compte_actif
            },
            'releves': releves_list
        })
    return missions_details
