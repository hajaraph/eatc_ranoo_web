from django.db import models
from django.utils import timezone

import Clients.models
import Compteurs.models
import Login.models


class Tarif(models.Model):
    id_tarif = models.BigAutoField(primary_key=True)
    prix_m3 = models.FloatField(blank=False)
    tva = models.FloatField(blank=False)
    nb_jour_echeance_fct = models.IntegerField(blank=False)
    cp_commune = models.ForeignKey(Clients.models.Commune, on_delete=models.CASCADE,
                                   blank=False, related_name='communes')


class Taxe(models.Model):
    id_taxe = models.BigAutoField(primary_key=True)
    nom_taxe = models.CharField(max_length=100, default='Taxe', null=False, blank=False)
    taux_taxe = models.FloatField(max_length=100, null=False, blank=False)
    tarif = models.ForeignKey(Tarif, on_delete=models.CASCADE, blank=False)


class Facture(models.Model):
    id_facture = models.BigAutoField(primary_key=True)
    num_facture = models.CharField(max_length=50, blank=False)
    date_facture = models.DateField(blank=False)
    montant_total_ttc = models.FloatField(null=True, blank=True)
    avoir_avant = models.FloatField(null=True, blank=True)
    avoir_utilise = models.FloatField(null=True, blank=True)
    restant_precedant = models.FloatField(null=True, blank=True)
    restant_nouvel = models.FloatField(null=True, blank=True)
    statut = models.BooleanField(default=False)
    num_contrat = models.ForeignKey(Clients.models.Contrat, on_delete=models.CASCADE, blank=False)
    relevecompteur = models.ForeignKey(Compteurs.models.ReleveCompteur, on_delete=models.CASCADE,
                                       related_name='factures', blank=False)


class MontantHT(models.Model):
    id_montant_ht = models.BigAutoField(primary_key=True)
    total_conso_ht = models.FloatField(blank=False)
    total_taxe_co_ht = models.FloatField(blank=False)
    total_redevance_bs_ht = models.FloatField(blank=False)
    total_redevance_fr_ht = models.FloatField(blank=False)
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
    utilisateur = models.ForeignKey(Login.models.Utilisateur, on_delete=models.CASCADE, blank=False)
    num_contrat = models.ForeignKey(Clients.models.Contrat, on_delete=models.CASCADE,
                                    related_name='avoirs', blank=False)


class Restant(models.Model):
    id_restant = models.BigAutoField(primary_key=True)
    restant = models.FloatField(blank=False)
    date_restant = models.DateField(default=timezone.now, blank=False)
    num_contrat = models.ForeignKey(Clients.models.Contrat, on_delete=models.CASCADE,
                                    related_name='restants', blank=False)
