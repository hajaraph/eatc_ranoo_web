from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from Tenants.models import Utilisateur


class Categories(models.Model):
    id_category = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name='ID Catégorie'
    )
    nom_categorie = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Nom de la catégorie'
    )

    class Meta:
        ordering = ['nom_categorie']

    def __str__(self):
        return self.nom_categorie


class Transactions(models.Model):
    id_transaction = models.BigAutoField(primary_key=True)
    date_transaction = models.DateField(
        verbose_name="Date de transaction",
        default=timezone.now
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name="Libellé"
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant",
        validators=[MinValueValidator(0.01)]
    )
    categorie = models.ForeignKey(
        Categories,
        on_delete=models.PROTECT,
        verbose_name="Catégorie",
        related_name="transactions"
    )
    numero_recu = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Numéro de reçu"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        verbose_name="Utilisateur",
        related_name="transactions"
    )

    class Meta:
        ordering = ['-date_transaction']
        indexes = [
            models.Index(fields=['date_transaction']),
            models.Index(fields=['categorie']),
        ]

    def __str__(self):
        return f"{self.libelle} - {self.montant} Ar ({self.date_transaction})"
