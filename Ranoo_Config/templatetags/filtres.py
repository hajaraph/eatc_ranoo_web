from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def format_number(value):
    if value is None:
        return ""
    try:
        float_val = float(value)
        if float_val.is_integer():
            return int(float_val)
        return float_val
    except (ValueError, TypeError):
        return value

@register.filter
def dict_values(dictionary):
    """Convertit un dictionnaire en liste de ses valeurs"""
    if not dictionary:
        return []
    return list(dictionary.values())

@register.filter
def sum_values(iterable):
    """Calcule la somme d'une liste de nombres"""
    if not iterable:
        return 0
    try:
        return sum(float(x) for x in iterable if x is not None)
    except (ValueError, TypeError):
        return 0

@register.filter
def sum_mois(clients, mois_index):
    """Calcule la somme des valeurs pour un mois spécifique dans une liste de clients"""
    if not clients:
        return 0
    
    total = 0
    for client in clients:
        mois_key = list(client['mois'].keys())[mois_index]
        total += client['mois'].get(mois_key, 0)
    return total

@register.filter
def sum_total(clients):
    """Calcule la somme totale de toutes les valeurs mensuelles pour chaque client"""
    if not clients:
        return []
    
    totals = []
    for client in clients:
        total = sum(float(v) for v in client['mois'].values() if v is not None)
        totals.append(total)
    return totals