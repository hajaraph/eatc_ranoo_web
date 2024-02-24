from django.db import models

from Login.models import Utilisateur


def upload_to_compteur(instance, filename):
    return f'compteurs/{instance.num_compteur_id}/{filename}'


class Compteur(models.Model):
    num_compteur = models.CharField(max_length=20, primary_key=True, blank=False)
    marque_compteur = models.CharField(max_length=30, blank=False)
    modele_compteur = models.CharField(max_length=30, blank=False)
    DN_compteur = models.CharField(max_length=5, blank=False)
    origin_compteur = models.CharField(max_length=20, blank=False)


class ReleveCompteur(models.Model):
    id_releve = models.BigAutoField(primary_key=True)
    date_releve = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    conso = models.IntegerField(blank=True, null=True)
    image_compteur = models.ImageField(upload_to=upload_to_compteur, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=True, null=True)
    num_compteur = models.ForeignKey(Compteur, blank=False, related_name='relevecompteurs', on_delete=models.CASCADE)

    # def save(self, *args, **kwargs):
    #     # Calcul de la consommation avant d'enregistrer
    #     releve_precedent = ReleveCompteur.objects.filter(
    #         num_compteur=self.num_compteur).latest('date_releve')
    #
    #     if releve_precedent:
    #         self.conso = self.volume - releve_precedent.volume
    #     else:
    #         # Si c'est le premier relevé, la consommation est égale au volume actuel
    #         self.conso = self.volume
    #
    #     super().save(*args, **kwargs)
