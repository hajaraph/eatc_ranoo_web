from collections import defaultdict
from datetime import datetime, date, timedelta
from django.contrib import messages
from django.db import models
from django.db.models import OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from weasyprint import HTML

from Acommune.models import Province, Commune
from Compteurs.models import Compteur, ReleveCompteur
from Clients.models import Contrat
from Facturation.models import Facture
from Facturation.views import facture_creation
from Login.views import role_requis
from Parametre.views import enregistre_historique, exporter_en_excel
from Tenants.middleware import schema_use, SchemaAwareView
from Rel_Compteur.utils import get_month_name_fr


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
        compteurs = list(
            Compteur.objects.prefetch_related(
                models.Prefetch('contrats', queryset=Contrat.objects.select_related('client'))
            ).annotate(
                dernier_releve=Subquery(derniers_releves.values('date_releve')[:1])
            ).order_by('pk')
        )
    else:
        cp_commune = request.session.get('cp_commune')

        derniers_releves = ReleveCompteur.objects.filter(
            num_compteur_id=OuterRef('pk')
        ).order_by('-date_releve')

        compteurs = list(
            Compteur.objects.annotate(
                dernier_releve=Subquery(derniers_releves.values('date_releve')[:1])
            ).filter(contrats__cp_commune_id=cp_commune).order_by('num_compteur')
        )
    compteurs.sort(key=lambda x: int(x.num_compteur))

    provinces = Province.objects.all().order_by('province')

    context = {
        'title_liste': title,
        'header_text': header,
        'active_li_co': active,
        'font_compteur': font,
        'compteur': compteurs,
        'provinces': provinces,
    }
    return render(request, 'all_page/compteurs/compteurs.html', context)


