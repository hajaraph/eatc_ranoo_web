from datetime import datetime, date, timedelta
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import DatabaseError
from django.db.models import QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from typing import Optional, Tuple, Any, Union

from django.utils import timezone
from num2words import num2words
from Facturation.models import Facture
from django.template.loader import render_to_string
from weasyprint import HTML

def filter_by_client_number(
    queryset: QuerySet,
    client_field: str = 'num_contrat__client__num_client',
    num_client_deb: Optional[str] = None,
    num_client_fin: Optional[str] = None
) -> QuerySet:
    """
    Filtre un queryset par plage de numéros de client.
    
    Args:
        queryset: Le queryset à filtrer
        client_field: Le champ du modèle contenant le numéro de client
        num_client_deb: Numéro de client de départ (inclus)
        num_client_fin: Numéro de client de fin (inclus)
        
    Returns:
        QuerySet: Le queryset filtré
    """
    if num_client_deb:
        queryset = queryset.filter(**{f"{client_field}__gte": num_client_deb})
        if num_client_fin:
            queryset = queryset.filter(**{f"{client_field}__lte": num_client_fin})
    return queryset


def get_previous_month(input_date: Union[date, datetime]) -> date:
    """
    Retourne le premier jour du mois précédent pour éviter les problèmes de jours invalides.
    Par exemple, le mois précédent de 2025-03-31 sera 2025-02-01
    """
    if isinstance(input_date, datetime):
        input_date = input_date.date()
    
    # On retourne toujours le premier jour du mois précédent pour éviter les problèmes de jours
    if input_date.month == 1:
        return date(input_date.year - 1, 12, 1)
    return date(input_date.year, input_date.month - 1, 1)


def get_month_range(year_month):
    """Retourne le premier et dernier jour d'un mois donné (format YYYY-MM)"""
    year, month = map(int, year_month.split('-'))
    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(seconds=1)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(seconds=1)
    return start, end


def get_default_month_range():
    now = timezone.now()

    date_debut = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    date_fin = (date_debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)
    date_fin = date_fin.replace(hour=23, minute=59, second=59, microsecond=999999)

    return date_debut, date_fin


def get_3_months_range(start_date, end_date):
    """Génère une liste de tuples (année, mois) entre deux dates, avec un décalage d'un mois en arrière.

    Args:
        start_date: Date de début (objet date)
        end_date: Date de fin (objet date)

    Returns:
        Liste de tuples (année, mois) pour chaque mois dans l'intervalle
    """
    months = []
    current = start_date.replace(day=1)
    end_date = end_date.replace(day=1)

    while current <= end_date:
        # Obtenir le mois précédent pour l'affichage
        prev_month = get_previous_month(current)
        months.append((prev_month.year, prev_month.month))

        # Passer au mois suivant
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return months


def get_month_name_fr(month_num) -> str:
    month_names = {
        1: 'Janvier',
        2: 'Février',
        3: 'Mars',
        4: 'Avril',
        5: 'Mai',
        6: 'Juin',
        7: 'Juillet',
        8: 'Août',
        9: 'Septembre',
        10: 'Octobre',
        11: 'Novembre',
        12: 'Décembre'
    }
    return month_names.get(month_num, '')


def prepare_facture_context(request: HttpRequest, facture: Facture) -> tuple[None, HttpResponse] | tuple[Any, None]:

    from Facturation.views import (facture_context_pdf, get_prix_m3_client,
                                   get_derniers_montants_impayees, calculer_total_net_a_payer)
    from Tenants.models import Entreprise

    # Préparer le contexte de base
    context = facture_context_pdf(request, facture)
    if isinstance(context, HttpResponse):
        return None, context

    # Ajouter les informations spécifiques à la facture
    context['prix_m3'] = get_prix_m3_client(facture)

    # Gestion des impayés
    montants_impayees = get_derniers_montants_impayees(
        facture.num_contrat_id,
        facture.date_facture
    )
    context['montants_impayees_precedents'] = montants_impayees

    # Calculer le total net à payer
    total_net_a_payer = calculer_total_net_a_payer(
        facture.montant_total_ttc,
        montants_impayees
    )
    context['total_net_a_payer'] = total_net_a_payer

    from Facturation.views import is_eatc_schema
    # Gestion spécifique au schéma non-EATC
    if not is_eatc_schema(request):
        try:
            id_entreprise = request.session.get('entreprise')
            if id_entreprise:
                entreprise = Entreprise.objects.get(pk=id_entreprise)
                context.update({
                    'nif': f"{entreprise.nif}" if entreprise.nif else '-',
                    'stat': f"{entreprise.stat}" if hasattr(entreprise, 'stat') and entreprise.stat else '-',
                    'num_mvola': f"{entreprise.numero_mvola}" if hasattr(entreprise, 'numero_mvola') and entreprise.numero_mvola else '-',
                    'nom_mvola': f"{entreprise.nom_mvola}" if hasattr(entreprise, 'nom_mvola') and entreprise.nom_mvola else '-',
                })

                # Encodage des images de l'entreprise si nécessaire
                if hasattr(entreprise, 'logo_entreprise') and entreprise.logo_entreprise:
                    import base64
                    with open(entreprise.logo_entreprise.path, 'rb') as img_file:
                        context['logo_entreprise'] = base64.b64encode(img_file.read()).decode('utf-8')

                if hasattr(entreprise, 'signature_entreprise') and entreprise.signature_entreprise:
                    import base64
                    with open(entreprise.signature_entreprise.path, 'rb') as img_file:
                        context['signature_entreprise'] = base64.b64encode(img_file.read()).decode('utf-8')

        except (ObjectDoesNotExist, PermissionDenied, DatabaseError):
            # Log l'erreur si nécessaire
            pass

    return context, None


