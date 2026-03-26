import os
import hashlib
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class DownloadToken(models.Model):
    """
    Modèle pour gérer les tokens de téléchargement temporaires.
    Chaque token est valide pour une durée limitée (défaut: 24h).
    """
    
    id_token = models.AutoField(primary_key=True, verbose_name="ID Token")
    token = models.CharField(max_length=64, unique=True, verbose_name="Token")
    mobile_version = models.ForeignKey(
        'MobileVersion',
        on_delete=models.CASCADE,
        related_name='download_tokens',
        verbose_name="Version mobile"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    expires_at = models.DateTimeField(verbose_name="Date d'expiration")
    used = models.BooleanField(default=False, verbose_name="Utilisé")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'utilisation")
    download_count = models.IntegerField(default=0, verbose_name="Nombre de téléchargements")
    max_downloads = models.IntegerField(default=5, verbose_name="Max téléchargements")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    
    class Meta:
        verbose_name = "Token de Téléchargement"
        verbose_name_plural = "Tokens de Téléchargement"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token {self.token[:8]}... (expire: {self.expires_at})"
    
    def is_valid(self):
        """Vérifie si le token est encore valide"""
        now = timezone.now()
        return (
            not self.used and
            now < self.expires_at and
            self.download_count < self.max_downloads
        )
    
    def increment_download(self):
        """Incrémente le compteur de téléchargements"""
        self.download_count += 1
        if self.download_count >= self.max_downloads:
            self.used = True
            self.used_at = timezone.now()
        self.save(update_fields=['download_count', 'used', 'used_at'])
    
    @classmethod
    def create_token(cls, mobile_version, duration_hours=24, max_downloads=5, ip_address=None):
        """
        Crée un nouveau token de téléchargement.
        
        Args:
            mobile_version: Instance de MobileVersion
            duration_hours: Durée de validité en heures (défaut: 24)
            max_downloads: Nombre max de téléchargements autorisés
            ip_address: Adresse IP du demandeur
        
        Returns:
            Instance de DownloadToken
        """
        # Générer un token unique et sécurisé
        token_string = secrets.token_urlsafe(32)
        
        # Calculer la date d'expiration
        expires_at = timezone.now() + timedelta(hours=duration_hours)
        
        # Créer le token en base
        token = cls.objects.create(
            token=token_string,
            mobile_version=mobile_version,
            expires_at=expires_at,
            max_downloads=max_downloads,
            ip_address=ip_address,
        )
        
        return token
    
    @classmethod
    def get_valid_token(cls, token_string):
        """
        Récupère un token valide depuis sa chaîne.
        
        Args:
            token_string: La chaîne du token
        
        Returns:
            Instance de DownloadToken ou None
        """
        try:
            token = cls.objects.get(token=token_string)
            if token.is_valid():
                return token
            return None
        except cls.DoesNotExist:
            return None


class MobileVersion(models.Model):
    """
    Modèle pour gérer les versions de l'application mobile.
    Chaque version uploadée est enregistrée en base de données.
    """
    
    id_version = models.AutoField(primary_key=True, verbose_name="ID Version")
    version = models.CharField(max_length=20, unique=True, verbose_name="Version")
    filename = models.CharField(max_length=255, verbose_name="Nom du fichier")
    file = models.FileField(upload_to='login/apk/', verbose_name="Fichier APK")
    taille = models.CharField(max_length=20, verbose_name="Taille")
    changelog = models.TextField(blank=True, verbose_name="Notes de version")
    est_actuelle = models.BooleanField(default=False, verbose_name="Version actuelle")
    maj_forcee = models.BooleanField(default=False, verbose_name="Mise à jour forcée")
    telecharge_par = models.ForeignKey(
        'Tenants.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Téléchargé par"
    )
    telecharge_le = models.DateTimeField(auto_now_add=True, verbose_name="Date de téléchargement")
    nombre_telechargements = models.IntegerField(default=0, verbose_name="Nombre de téléchargements")
    statut = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('archivee', 'Archivée'),
            ('supprimee', 'Supprimée'),
        ],
        default='active',
        verbose_name="Statut"
    )
    
    class Meta:
        verbose_name = "Version Mobile"
        verbose_name_plural = "Versions Mobile"
        ordering = ['-telecharge_le']
    
    def __str__(self):
        return f"v{self.version}"
    
    def incrementer_telechargements(self):
        """Incrémente le compteur de téléchargements"""
        self.nombre_telechargements += 1
        self.save(update_fields=['nombre_telechargements'])
    
    def definir_comme_actuelle(self):
        """Définit cette version comme actuelle et désactive les autres"""
        if not self.est_actuelle:
            MobileVersion.objects.filter(est_actuelle=True).update(est_actuelle=False)
            self.est_actuelle = True
            self.statut = 'active'
            self.save(update_fields=['est_actuelle', 'statut'])
    
    @property
    def url_telechargement(self):
        """Retourne l'URL de téléchargement"""
        from django.conf import settings
        # Utiliser MEDIA_URL car le fichier est uploadé via FileField
        return f"{settings.MEDIA_URL}login/apk/{self.filename}"
    
    @property
    def taille_formatee(self):
        """Retourne la taille formatée"""
        return self.taille
    
    @classmethod
    def obtenir_version_actuelle(cls):
        """Retourne la version actuelle de l'application"""
        return cls.objects.filter(est_actuelle=True, statut='active').first()
    
    @classmethod
    def obtenir_historique(cls):
        """Retourne l'historique des versions (exclut la version actuelle)"""
        return cls.objects.filter(est_actuelle=False, statut='active').order_by('-telecharge_le')
