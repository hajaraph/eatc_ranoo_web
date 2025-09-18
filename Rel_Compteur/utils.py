from datetime import datetime, date, timedelta
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import DatabaseError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from typing import Optional, Tuple, Any, Union

from django.utils import timezone
from num2words import num2words
from Facturation.models import Facture


def get_previous_month(input_date: Union[date, datetime]) -> date:
    if isinstance(input_date, datetime):
        input_date = input_date.date()
        
    if input_date.month == 1:
        return input_date.replace(year=input_date.year - 1, month=12)
    return input_date.replace(month=input_date.month - 1)


def get_month_range(year_month):
    """Retourne le premier et dernier jour d'un mois donné (format YYYY-MM)"""
    year, month = map(int, year_month.split('-'))
    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(seconds=1)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(seconds=1)
    return start, end


def get_default_month_range(now=None):
    """
    Retourne les dates de début et de fin par défaut pour le mois en cours.
    
    Args:
        now (datetime, optional): Date de référence. Si non fourni, utilise la date actuelle.
        
    Returns:
        tuple: (date_debut, date_fin) - Les dates de début et de fin du mois
    """
    if now is None:
        now = timezone.now()
        
    date_debut = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    date_fin = (date_debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)
    date_fin = date_fin.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return date_debut, date_fin


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


def filter_by_date_range(
    queryset: QuerySet,
    date_field: str,
    date_start: Optional[str],
    date_end: Optional[str],
    default_month: Optional[int] = None
) -> Tuple[QuerySet, Any, Any]:

    if date_start and date_end:
        try:
            # Convertir les chaînes de date en objets date
            date_debut = datetime.strptime(date_start, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_end, '%Y-%m-%d').date()
            
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
