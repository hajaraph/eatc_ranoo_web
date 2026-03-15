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
            icone = 'radiation' if alerte.type_alerte == 'ECART_CRITIQUE' else 'exclamation-triangle'
            
            # Créer un message court et clair pour la notification
            if alerte.type_alerte == 'ECART_CRITIQUE':
                titre_court = "ALERTE CRITIQUE"
            else:
                titre_court = "Écart détecté"
            
            # Déterminer le type d'anomalie
            if alerte.ecart_m3 > 0:
                type_anomalie = "Perte d'eau"
            else:
                type_anomalie = "Anomalie (sous-compteurs > principal)"
            
            message_court = f"{titre_court}\n{type_anomalie}: {abs(alerte.ecart_m3)} m³ ({alerte.pourcentage_ecart}%)"
            
            notifications.append({
                'id': alerte.id_alerte,
                'message': message_court,
                'message_complet': alerte.message,
                'date_creation': alerte.date_creation,
                'icone': icone,
                'lu': False,
                'type': alerte.type_alerte,
                'compteur': alerte.compteur_principal.num_compteur_principale,
                'ecart': alerte.ecart_m3,
                'pourcentage': alerte.pourcentage_ecart,
                'type_anomalie': type_anomalie
            })
        
        context['notifications'] = notifications
        context['notifications_count'] = AlerteConsommation.objects.filter(statut='NON_LU').count()
        
    except Exception:
        pass
    
    return context
