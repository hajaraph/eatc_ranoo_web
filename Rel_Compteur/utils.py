from datetime import datetime
from django.db.models import QuerySet
from typing import Optional, Tuple, Any

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
