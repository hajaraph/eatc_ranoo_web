import os
from django.conf import settings
from django.db import models
from django.utils import timezone


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
