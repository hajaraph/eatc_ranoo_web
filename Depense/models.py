from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from Acommune.models import Commune
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
    cp_commune = models.ForeignKey(
        Commune, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True, 
        verbose_name='Commune'
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
            models.Index(fields=['cp_commune']),
        ]

    def __str__(self):
        return f"{self.libelle} - {self.montant} Ar ({self.date_transaction})"

    def save(self, *args, **kwargs):
        # Remplissage automatique de la commune à partir de l'utilisateur (si pas Admin)
        if not self.cp_commune and self.utilisateur:
            if self.utilisateur.role and self.utilisateur.role.role != 'Administrateur':
                self.cp_commune = self.utilisateur.cp_commune
            
        super().save(*args, **kwargs)
