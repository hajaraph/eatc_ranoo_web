from django.db import models
from django.db.models.functions import Now
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from Acommune.models import Commune
from Clients.models import Client
from Tenants.models import Utilisateur
from Rel_Compteur.mixins import SyncMixin, SyncManager
import uuid


def upload_to_mc(instance, filename):
    return f'mc/{instance.main_courante.pk}/{filename}'


class MainCourante(SyncMixin, models.Model):
    # SURCHARGE TEMPORAIRE pour la migration : on autorise les doublons et le null
    sync_id = models.UUIDField(default=uuid.uuid4, null=True)

    id_mc = models.BigAutoField(primary_key=True)
    date_mc = models.DateField(default=timezone.now, blank=False)
    type_anomalie = models.CharField(max_length=50, blank=False)
    longitude_mc = models.CharField(max_length=50, blank=True, null=True)
    latitude_mc = models.CharField(max_length=50, blank=True, null=True)
    description_mc = models.CharField(max_length=255, blank=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, null=True, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=False)

    objects = SyncManager()
    all_objects = models.Manager()

    def touch(self):
        """Met à jour updated_at pour signaler une modification (utile pour delta sync)."""
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])


class StatutMC(models.Model):
    id_statut = models.BigAutoField(primary_key=True)
    en_cours = models.BooleanField(default=False, blank=False)
    realise = models.BooleanField(default=False, blank=False)
    non_traite = models.BooleanField(default=True, blank=False)
    date_status = models.DateField(db_default=Now(), blank=True, null=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, related_name='statuts')


class PhotoMC(models.Model):
    id_photos = models.BigAutoField(primary_key=True)
    photo_anomalie = models.ImageField(upload_to=upload_to_mc, blank=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, blank=True, related_name='photomcs')


class SuivieMC(models.Model):
    id_suivie = models.BigAutoField(primary_key=True)
    date_suivie = models.DateTimeField(blank=False, null=False)
    commentaire_suivie = models.CharField(max_length=200, blank=False)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, blank=False, related_name='suiviemcs')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT)


# === SIGNAUX POUR LE DELTA SYNC ===
# Quand un statut, photo ou suivi change, on met à jour updated_at de MainCourante
# pour que le delta sync détecte le changement.

@receiver(post_save, sender=StatutMC)
def update_main_courante_on_statut_change(sender, instance, **kwargs):
    """Met à jour MainCourante.updated_at quand le statut change."""
    if instance.main_courante_id:
        MainCourante.all_objects.filter(pk=instance.main_courante_id).update(
            updated_at=timezone.now()
        )


@receiver(post_save, sender=SuivieMC)
def update_main_courante_on_suivie_change(sender, instance, **kwargs):
    """Met à jour MainCourante.updated_at quand un suivi est ajouté/modifié."""
    if instance.main_courante_id:
        MainCourante.all_objects.filter(pk=instance.main_courante_id).update(
            updated_at=timezone.now()
        )


@receiver(post_save, sender=PhotoMC)
@receiver(post_delete, sender=PhotoMC)
def update_main_courante_on_photo_change(sender, instance, **kwargs):
    """Met à jour MainCourante.updated_at quand une photo est ajoutée/modifiée/supprimée."""
    if instance.main_courante_id:
        MainCourante.all_objects.filter(pk=instance.main_courante_id).update(
            updated_at=timezone.now()
        )

