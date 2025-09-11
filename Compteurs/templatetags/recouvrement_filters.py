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
