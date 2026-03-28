# APIs REST Tableau de Bord - Documentation

## Vue d'ensemble

Les APIs du tableau de bord sont maintenant organisées dans un dossier dédié `Tableau_Bord/api/` pour une meilleure maintenabilité.

---

## Structure du Dossier

```
Tableau_Bord/
├── api/
│   ├── __init__.py          # Export des vues
│   ├── views.py             # Vues API REST (DRF)
│   └── urls.py              # URLs des APIs
├── urls.py                  # URLs web existantes (JsonResponse)
├── urls_api_admin.py        # Fichier d'inclusion pour URLs admin
├── views.py                 # Vues web existantes + fonctions utilitaires
└── api_views.py             # (Supprimé - déplacé dans api/)
```

---

## Endpoints Disponibles

### Nouvelles APIs REST (pour Mobile)

| Endpoint | Méthode | Rôles | Format | Description |
|----------|---------|-------|--------|-------------|
| `/api/admin/dashboard/kpi/` | GET | Admin/Gest | DRF ApiResponse | KPI globaux |
| `/api/admin/dashboard/evo-conso/` | GET | Admin/Gest | DRF ApiResponse | Évolution consommation (6 mois) |
| `/api/admin/dashboard/factures-statut/` | GET | Admin/Gest | DRF ApiResponse | Statut factures (payées/impayées) |
| `/api/admin/dashboard/anomalies-statut/` | GET | Admin/Gest | DRF ApiResponse | Statut anomalies |

### Anciennes APIs (pour Web)

| Endpoint | Méthode | Rôles | Format | Description |
|----------|---------|-------|--------|-------------|
| `/tableau_bord/api/kpi-globaux/` | GET | Admin/Gest/Autre | JsonResponse | KPI globaux |
| `/tableau_bord/api/evo-conso-commune/` | GET | Admin/Gest/Autre | JsonResponse | Évolution conso par commune |
| `/tableau_bord/api/statut-factures/` | GET | Admin/Gest/Autre | JsonResponse | Statut factures |
| `/tableau_bord/api/statut-main-courante/` | GET | Admin/Gest/Autre | JsonResponse | Statut anomalies |
| ... (autres endpoints existants) | | | | |

---

## Différences entre Anciennes et Nouvelles APIs

| Aspect | Anciennes APIs (Web) | Nouvelles APIs (Mobile) |
|--------|---------------------|------------------------|
| **Format** | `JsonResponse` simple | `ApiResponse` standardisé |
| **Authentification** | Session Django (`@role_requis`) | JWT Token (`IsAdminOuGestionnaire`) |
| **Middleware** | `@schema_use` | `@schema_use_api` |
| **Permissions** | Basées sur session | Basées sur JWT claims |
| **Public cible** | Interface web | Application mobile |

---

## Exemple de Réponse

### KPI Globaux

**Requête** :
```bash
curl -X GET "http://localhost:8000/api/admin/dashboard/kpi/" \
  -H "Authorization: Bearer eyJ..."
```

**Réponse** :
```json
{
  "success": true,
  "timestamp": "2026-03-28T10:30:00Z",
  "data": {
    "chiffre_affaires": 15000000.50,
    "nombre_clients": 1250,
    "nombre_compteurs": 1180,
    "total_recettes": 12500000.00,
    "total_depenses": 8300000.00,
    "resultat_net": 4200000.00,
    "taux_recouvrement": 78.50,
    "nombre_factures_impayees": 342,
    "nombre_anomalies_en_cours": 15,
    "periode": {
      "debut": "2026-03-01",
      "fin": "2026-03-31"
    }
  }
}
```

---

## Fonctions Utilitaires Réutilisées

Les nouvelles APIs utilisent les fonctions existantes de `views.py` :

### `_get_filtered_queryset()`

```python
def _get_filtered_queryset(request, model, role_filter_path, commune_filter_path, date_filter_path, default_to_year=True):
    """
    Applique les filtres communs (rôle, commune, date) à un queryset.
    
    Args:
        request: Requête HTTP
        model: Modèle Django à filtrer
        role_filter_path: Chemin du champ pour le filtre par rôle
        commune_filter_path: Chemin du champ pour le filtre par commune
        date_filter_path: Chemin du champ pour le filtre par date
        default_to_year: Si True, filtre par année courante par défaut
    
    Returns:
        QuerySet filtré
    """
```

**Exemple d'utilisation** :
```python
# Filtrer les factures par rôle et commune
factures_query = _get_filtered_queryset(
    request,
    Facture,
    'num_contrat__cp_commune_id',  # Filtre par rôle
    'num_contrat__cp_commune',      # Filtre par commune
    'date_facture',                 # Champ de date
    default_to_year=False          # Pas de filtre année par défaut
)
```

---

## Permissions

Les APIs utilisent le système de permissions personnalisé :

```python
from Login.permissions import IsAdminOuGestionnaire

@api_view(['GET'])
@permission_classes([IsAdminOuGestionnaire])
@schema_use_api
def dashboard_kpi(request):
    # Seul Admin et Gestionnaire peuvent accéder
    ...
```

### Comportement par Rôle

- **Administrateur** : Accès à toutes les données (global)
- **Gestionnaire** : Données limitées à sa commune (`request.user.cp_commune_id`)

---

## Migration du Code

### Avant (dans `Login/api_admin/`)
```
Login/api_admin/
├── views.py
├── urls.py
└── serializers.py
```

### Après (dans `Tableau_Bord/api/`)
```
Tableau_Bord/api/
├── __init__.py
├── views.py      # Vues avec fonctions utilitaires réutilisées
└── urls.py       # URLs dédiées
```

### Fichiers d'Inclusion

**`Tableau_Bord/urls_api_admin.py`** :
```python
from django.urls import path, include

urlpatterns = [
    path('', include('Tableau_Bord.api.urls')),
]
```

**`Rel_Compteur/urls.py`** :
```python
path('api/', include([
    path('', include('Login.api_auth.urls')),
    path('', include('Compteurs.api_compteur.urls')),
    path('', include('Main_Courante.api_anomalie.urls')),
    path('admin/dashboard/', include('Tableau_Bord.urls_api_admin')),
]))
```

---

## Prochaines Étapes

### APIs à Créer (Par App)

Suivant le même principe, les futures APIs seront organisées par application :

- **Clients** : `Clients/api/urls.py` et `Clients/api/views.py`
- **Facturation** : `Facturation/api/urls.py` et `Facturation/api/views.py`
- **Compteurs** : Déjà existant (`Compteurs/api_compteur/`)
- **Main Courante** : Déjà existant (`Main_Courante/api_anomalie/`)

### Structure Recommandée

```
<App>/
├── api/
│   ├── __init__.py
│   ├── views.py      # Vues API REST
│   ├── urls.py       # URLs API
│   └── serializers.py # Serializers spécifiques
├── models.py
├── views.py          # Vues web existantes
└── urls.py           # URLs web existantes
```

---

## Notes Importantes

1. **Réutilisation du code** : Les fonctions utilitaires de `views.py` sont importées dans les APIs pour éviter la duplication

2. **Cohérence** : Toutes les nouvelles APIs utilisent `ApiResponse` pour un format standardisé

3. **Rétrocompatibilité** : Les anciennes APIs (JsonResponse) restent fonctionnelles pour le web

4. **Performance** : Les APIs utilisent `select_related()` et `prefetch_related()` pour optimiser les requêtes

---

## Auteurs
- Date : 28 Mars 2026
- Version : 1.0.0
