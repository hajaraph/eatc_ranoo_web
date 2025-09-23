import os
import re
from io import BytesIO

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from datetime import datetime
from xhtml2pdf import pisa

from Clients.models import Client, PieceClient, Contrat, TypeClient
from Compteurs.models import Compteur
from Facturation.models import Tarif, Facture
from Login.views import role_requis
from Parametre.views import enregistre_historique, exporter_en_excel
from Acommune.models import Province, Commune
from Tenants.middleware import schema_use, SchemaAwareView
from Rel_Compteur.utils import filter_by_user_role


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def client_liste(request):
    title = 'Clients | Liste'
    active = 'active'
    font = 'custom-font'

    client = filter_by_user_role(request, Client.objects.all().order_by('pk'), 'cp_commune')
    province = Province.objects.order_by('region').all()
    context = {
        'title_liste': title,
        'active_liste': active,
        'font_client': font,
        'client': client,
        'provinces': province
    }
    return render(request, 'all_page/clients/content_client.html', context)


def extract_client_data(request):
    return {
        'num_client': request.POST.get('id_client'),  # Utilisation de .get() au lieu de []
        'nom_client': request.POST['nom_client'],
        'prenom_client': request.POST.get('prenom_client'),
        'profession_client': request.POST.get('profession_client'),
        'nb_personne_menage': request.POST.get('nb_personne_menage'),
        'compte_actif': request.POST.get('compte_actif', False),
        'adresse_client': request.POST['adresse_client'],
        'cp_commune': request.POST['commune'],
        'pays_client': request.POST['pays_client'],
        'tel1_client': request.POST.get('tel1_client'),
        'tel2_client': request.POST.get('tel2_client'),
        'email_client': request.POST.get('email_client'),
        'piece_client': request.FILES.getlist('piece_client'),
        'designation': request.POST.getlist('designation'),
    }


def extract_contrat_data(request):
    return {
        'adresse_contrat': request.POST['adresse_contrat'],
        'cp_commune': request.POST['commune'],
        'pays_contrat': request.POST['pays_contrat'],
    }


class ClientNew(SchemaAwareView):
    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        title = 'Nouveau Client'
        active = 'active'
        font = 'custom-font'
        province = Province.objects.all().order_by('province')
        type_client = TypeClient.objects.all()
        context = {
            'title_new': title,
            'active_liste': active,
            'font_client': font,
            'provinces': province,
            'type': type_client
        }
        return render(request, 'all_page/clients/content_client.html', context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        try:
            client_data = extract_client_data(request)

            # Vérification d'unicité du numéro de client par commune
            num_client = client_data['num_client']
            if num_client:
                # Vérifier si le numéro existe déjà dans la même commune
                client_existant = Client.objects.filter(
                    num_client=num_client,
                    cp_commune_id=client_data['cp_commune']
                ).exists()

                if client_existant:
                    messages.warning(request, f'Le numéro Client {num_client} existe déjà dans cette commune !')
                    return redirect('client_new')

            tel1_value = client_data['tel1_client']
            if tel1_value:  # Ne vérifie que si tel1_client n'est pas None ou ''
                tel = Client.objects.filter(tel1_client=tel1_value)
                if tel.exists():
                    messages.warning(request, f'Téléphone 1 déjà utilisé par un client !')
                    return redirect('client_new')

            tel2_value = client_data['tel2_client']
            if tel2_value:  # Ne vérifie que si tel2_client n'est pas None ou ''
                tel = Client.objects.filter(tel2_client=tel2_value)
                if tel.exists():
                    messages.warning(request, f'Téléphone 2 déjà utilisé par un client !')
                    return redirect('client_new')

            # Création du client
            client = Client.objects.create(
                num_client=client_data['num_client'],  # Sauvegarde du numéro de client
                nom_client=client_data['nom_client'],
                prenom_client=client_data['prenom_client'],
                profession_client=client_data['profession_client'],
                nb_personne_menage=client_data['nb_personne_menage'],
                compte_actif=client_data['compte_actif'],
                adresse_client=client_data['adresse_client'],
                cp_commune_id=client_data['cp_commune'],
                pays_client=client_data['pays_client'],
                tel1_client=client_data['tel1_client'],
                tel2_client=client_data['tel2_client'],
                email_client=client_data['email_client'],
                type_client_id=request.POST['type_client_id']
            )

            # Ajout des pièces jointes
            for file, design in zip(client_data['piece_client'], client_data['designation']):
                PieceClient.objects.create(
                    client_id=client.id_client,
                    pieces_client=file,
                    designation=design
                )

            messages.success(request, f'Client enregistré avec succès !')
            historique = f'Création du Client {client.nom_client} {client.prenom_client}'
            enregistre_historique(historique, request.session.get('id_utilisateur'))
            return redirect('client_liste')

        except Exception as e:
            messages.error(request, f'Erreur {e} lors de l\'enregistrer du client !')
            return redirect('client_new')


class ClientDetail(SchemaAwareView):
    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request, pk, *args, **kwargs):
        client_detail = Client.objects.get(pk=pk)
        pieces_client = client_detail.piececlients.all()
        contrat = client_detail.contrats.exists()
        provinces = Province.objects.all().order_by('province')
        type_client = TypeClient.objects.all()

        title = f"Client | Detail | {client_detail.nom_client} {client_detail.prenom_client}"
        active = 'active'
        font = 'custom-font'
        context = {
            'title_detail': title,
            'detail': client_detail,
            'contrat': contrat,
            'font_client': font,
            'active_li_liste': active,
            'active_liste': active,
            'piece_client': pieces_client,
            'provinces': provinces,
            'type': type_client
        }
        return render(request, 'all_page/clients/content_client.html', context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk, *args, **kwargs):
        client_data = extract_client_data(request)
        client = Client.objects.get(pk=pk)
        historique = (f"Client ID {client.pk} - Modification des informations pour {client.nom_client} "
                      f"{client.prenom_client}")
        msg = f'{client.nom_client} {client.prenom_client}'

        client_id = client.pk
        client.nom_client = client_data['nom_client']
        client.prenom_client = client_data['prenom_client']
        client.compte_actif = client_data['compte_actif']
        client.adresse_client = client_data['adresse_client']
        client.cp_commune_id = client_data['cp_commune']
        client.pays_client = client_data['pays_contrat']
        client.tel1_client = client_data['tel1_client']
        client.tel2_client = client_data['tel2_client']
        client.email_client = client_data['email_client']
        client.save()

        for file, design in zip(client_data['piece_client'], client_data['designation']):
            client.piececlients.create(
                client_id=client_id,
                pieces_client=file,
                designation=design
            )
        # Historique
        enregistre_historique(historique, request.session.get('id_utilisateur'))
        messages.success(request, f"Le client {msg} est modifié avec succès !")
        return redirect('client_detail', pk)


