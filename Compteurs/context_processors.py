"""
Context processor pour les alertes/notifications
Passe les alertes non lues à toutes les pages
"""
from Compteurs.models import AlerteConsommation


def alertes_context(request):
    """Ajoute les alertes non lues au contexte de toutes les pages"""
    context = {
        'notifications': [],
        'notifications_count': 0
    }
    
    # Vérifier si l'utilisateur est connecté
    if not request.session.get('id_utilisateur'):
        return context
    
    # Vérifier le rôle (seuls Admin et Gestionnaire voient les alertes)
    role = request.session.get('role_utilisateur')
    if role not in ['Administrateur', 'Gestionnaire']:
        return context
    
    try:
        # Récupérer les alertes non lues
        alertes = AlerteConsommation.objects.filter(
            statut='NON_LU'
        ).order_by('-date_creation')[:10]
        
        # Transformer en format pour le template
        notifications = []
        for alerte in alertes:
            icone = 'exclamation-triangle' if alerte.type_alerte == 'ECART_CRITIQUE' else 'exclamation-circle'
            notifications.append({
                'id': alerte.id_alerte,
                'message': alerte.message,
                'date_creation': alerte.date_creation,
                'icone': icone,
                'lu': False,
                'type': alerte.type_alerte,
                'compteur': alerte.compteur_principal.num_compteur_principale,
                'ecart': alerte.ecart_m3,
                'pourcentage': alerte.pourcentage_ecart
            })
        
        context['notifications'] = notifications
        context['notifications_count'] = AlerteConsommation.objects.filter(statut='NON_LU').count()
        
    except Exception:
        pass
    
    return context
