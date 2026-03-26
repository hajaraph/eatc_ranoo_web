# API Mobile - Documentation

## 📋 Vue d'ensemble

Cette API permet la gestion des uploads d'APK et la vérification de version pour l'application mobile EATC Releveurs.

**Nouvelle fonctionnalité** : Les versions sont maintenant gérées en base de données avec le modèle `MobileVersion`.

---

## 🗄️ Modèle de Données

### Modèle `MobileVersion`

| Champ | Type | Description |
|-------|------|-------------|
| `id_version` | AutoField | Clé primaire |
| `version` | CharField | Version (ex: `1.0.0`) |
| `filename` | CharField | Nom du fichier |
| `file` | FileField | Fichier APK (MEDIA_ROOT/login/apk/) |
| `taille` | CharField | Taille (ex: `25 MB`) |
| `changelog` | TextField | Notes de version |
| `est_actuelle` | BooleanField | Version active |
| `maj_forcee` | BooleanField | Mise à jour obligatoire |
| `telecharge_par` | ForeignKey | Utilisateur ayant uploadé |
| `telecharge_le` | DateTimeField | Date d'upload |
| `nombre_telechargements` | IntegerField | Compteur de téléchargements |
| `statut` | CharField | `active`, `archivee`, `supprimee` |

### Gestion via Django Admin

Le modèle est accessible dans l'admin Django pour :
- ✅ Voir l'historique des versions
- ✅ Définir la version actuelle
- ✅ Activer/désactiver le force update
- ✅ Voir les statistiques de téléchargement

---

## 🔐 Authentification

### Token de Service

Pour utiliser l'API d'upload, vous devez générer un token de service :

```bash
# Dans le container Django
docker exec -it eatc_web-web-1 python manage.py create_service_token
```

**Options :**
```bash
# Nom personnalisé
python manage.py create_service_token --username ci_deploy

# Régénérer un token (révoquer l'ancien)
python manage.py create_service_token --revoke
```

### Ajouter le token dans GitHub Secrets

```
GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret

Name: DJANGO_SERVICE_TOKEN
Value: <token généré ci-dessus>
```

---

## 📤 API d'Upload d'APK

### Endpoint

```
POST /api/upload-apk/
```

### Authentification

```
Authorization: Token <your_service_token>
```

### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `apk_file` | File | Oui | Fichier APK à uploader |
| `version` | String | Oui | Version (ex: `1.0.0`) |
| `changelog` | String | Non | Description des changements |
| `size` | String | Non | Taille du fichier (ex: `25 MB`) |

### Exemple avec cURL

```bash
curl -X POST https://app.eatc.me/api/upload-apk/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: multipart/form-data" \
  -F "apk_file=@app-release.apk" \
  -F "version=1.0.0" \
  -F "changelog=Nouvelle version avec corrections de bugs" \
  -F "size=25 MB"
```

### Réponse Succès

```json
{
  "success": true,
  "timestamp": "2026-03-26T10:30:00+03:00",
  "data": {
    "filename": "EATC_Releveurs_v1.0.0.apk",
    "version": "1.0.0",
    "size": "25.00 MB",
    "upload_path": "/app/static/login/apk/EATC_Releveurs_v1.0.0.apk",
    "download_url": "/static/login/apk/EATC_Releveurs_v1.0.0.apk"
  },
  "message": "APK v1.0.0 uploadé avec succès"
}
```

### Réponse Erreur

```json
{
  "success": false,
  "timestamp": "2026-03-26T10:30:00+03:00",
  "error": {
    "code": "MISSING_FILE",
    "message": "Le fichier APK est requis."
  }
}
```

### Codes d'Erreur

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `MISSING_FILE` | 400 | Fichier APK non fourni |
| `MISSING_VERSION` | 400 | Version non fournie |
| `INVALID_FILE_TYPE` | 400 | Fichier non-APK |
| `ACCESS_DENIED` | 403 | Token invalide ou utilisateur non autorisé |
| `UPLOAD_ERROR` | 500 | Erreur serveur lors de l'upload |

---

## 📱 API de Version Mobile

### Endpoint

```
GET /api/version/
```

### Authentification

Aucune (publique)

### Exemple avec cURL

```bash
curl https://app.eatc.me/api/version/
```

### Réponse

```json
{
  "success": true,
  "timestamp": "2026-03-26T10:30:00+03:00",
  "data": {
    "version": "1.0.0",
    "date": "2026-03-26",
    "size": "25 MB",
    "changelog": [
      "Version initiale de l'application",
      "Relevés de compteurs d'eau",
      "Gestion des anomalies et incidents",
      "Synchronisation offline avec le serveur"
    ],
    "download_url": "/static/login/apk/EATC_Releveurs_v1.0.0.apk",
    "force_update": false
  }
}
```

---

## 🔧 GitHub Actions Workflow

### Exemple complet

```yaml
name: Build & Deploy Android APK

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build APK
        run: |
          # Flutter
          flutter build apk --release
          # ou React Native
          # npm run build:android

      - name: Get version from tag
        id: get_version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Upload APK to Django
        run: |
          curl -X POST https://app.eatc.me/api/upload-apk/ \
            -H "Authorization: Token ${{ secrets.DJANGO_SERVICE_TOKEN }}" \
            -F "apk_file=@build/app/outputs/flutter-apk/app-release.apk" \
            -F "version=${{ steps.get_version.outputs.VERSION }}" \
            -F "changelog=${{ github.event.head_commit.message }}"
```

---

## 📁 Structure des fichiers

```
Login/
├── api_auth/
│   ├── views.py          # upload_apk(), get_mobile_version()
│   └── urls.py           # /api/upload-apk/, /api/version/
├── management/
│   └── commands/
│       └── create_service_token.py  # python manage.py create_service_token
├── static/
│   └── login/
│       └── apk/          # APKs uploadés
└── views.py
    └── MOBILE_VERSIONS   # Liste des versions
```

---

## 🚀 Commandes utiles

```bash
# Générer un token
docker exec -it eatc_web-web-1 python manage.py create_service_token

# Régénérer un token
docker exec -it eatc_web-web-1 python manage.py create_service_token --revoke

# Tester l'API (remplacer TOKEN)
curl -H "Authorization: Token TOKEN" https://app.eatc.me/api/version/
```

---

## 🔒 Sécurité

- **Token Authentication** : Seul les utilisateurs avec token valide peuvent uploader
- **Utilisateurs de service** : Seuls les utilisateurs `service_*` peuvent uploader
- **Validation de fichier** : Seuls les fichiers `.apk` sont acceptés
- **HTTPS requis** : Toujours utiliser HTTPS en production

---

## 📝 Notes

- Les APKs sont stockés dans `STATIC_ROOT/login/apk/`
- Penser à exécuter `python manage.py collectstatic` après upload manuel
- Le nom de fichier est généré automatiquement : `EATC_Releveurs_v{VERSION}.apk`
