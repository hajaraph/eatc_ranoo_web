# Application Mobile EATC Releveurs

## 📁 Structure du dossier

Ce dossier contient les fichiers APK de l'application mobile EATC Releveurs.

## 📥 Comment ajouter un nouveau fichier APK

1. **Construire l'APK** depuis le projet mobile (Flutter/React Native)
2. **Renommer le fichier** selon le format :
   ```
   EATC_Releveurs_v{VERSION}.apk
   ```
   Exemple : `EATC_Releveurs_v1.0.0.apk`

3. **Copier le fichier** dans ce dossier

4. **Mett à jour** la liste `MOBILE_VERSIONS` dans `Login/views.py` :

```python
MOBILE_VERSIONS = [
    {
        'version': '1.0.0',
        'date': datetime(2026, 3, 26),
        'filename': 'EATC_Releveurs_v1.0.0.apk',
        'size': '25 MB',
        'changelog': [
            'Nouvelle fonctionnalité 1',
            'Correction de bug 2',
        ],
        'current': True,
    },
    # Anciennes versions...
]
```

5. **Exécuter collectstatic** :
```bash
python manage.py collectstatic
```

## 📊 Versions

| Version | Date | Taille | Statut |
|---------|------|--------|--------|
| 1.0.0 | 26 Mars 2026 | 25 MB | Actuelle |

## 🔗 Accès

- **Page de téléchargement** : `https://app.eatc.me/mobile-app/`
- **Lien direct APK** : `https://app.eatc.me/static/login/apk/EATC_Releveurs_v1.0.0.apk`
