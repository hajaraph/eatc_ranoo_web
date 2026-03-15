from datetime import datetime

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def sum_mois(clients, mois_index):
    total = 0
    for client in clients:
        mois_key = list(client['mois'].keys())[mois_index]
        total += client['mois'].get(mois_key, 0)
    return total

@register.filter
def sum_total(clients):
    total = 0
    for client in clients:
        total += sum(client['mois'].values())
    return total

@register.filter
def string_to_date(value, date_format="%d/%m/%Y %H:%M"):
    """
    Converts a date string from format 'YYYY-MM-DDTHH:MM' to a formatted date string.
    Example: '2025-10-29T11:50' -> '29/10/2025 11:50'
    """
    if not value or not isinstance(value, str):
        return value
    try:
        # datetime.fromisoformat handles 'YYYY-MM-DDTHH:MM' directly
        dt_object = datetime.fromisoformat(value)
        return dt_object.strftime(date_format)
    except ValueError:
        # If parsing fails for any reason, return the original value
        return value

@register.filter
def neg(value):
    """Retourne la valeur négative d'un nombre"""
    try:
        return -float(value)
    except (ValueError, TypeError):
        return 0
