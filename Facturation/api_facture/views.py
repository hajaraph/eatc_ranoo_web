import calendar
from datetime import datetime

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from Tenants.middleware import schema_use_api
from Rel_Compteur.api_utils import ApiResponse
from Login.permissions import IsAdminOuGestionnaire

from Facturation.models import Facture
from .serializer import (
    FactureListSerializer,
    FactureDetailSerializer,
    PaiementCreateSerializer,
    PaiementSerializer,
)


class FactureListView(APIView):
    """Liste des factures avec filtres optionnels."""
    permission_classes = [IsAdminOuGestionnaire]

    @staticmethod
    @schema_use_api
    def get(request):
        queryset = Facture.objects.select_related(
            'num_contrat__client',
            'num_contrat__cp_commune',
            'num_contrat__num_compteur',
        ).prefetch_related('paiements').all()

        # Filtre par mois (YYYY-MM) - prioritaire sur date_deb/date_fin
        mois = request.query_params.get('mois')
        if mois:
            try:
                annee, mois_num = map(int, mois.split('-'))
                dernier_jour = calendar.monthrange(annee, mois_num)[1]
                date_deb = f"{mois}-01"
                date_fin = f"{mois}-{dernier_jour:02d}"
                queryset = queryset.filter(
                    date_facture__gte=date_deb,
                    date_facture__lte=date_fin,
                )
            except (ValueError, IndexError):
                pass
        else:
            date_deb = request.query_params.get('date_deb')
            if date_deb:
                queryset = queryset.filter(date_facture__gte=date_deb)

            date_fin = request.query_params.get('date_fin')
            if date_fin:
                queryset = queryset.filter(date_facture__lte=date_fin)

        # Filtres optionnels
        statut = request.query_params.get('statut')
        if statut == 'paye':
            queryset = queryset.filter(statut=True)
        elif statut == 'impaye':
            queryset = queryset.filter(statut=False)

        commune = request.query_params.get('commune')
        if commune:
            queryset = queryset.filter(num_contrat__cp_commune_id=commune)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(num_facture__icontains=search) |
                models.Q(num_contrat__client__nom_client__icontains=search) |
                models.Q(num_contrat__client__prenom_client__icontains=search) |
                models.Q(num_contrat__client__num_client__icontains=search)
            )

        queryset = queryset.order_by('-date_facture')

        serializer = FactureListSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data)


class FactureDetailView(APIView):
    """Detail d'une facture."""
    permission_classes = [IsAdminOuGestionnaire]

    @staticmethod
    @schema_use_api
    def get(request, pk):
        facture = get_object_or_404(
            Facture.objects.select_related(
                'num_contrat__client',
                'num_contrat__cp_commune',
                'num_contrat__num_compteur',
            ).prefetch_related('paiements'),
            pk=pk
        )
        serializer = FactureDetailSerializer(facture)
        return ApiResponse.success(data=serializer.data)


class FacturePaiementView(APIView):
    """Enregistrer un paiement pour une facture."""
    permission_classes = [IsAdminOuGestionnaire]

    @staticmethod
    @schema_use_api
    def post(request, pk):
        facture = get_object_or_404(Facture, pk=pk)

        serializer = PaiementCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse.error(
                "Erreur de validation",
                code="VALIDATION_ERROR",
                details=serializer.errors
            )

        paiement = serializer.save(facture=facture)

        # Mettre a jour le statut si le montant total est paye
        total_paye = facture.paiements.aggregate(
            total=models.Sum('montant_payer')
        )['total'] or 0

        if total_paye >= (facture.montant_total_ttc or 0):
            facture.statut = True
            facture.save(update_fields=['statut'])

        return ApiResponse.success(
            data=PaiementSerializer(paiement).data,
            http_status=status.HTTP_201_CREATED
        )