class CompteurNew(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Compteurs | Nouveau'
        active = 'active'
        font = 'custom-font'
        context = {
            'title_new': title,
            'active_li_co': active,
            'font_compteur': font
        }
        return render(request, self.template_name, context)

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire')
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


class CompteurDetail(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def get(self, request, pk):
        try:
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
                'client': contrat.get().client if contrat.exists() else None,
                'client_active': contrat.get().client.compte_actif if contrat.exists() else None
            }
            return render(request, self.template_name, context)
        except Exception as e:
            messages.error(request, f"Une erreur est survenue sur le compteur : {e}")
            return redirect('compteur_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
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


class ReleveNew(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def get(self, request, num_compteur):
        try:
            compteur = Compteur.objects.get(pk=num_compteur)

            title = f'Compteur Numéro : {compteur.num_compteur} | Relevé | Nouveau'
            active = 'active'
            font = 'custom-font'
            context = {
                'title_releve_new': title,
                'active_releve_new': active,
                'font_compteur': font,
                'compteur': compteur,
            }
            return render(request, self.template_name, context)
            
        except Compteur.DoesNotExist:
            messages.error(request, "Le compteur spécifié n'existe pas.")
            return redirect('compteur_list')
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")
            return redirect('compteur_list')

    @staticmethod
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
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


class ReleveMod(SchemaAwareView):

    template_name = 'all_page/compteurs/compteurs.html'

    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
    def get(self, request, pk):
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
        return render(request, self.template_name, context)

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
    @role_requis('Administrateur', 'Gestionnaire', 'Releveur')
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


@role_requis('Administrateur', 'Gestionnaire', 'Releveur')
@schema_use
def del_releve(request, pk):
    releve = get_object_or_404(ReleveCompteur, pk=pk)
    releve.image_compteur.delete()
    releve.delete()
    messages.success(request, f"Relevé supprimé avec succès !")
    return redirect('compteur_detail', releve.num_compteur.pk)


@schema_use
def export_compteur(request):
    # Récupérer le paramètre de filtre par commune
    commune_id = request.GET.get('commune')
    
    # Construire la requête de base pour les contrats actifs avec leurs relations
    contrats_query = Contrat.objects.select_related(
        'client',
        'client__type_client',
        'num_compteur',
        'cp_commune'  # Ajout de la jointure avec la commune
    ).prefetch_related(
        'num_compteur__relevecompteurs'
    )
    
    # Appliquer le filtre par commune si spécifié
    if commune_id:
        contrats_query = contrats_query.filter(cp_commune_id=commune_id)
    
    # Exécuter la requête
    contrats = contrats_query.all()
    
    # Préparer les données pour le template
    data = []
    for contrat in contrats:
        compteur = contrat.num_compteur
        if not compteur:
            continue
            
        # Récupérer les relevés triés par date décroissante
        releves = list(compteur.relevecompteurs.all().order_by('-date_releve'))
        dernier_releve = releves[0] if releves else None
        avant_dernier_releve = releves[1] if len(releves) > 1 else None
        
        # Calculer la consommation
        conso = 0
        if dernier_releve and avant_dernier_releve:
            conso = dernier_releve.volume - avant_dernier_releve.volume
        elif dernier_releve:
            conso = dernier_releve.volume
            
        data.append({
            'num_client': contrat.client.num_client,
            'num': compteur.num_compteur,
            'nom_client': f"{contrat.client.nom_client} {contrat.client.prenom_client or ''}".strip(),
            'adresse': contrat.adresse_contrat,
            'ancien_releve': avant_dernier_releve.volume if avant_dernier_releve else 0,
            'conso': conso,
            'type_client': contrat.client.type_client.designation_client if contrat.client and contrat.client.type_client else ''
        })

    # Récupérer le nom de la commune pour le titre
    commune_nom = 'Toutes les communes'
    if commune_id:
        try:
            commune = Commune.objects.get(pk=commune_id)
            commune_nom = commune.commune
        except (Commune.DoesNotExist, Exception):
            pass
    
    # Préparer le contexte pour le template
    context = {
        'compteurs': data,
        'date_export': datetime.now(),
        'commune': commune_nom
    }
    
    # Rendre le template en chaîne HTML
    html_string = render_to_string(
        'all_page/compteurs/pdf/fiche_releve.html',
        context
    )
    
    # Créer une réponse HTTP avec le type MIME PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Fiche_de_releve_{commune_nom}({datetime.now()}).pdf"'
    
    # Générer le PDF
    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)
    
    # Enregistrer dans l'historique
    message = "Export PDF de la liste des compteurs"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    
    return response


def get_months_range(start_date, end_date):
    """Génère une liste de tuples (année, mois) entre deux dates"""
    months = []
    current = start_date.replace(day=1)
    end_date = end_date.replace(day=1)
    
    while current <= end_date:
        months.append((current.year, current.month))
        # Passer au mois suivant
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    return months

@schema_use
def export_recouvrement(request):
    # Récupérer les paramètres de requête
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    commune_id = request.GET.get('commune')
    
    # Définir les dates par défaut si non fournies (3 mois en arrière par défaut)
    today = date.today()
    if not date_debut:
        # Premier jour du mois il y a 3 mois
        if today.month > 3:
            date_debut = today.replace(month=today.month-3, day=1)
        else:
            date_debut = today.replace(year=today.year-1, month=12-(3-today.month), day=1)
    else:
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
    
    if not date_fin:
        date_fin = today  # Aujourd'hui par défaut
    else:
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
    
    # Générer la liste des mois dans l'intervalle
    months = get_months_range(date_debut, date_fin)
    
    # Ajuster la date de fin pour inclure toute la journée
    date_fin = date_fin.replace(day=1, month=date_fin.month % 12 + 1) - timedelta(days=1) if date_fin.day == 1 else date_fin
    
    # Préparer la requête de base pour les factures impayées
    factures_query = Facture.objects.filter(
        statut=False,
        date_facture__range=[date_debut, date_fin]
    )
    
    # Filtrer par commune si spécifiée
    if commune_id:
        factures_query = factures_query.filter(
            num_contrat__cp_commune_id=commune_id
        )
    
    # Exécuter la requête avec les jointures nécessaires
    factures_impayees = factures_query.select_related(
        'num_contrat__client',
        'num_contrat__num_compteur',
        'num_contrat__cp_commune'
    ).order_by('num_contrat__num_compteur')
    
    # Créer une structure pour stocker les données par client
    clients_data = defaultdict(dict)
    clients_info = {}
    
    # Remplir les données
    for facture in factures_impayees:
        client = facture.num_contrat.client
        month_key = facture.date_facture.strftime('%Y-%m')
        
        if client.id_client not in clients_info:
            clients_info[client.id_client] = {
                'nom': f"{client.nom_client} {client.prenom_client or ''}".strip(),
                'adresse': facture.num_contrat.adresse_contrat or '',
                'compteur': facture.num_contrat.num_compteur.num_compteur if facture.num_contrat.num_compteur else '',
                'commune': facture.num_contrat.cp_commune.commune if hasattr(facture.num_contrat.cp_commune, 'commune') else 'Non spécifiée'
            }
        
        if month_key not in clients_data[client.id_client]:
            clients_data[client.id_client][month_key] = 0
            
        clients_data[client.id_client][month_key] += float(facture.montant_total_ttc or 0)
    
    # Préparer les données pour le template
    data = []
    for client_id, montants in clients_data.items():
        client_row = {
            'id': client_id,
            'nom': clients_info[client_id]['nom'],
            'adresse': clients_info[client_id]['adresse'],
            'compteur': clients_info[client_id]['compteur'],
            'mois': {}
        }
        
        # Ajouter les montants par mois
        for year, month in months:
            month_key = f"{year:04d}-{month:02d}"  # Clé pour la recherche dans les montants
            display_month = get_month_name_fr(month)  # Format d'affichage : nom du mois
            client_row['mois'][display_month] = montants.get(month_key, 0)
        
        data.append(client_row)
    
    # Préparer les en-têtes de colonnes avec le nom du mois
    mois_headers = [get_month_name_fr(month) for year, month in months]
    
    # Récupérer le nom de la commune pour le titre
    commune_nom = 'Toutes les communes'
    if commune_id:
        try:
            commune = Commune.objects.get(pk=commune_id)
            commune_nom = commune.commune
        except (Commune.DoesNotExist, Exception):
            pass
    
    context = {
        'clients': data,
        'mois_headers': mois_headers,
        'date_export': datetime.now(),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'form_action': request.path,
        'commune': commune_nom
    }
    
    # Rendu du template
    html_string = render_to_string('all_page/compteurs/pdf/recouvrement.html', context)
    
    # Création du PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Recouvrement_{commune_nom}_{date_debut.strftime("%Y-%m-%d")}_au_{date_fin.strftime("%Y-%m-%d")}.pdf"'
    
    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)
    
    return response


@schema_use
def export_relever(request, num_compteur):
    # Récupérer le paramètre de filtre par commune
    commune_id = request.GET.get('commune')
    
    # Construire la requête de base pour les relevés
    releves_query = ReleveCompteur.objects.filter(num_compteur_id=num_compteur)
    
    # Filtrer par commune si spécifiée
    if commune_id:
        releves_query = releves_query.filter(
            num_compteur__contrats__cp_commune_id=commune_id
        ).distinct()
    
    # Récupérer les relevés
    relevecompteur = releves_query.all()
    
    # Nom du fichier d'export
    nom_fichier = f"Relever_de_{num_compteur}.xlsx"
    
    # Champs à exporter
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
