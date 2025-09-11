from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import DatabaseError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from typing import Optional, Tuple, Any
from Facturation.models import Facture

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
