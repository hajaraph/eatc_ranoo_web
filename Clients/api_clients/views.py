from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from Tenants.middleware import schema_use_api
from Rel_Compteur.api_utils import ApiResponse

from Clients.models import Client, TypeClient, PieceClient, Contrat
from .serializer import (
    ClientSerializer, ClientCreateSerializer,
    TypeClientSerializer,
    PieceClientSerializer,
    ContratSerializer, ContratCreateSerializer
)


# TypeClient CRUD
class TypeClientListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request):
        type_clients = TypeClient.objects.all()
        serializer = TypeClientSerializer(type_clients, many=True)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def post(request):
        serializer = TypeClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data, http_status=status.HTTP_201_CREATED)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)


class TypeClientDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request, pk):
        type_client = get_object_or_404(TypeClient, pk=pk)
        serializer = TypeClientSerializer(type_client)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def put(request, pk):
        type_client = get_object_or_404(TypeClient, pk=pk)
        serializer = TypeClientSerializer(type_client, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def delete(request, pk):
        type_client = get_object_or_404(TypeClient, pk=pk)
        type_client.delete()
        return ApiResponse.success(data={"message": "TypeClient supprimé avec succès"})


# Client CRUD
class ClientListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request):
        clients = Client.objects.select_related('cp_commune', 'type_client').prefetch_related('contrats__num_compteur').all()
        
        # Filtrage par compte_actif
        actif = request.GET.get('actif')
        if actif is not None:
            clients = clients.filter(compte_actif=actif.lower() == 'true')
        
        # Filtrage par commune
        commune_id = request.GET.get('commune_id')
        if commune_id:
            clients = clients.filter(cp_commune_id=commune_id)
        
        # Filtrage par type_client
        type_client_id = request.GET.get('type_client_id')
        if type_client_id:
            clients = clients.filter(type_client_id=type_client_id)
        
        # Recherche par nom ou prénom
        search = request.GET.get('search')
        if search:
            clients = clients.filter(
                nom_client__icontains=search
            ) | clients.filter(
                prenom_client__icontains=search
            )
        
        serializer = ClientSerializer(clients, many=True)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def post(request):
        serializer = ClientCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data, http_status=status.HTTP_201_CREATED)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)


class ClientDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request, pk):
        client = get_object_or_404(Client.objects.select_related('cp_commune', 'type_client'), pk=pk)
        serializer = ClientSerializer(client)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def put(request, pk):
        client = get_object_or_404(Client.objects.select_related('cp_commune', 'type_client'), pk=pk)
        serializer = ClientCreateSerializer(client, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def patch(request, pk):
        client = get_object_or_404(Client.objects.select_related('cp_commune', 'type_client'), pk=pk)
        serializer = ClientCreateSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def delete(request, pk):
        client = get_object_or_404(Client, pk=pk)
        client.delete()
        return ApiResponse.success(data={"message": "Client supprimé avec succès"})


# PieceClient CRUD
class PieceClientListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request):
        client_id = request.GET.get('client_id')
        if client_id:
            pieces = PieceClient.objects.filter(client_id=client_id)
        else:
            pieces = PieceClient.objects.select_related('client').all()
        
        serializer = PieceClientSerializer(pieces, many=True)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def post(request):
        serializer = PieceClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data, http_status=status.HTTP_201_CREATED)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)


class PieceClientDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request, pk):
        piece = get_object_or_404(PieceClient.objects.select_related('client'), pk=pk)
        serializer = PieceClientSerializer(piece)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def put(request, pk):
        piece = get_object_or_404(PieceClient.objects.select_related('client'), pk=pk)
        serializer = PieceClientSerializer(piece, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def delete(request, pk):
        piece = get_object_or_404(PieceClient, pk=pk)
        piece.delete()
        return ApiResponse.success(data={"message": "PieceClient supprimé avec succès"})


# Contrat CRUD
class ContratListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request):
        contrats = Contrat.objects.select_related('client', 'num_compteur', 'cp_commune', 'utilisateur').all()
        
        # Filtrage par client
        client_id = request.GET.get('client_id')
        if client_id:
            contrats = contrats.filter(client_id=client_id)
        
        # Filtrage par compteur
        compteur_id = request.GET.get('compteur_id')
        if compteur_id:
            contrats = contrats.filter(num_compteur_id=compteur_id)
        
        # Filtrage par commune
        commune_id = request.GET.get('commune_id')
        if commune_id:
            contrats = contrats.filter(cp_commune_id=commune_id)
        
        serializer = ContratSerializer(contrats, many=True)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def post(request):
        serializer = ContratCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data, http_status=status.HTTP_201_CREATED)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)


class ContratDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    @schema_use_api
    def get(request, num_contrat):
        contrat = get_object_or_404(Contrat.objects.select_related('client', 'num_compteur', 'cp_commune', 'utilisateur'), pk=num_contrat)
        serializer = ContratSerializer(contrat)
        return ApiResponse.success(data=serializer.data)

    @staticmethod
    @schema_use_api
    def put(request, num_contrat):
        contrat = get_object_or_404(Contrat.objects.select_related('client', 'num_compteur', 'cp_commune', 'utilisateur'), pk=num_contrat)
        serializer = ContratCreateSerializer(contrat, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def patch(request, num_contrat):
        contrat = get_object_or_404(Contrat.objects.select_related('client', 'num_compteur', 'cp_commune', 'utilisateur'), pk=num_contrat)
        serializer = ContratCreateSerializer(contrat, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return ApiResponse.success(data=serializer.data)
        return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

    @staticmethod
    @schema_use_api
    def delete(request, num_contrat):
        contrat = get_object_or_404(Contrat, pk=num_contrat)
        contrat.delete()
        return ApiResponse.success(data={"message": "Contrat supprimé avec succès"})