@role_requis('Administrateur')
@schema_use
def delete_client(request, pk):
    client = Client.objects.get(pk=pk)
    message = f"Client ID {client.pk} - Suppression du profil de {client.nom_client} {client.prenom_client}"
    # Pour supprimer tout le fichier stocker dans le serveur
    for piece in client.piececlients.all():
        if os.path.exists(piece.pieces_client.path):
            os.remove(piece.pieces_client.path)

    client.piececlients.all().delete()
    client.delete()
    # Historique
    enregistre_historique(message, request.session.get('id_utilisateur'))
    messages.success(request, "Client supprimer avec succès !")
    return redirect('client_liste')


@role_requis('Administrateur')
@schema_use
def supp_file_client(request, pk):
    file = get_object_or_404(PieceClient, pk=pk)

    message = (f"Suppression de la pièce '{file.designation}' du client ID "
               f"{file.client.pk} - {file.client.nom_client} {file.client.prenom_client}")

    file.pieces_client.delete()
    file.delete()
    # Historique
    enregistre_historique(message, request.session.get('id_utilisateur'))
    messages.success(request, f"Pièces supprimé avec succès !")
    return redirect('client_detail', file.client_id)


class ClientContrat(SchemaAwareView):

    template_name = 'all_page/clients/content_client.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request, pk, *args, **kwargs):
        active = 'active'
        font = 'custom-font'

        title = ''
        client = ''
        contrats = ''
        contrat = ''

        try:
            if Client.objects.filter(pk=pk).exists():
                client = Client.objects.get(pk=pk)
                contrats = client.contrats.all()
                contrat = client.contrats.latest('date_debut')
            else:
                client = Client.objects.get(contrats__num_contrat=pk)
                contrats = client.contrats.all()
                contrat = client.contrats.get(num_contrat=pk)

            title = f'Clients | Detail | Contrats | {client.nom_client} {client.prenom_client}'

        except Client.DoesNotExist:
            messages.warning(request, "Ce contrat n'exist pas")

        provinces = Province.objects.all().order_by('province')
        type_client = TypeClient.objects.all().order_by('designation_client')

        context = {
            'title_li_contrat': title,
            'active_li_contrat': active,
            'active_liste': active,
            'contrat': True,
            'font_client': font,
            'contrats': contrats,
            'detail': client,
            'detail_co': contrat,
            'provinces': provinces,
            'type': type_client
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request, pk, *args, **kwargs):
        nom_client = request.POST['nom_client']
        prenom_client = request.POST['prenom_client']
        num_contrat = request.POST['num_contrat'] if 'num_contrat' in request.POST else None
        contrat_data = extract_contrat_data(request)

        if Client.objects.filter(pk=pk).exists():
            client = Client.objects.get(pk=pk)
            contrat = client.contrats.get(num_contrat=num_contrat)
        else:
            client = Client.objects.get(contrats__num_contrat=pk)
            contrat = client.contrats.get(num_contrat=pk)

        client.nom_client = nom_client
        client.prenom_client = prenom_client
        client.save()

        num_contrat_original = num_contrat  # Copie du numéro de contrat original
        suffix_pattern = r'\((\d+)\)$'  # Modèle de suffixe numérique avec parenthèses
        match = re.search(suffix_pattern, num_contrat_original)

        if match:
            # Si un suffixe numérique avec parenthèses est trouvé, extrait et incrémente le suffixe
            suffix = int(match.group(1)) + 1
            num_contrat = re.sub(suffix_pattern, f'({suffix})', num_contrat_original)
        else:
            # Si aucun suffixe numérique avec parenthèses n'est trouvé, ajoute le suffixe (1).
            num_contrat = f"{num_contrat_original}(1)"

        client.contrats.create(
            num_contrat=num_contrat,
            client_id=client.pk,
            num_compteur_id=contrat.num_compteur.pk,
            adresse_contrat=contrat_data['adresse_contrat'],
            cp_commune_id=contrat_data['cp_commune'],
            pays_contrat=contrat_data['pays_contrat'],
            date_debut=contrat.date_debut,
            date_fin=contrat.date_fin,
            utilisateur_id=request.session.get('id_utilisateur')
        )
        # Historique
        message = f"Modification de contrat numéro - {num_contrat}"
        enregistre_historique(message, request.session.get('id_utilisateur'))

        messages.success(request, f"Le client {client.nom_client} {client.prenom_client} est modifié avec succès !")
        return redirect('client_li_contrat', pk)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def client_contrat(request):
    title = 'Clients | Contrats'
    active = 'active'
    font = 'custom-font'
    contrat = filter_by_user_role(request, Contrat.objects.all(), 'cp_commune')
    context = {
        'title_contrat': title,
        'active_contrat': active,
        'font_contrat': font,
        'contrat': contrat
    }
    return render(request, 'all_page/clients/content_client.html', context)