def filter_by_month_range(
    queryset: QuerySet,
    date_field: str,
    date_start: Optional[str],
    date_end: Optional[str],
    default_month: Optional[int] = None
) -> Tuple[QuerySet, Any, Any]:

    if date_start and date_end:
        try:
            # Convertir les chaînes de date en objets date
            date_debut, _ = get_month_range(date_start)
            _, date_fin = get_month_range(date_end)

            # Créer le filtre dynamique
            filter_kwargs = {f"{date_field}__range": [date_debut, date_fin]}
            return (
                queryset.filter(**filter_kwargs),
                date_start,
                date_end
            )
        except ValueError:
            pass

    # Si on arrive ici, soit les dates sont invalides, soit elles ne sont pas fournies
    if default_month is not None:
        filter_kwargs = {f"{date_field}__month": default_month}
        return queryset.filter(**filter_kwargs), None, None

    return queryset, None, None


def montant_en_lettres(montant) -> str:
    try:
        nombre = float(montant)
        lettre = num2words(nombre, lang='fr')
        return lettre[0].upper() + lettre[1:]
    except (ValueError, TypeError, AttributeError):
        return "Nombre invalide"


def filter_by_user_role(request, queryset, filter_field) -> QuerySet:
    """
    Filtre un queryset en fonction du rôle de l'utilisateur.

    Args:
        request: La requête HTTP
        queryset: Le queryset à filtrer
        filter_field: Le champ à utiliser pour le filtrage (par défaut: 'contrats__cp_commune_id')

    Returns:
        QuerySet: Le queryset filtré selon le rôle de l'utilisateur
    """
    role = request.session.get('role_utilisateur')

    if role in ['Releveur', 'Gestionnaire']:
        cp_commune = request.session.get('cp_commune')
        return queryset.filter(**{filter_field: cp_commune})

    return queryset

def generate_pdf_export(
    request: HttpRequest,
    queryset: QuerySet,
    date_field: str,
    total_field: str,
    template_path: str,
    filename_prefix: str,
    title_key: str,
    item_name: str,
    filter_field: str
) -> HttpResponse:
    """
    Génère un export PDF générique pour les recettes et les dépenses.

    Args:
        request: L'objet HttpRequest.
        queryset: Le QuerySet de base à exporter.
        date_field: Le nom du champ de date dans le modèle (ex: 'date_encaissement').
        total_field: Le nom du champ à sommer pour le total (ex: 'montant').
        template_path: Le chemin vers le template HTML pour le PDF.
        filename_prefix: Le préfixe du nom de fichier pour le PDF exporté (ex: 'Recettes').
        title_key: La clé du contexte pour le titre (ex: 'periode_recette').
        item_name: Le nom des éléments (ex: 'recettes' ou 'transactions').
        filter_field: Le champ à utiliser pour le filtrage par rôle (ex: 'facture__num_contrat__cp_commune_id').

    Returns:
        HttpResponse: La réponse HTTP contenant le PDF.
    """
    from Acommune.models import Commune

    mois_debut_str = request.GET.get('datedeb')
    mois_fin_str = request.GET.get('datefin')
    commune_id = request.GET.get('commune')

    # Appliquer le filtre par rôle utilisateur
    filtered_queryset = filter_by_user_role(request, queryset, filter_field)

    # Filtrer par commune si spécifiée
    if commune_id:
        filtered_queryset = filtered_queryset.filter(**{filter_field: commune_id})

    # Utilisation de la fonction utilitaire pour filtrer par mois
    filtered_queryset, mois_debut_obj, mois_fin_obj = filter_by_month_range(
        queryset=filtered_queryset,
        date_field=date_field,
        date_start=mois_debut_str,
        date_end=mois_fin_str,
        default_month=datetime.now().month
    )

    # Calculer le total et le nombre d'éléments
    total_sum = filtered_queryset.aggregate(total=Sum(total_field))['total'] or 0
    item_count = filtered_queryset.count()

    # Récupérer le nom de la commune sélectionnée
    commune_nom = None
    if commune_id:
        commune = Commune.objects.filter(pk=commune_id).first()
        if commune:
            commune_nom = commune.commune

    if mois_debut_str and mois_fin_str:
        start_date = datetime.strptime(mois_debut_str, '%Y-%m')
        end_date = datetime.strptime(mois_fin_str, '%Y-%m')

        if start_date.year == end_date.year and start_date.month == end_date.month:
            periode_str = f"du mois de {get_month_name_fr(start_date.month)} {start_date.year}"
        elif start_date.year == end_date.year:
            periode_str = f"des mois de {get_month_name_fr(start_date.month)} à {get_month_name_fr(end_date.month)} {start_date.year}"
        else:
            periode_str = f"des mois de {get_month_name_fr(start_date.month)} {start_date.year} à {get_month_name_fr(end_date.month)} {end_date.year}"
    else:
        current_month = datetime.now()
        periode_str = f"du mois de {get_month_name_fr(current_month.month)} {current_month.year}"

    context = {
        item_name: filtered_queryset,
        'date_export': datetime.now(),
        f'total_{item_name}': total_sum,
        f'nombre_{item_name}': item_count,
        title_key: periode_str,
        'commune_nom': commune_nom,
    }

    html_string = render_to_string(template_path, context)

    response = HttpResponse(content_type='application/pdf')
    if commune_nom:
        commune_safe = commune_nom.replace(' ', '_').replace('/', '_')
        response['Content-Disposition'] = f'filename="{filename_prefix}_{commune_safe}_{datetime.now().strftime("%Y-%m-%d")}.pdf"'
    else:
        response['Content-Disposition'] = f'filename="{filename_prefix}_{datetime.now().strftime("%Y-%m-%d")}.pdf"'

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)

    return response
