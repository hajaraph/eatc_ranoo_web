from django.db import models
from django.utils import timezone

from Acommune.models import Commune
from Clients.models import Contrat
from Compteurs.models import ReleveCompteur
from Tenants.models import Utilisateur


class Tarif(models.Model):
    id_tarif = models.BigAutoField(primary_key=True)
    prix_m3_bs = models.FloatField(blank=True, null=True)
    prix_m3_bp = models.FloatField(blank=True, null=True)
    prix_m3_k = models.FloatField(blank=True, null=True)
    tva = models.FloatField(blank=False)
    conso_tva_app = models.FloatField(blank=True, null=True)
    nb_jour_echeance_fct = models.IntegerField(blank=False)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE,
                                   blank=False, related_name='communes')


class Taxe(models.Model):
    id_taxe = models.BigAutoField(primary_key=True)
    nom_taxe = models.CharField(max_length=100, default='Taxe', null=False, blank=False)
    taux_taxe = models.FloatField(null=False, blank=False)
    tarif = models.ForeignKey(Tarif, on_delete=models.CASCADE, related_name='taxes', blank=False)


class Facture(models.Model):
    id_facture = models.BigAutoField(primary_key=True)
    num_facture = models.CharField(max_length=50, blank=False)
    date_facture_precedant = models.DateField(blank=True, null=True)
    date_facture = models.DateField(blank=False)
    montant_total_ttc = models.FloatField(null=True, blank=True)
    avoir_avant = models.FloatField(null=True, blank=True)
    avoir_utilise = models.FloatField(null=True, blank=True)
    avoir_nouveau = models.FloatField(null=True, blank=True)
    restant_precedant = models.FloatField(null=True, blank=True)
    restant_nouvel = models.FloatField(null=True, blank=True)
    statut = models.BooleanField(default=False)
    taxes_appliquees = models.JSONField(blank=True, null=True)
    date_echeance = models.DateField(blank=True, null=True)
    tva_appliquer = models.FloatField(blank=True, null=True)
    num_contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE, blank=False)
    relevecompteur = models.ForeignKey(ReleveCompteur, on_delete=models.CASCADE,
                                       related_name='factures', blank=False)


class MontantHT(models.Model):
    id_montant_ht = models.BigAutoField(primary_key=True)
    total_conso_ht = models.FloatField(blank=False)
    tarif = models.ForeignKey(Tarif, on_delete=models.CASCADE, blank=False)
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, blank=False)


class MontantTTC(models.Model):
    id_montant_ttc = models.BigAutoField(primary_key=True)
    total_conso_ttc = models.FloatField(blank=False)
    montant_ht = models.ForeignKey(MontantHT, on_delete=models.CASCADE, related_name='montantttc', null=False)


class Paiement(models.Model):
    id_paiement = models.BigAutoField(primary_key=True)
    montant_payer = models.FloatField(null=True, blank=True)
    date_paiement = models.DateField(default=timezone.now, blank=False)
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='paiements', blank=False)


class Avoir(models.Model):
    id_avoir = models.BigAutoField(primary_key=True)
    montant_avoir = models.FloatField(blank=False)
    date_avoir = models.DateField(default=timezone.now, blank=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=False)
    num_contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE,
                                    related_name='avoirs', blank=False)


class Restant(models.Model):
    id_restant = models.BigAutoField(primary_key=True)
    restant = models.FloatField(blank=False)
    date_restant = models.DateField(default=timezone.now, blank=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=True, null=True)
    num_contrat = models.ForeignKey(Contrat, on_delete=models.CASCADE,
                                    related_name='restants', blank=False)