class ContratNew(SchemaAwareView):
    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def get(request):
        title = 'Clients | Contrats | Nouveau'
        active = 'active'
        font = 'custom-font'
        client = Client.objects.all().order_by('id_client')
        compteurs = Compteur.objects.exclude(contrats__isnull=False)
        provinces = Province.objects.all().order_by('province')

        context = {
            'title_new_contrat': title,
            'active_contrat': active,
            'font_client': font,
            'client': client,
            'compteurs': compteurs,
            'provinces': provinces,
        }
        return render(request, 'all_page/clients/content_client.html', context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
    def post(request):
        try:
            contrat = extract_contrat_data(request)
            client_id = request.POST['client_id']
            num_contrat = request.POST['num_contrat']
            date_debut = request.POST['date_debut']
            date_fin = request.POST['date_fin']
            num_compteur = request.POST['num_compteur']

            date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            num_contrat_exist = Contrat.objects.filter(num_contrat=num_contrat).exists()

            client = Client.objects.get(pk=client_id)
            historique = f'Creation de contrat pour le client ID {client.pk} {client.nom_client} {client.prenom_client}'

            cp_commune_tarif = Tarif.objects.filter(cp_commune_id=contrat['cp_commune'])

            # Pour verifier si le tarif pour ce commun qu'on a seleectionné est déjà definie
            if cp_commune_tarif.exists():
                # Pour verifier si le numéro de contrat est déjà était utilisé
                if not num_contrat_exist:
                    # Pour verifier si la date fin a un valeur
                    if date_fin:
                        # Conversion de la date
                        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                        if date_debut > date_fin:
                            messages.warning(request, f"Veuillez entré des dates correctes s'il vous plait !")
                            return redirect('client_new_contrat')
                        else:
                            Contrat.objects.create(
                                client_id=client_id,
                                adresse_contrat=contrat['adresse_contrat'],
                                cp_commune_id=contrat['cp_commune'],
                                compteur_id=contrat['compteur_id'],
                                pays_contrat=contrat['pays_contrat'],
                                num_contrat=num_contrat,
                                date_debut=date_debut,
                                date_fin=date_fin,
                                utilisateur_id=request.session.get('id_utilisateur')
                            )
                            messages.success(request, f'Contrat crée avec succès !')
                            return redirect('client_contrat')
                    else:
                        Contrat.objects.create(
                            client_id=client_id,
                            adresse_contrat=contrat['adresse_contrat'],
                            cp_commune_id=contrat['cp_commune'],
                            num_compteur_id=num_compteur,
                            pays_contrat=contrat['pays_contrat'],
                            num_contrat=num_contrat,
                            date_debut=date_debut,
                            utilisateur_id=request.session.get('id_utilisateur')
                        )
                        messages.success(request, f"Contrat crée avec succès !")
                    # Historique
                    enregistre_historique(historique, request.session.get('id_utilisateur'))
                    return redirect('client_contrat')
                else:
                    messages.warning(request, f"Le numéro de contrat est déjà utilisé dans un autre !")
                    return redirect('client_new_contrat')
            else:
                messages.warning(request, f"Veuillez ajouter de Tarif pour ce Commune s'il vous plait !")
                return redirect('client_new_contrat')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement d'un contrat ({e}) !")
            return redirect('client_new_contrat')


@role_requis('Administrateur')
@schema_use
def supp_contrat(request, pk):
    contrat = get_object_or_404(Contrat, pk=pk)
    num_contrat = contrat.num_contrat
    client_id = contrat.client.pk
    contrat.delete()
    historie = f"Le contrat numéro {num_contrat} a été supprimer"
    enregistre_historique(historie, request.session.get('id_utilisateur'))
    messages.success(request, f"Contrat numero {num_contrat} supprimer avec succès !")
    return redirect('client_detail', client_id)


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def export_clients(request):
    commune = request.GET.get('commune')

    clients = Client.objects.order_by('id_client').all()
    nom_fichier = f'clients({commune}).xlsx'
    if commune:
        clients = clients.filter(cp_commune_id=commune)

    champs = [
        'id_client',
        'nom_client',
        'prenom_client',
        'adresse_client',
        'cp_commune__region__region',
        'cp_commune__commune',
        'cp_commune_id',
        'pays_client',
        'tel1_client',
        'tel2_client',
        'email_client',
        'compte_actif',
        'type_client__designation_client'
    ]
    nom_colonnes = [
        'ID',
        'Nom',
        'Prénom',
        'Adresse',
        'Région',
        'Commune',
        'CP Commune',
        'Pays',
        'Téléphone 1',
        'Téléphone 2',
        'Mail',
        'Compte Actif',
        'Type'
    ]
    response = exporter_en_excel(clients, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout les clients"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def genere_pdf_contrat(request, pk):
    template_path = 'all_page/clients/clients_contrats/template_contrat.html'
    contrat = Contrat.objects.get(pk=pk)
    nom_fichier_prefix = f'Contrat_de_{contrat.client.nom_client}'
    message = f"Export de contrat numéro {pk}"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    context = {
        'instance': contrat,
    }
    return generate_pdf(request, context, template_path, nom_fichier_prefix)


def generate_pdf(request, context, template_path, nom_fichier_prefix):
    # Crée un buffer en mémoire pour stocker le PDF généré
    pdf_buffer = BytesIO()

    template = get_template(template_path)
    html = template.render(context)

    # Crée le PDF dans le buffer en mémoire
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)

    if pisa_status.err:
        return HttpResponse("Error in generating PDF", status=500)

    # Réinitialise le buffer pour lire les données PDF
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nom_fichier_prefix}.pdf"'

    return response


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def export_clients_pdf(request):
    # Récupérer le paramètre de filtre par commune
    cp_commune = request.GET.get('commune')
    
    # Récupérer les clients uniques avec leur dernière facture
    clients_data = []
    
    # Filtrer les clients par commune si spécifiée
    clients = Client.objects.all().order_by('num_client')
    if cp_commune:
        clients = clients.filter(cp_commune_id=cp_commune)
    
    # Récupérer la commune pour le nom du fichier
    nom_commune = ""
    if cp_commune:
        try:
            commune = Commune.objects.get(cp_commune=cp_commune)
            nom_commune = f"_{commune.commune}"
        except Commune.DoesNotExist:
            pass
    
    for client in clients:
        # Récupérer la dernière facture pour ce client
        derniere_facture = Facture.objects.filter(
            num_contrat__client=client
        ).order_by('-date_facture').first()
        
        if derniere_facture:
            clients_data.append({
                'client': client,
                'facture': derniere_facture,
                'releve': derniere_facture.relevecompteur
            })
    
    context = {
        'clients_data': clients_data,
        'date_export': datetime.now(),
    }
    
    template_path = 'all_page/clients/export_client_pdf.html'
    nom_fichier_prefix = f'Liste_des_clients{nom_commune}'
    
    # Enregistrement dans l'historique
    message = f"Export PDF de la liste des clients {f'de la commune {nom_commune}' if nom_commune else ''} avec leurs dernières factures"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    
    return generate_pdf(request, context, template_path, nom_fichier_prefix)
