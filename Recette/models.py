from datetime import datetime

from django.db import models
from django.db.models.functions import Now
from django.core.validators import MinValueValidator

from Facturation.models import Facture
from Tenants.models import Utilisateur


class TypeRecette(models.Model):
    id_type_recette = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.libelle


class Recette(models.Model):
    id_recette = models.AutoField(primary_key=True)
    type_recette = models.ForeignKey(TypeRecette, on_delete=models.PROTECT)
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    reference = models.CharField( max_length=100, blank=True, null=True)
    date_encaissement = models.DateField(db_default=Now())
    description = models.TextField(blank=True)
    facture = models.ForeignKey(Facture, on_delete=models.SET_NULL, null=True, blank=True)
    cree_par = models.ForeignKey(Utilisateur, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_encaissement', '-created_at']
        indexes = [
            models.Index(fields=['date_encaissement']),
            models.Index(fields=['type_recette']),
            models.Index(fields=['facture']),
        ]

    def __str__(self):
        return "Recette #{id} - {type} - {montant} MGA".format(
            id=self.id_recette,
            type=self.type_recette,
            montant=self.montant
        )

    @classmethod
    def generate_reference(cls):
        # Format : PAY + AAAA + MM + JJ + - + NNN
        today = datetime.now().strftime('%Y%m%d')
        prefix = f"PAY{today}-"

        # Trouver le dernier numéro pour aujourd'hui
        last_ref = cls.objects.filter(reference__startswith=prefix).order_by('reference').last()

        if last_ref:
            try:
                # Extraire le numéro et incrémenter
                last_num = int(last_ref.reference.split('-')[-1])
                new_num = f"{last_num + 1:03d}"
            except (ValueError, IndexError):
                new_num = "001"
        else:
            new_num = "001"

        return f"{prefix}{new_num}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()

        # Vérification supplémentaire du montant
        if self.montant <= 0:
            raise ValueError("Le montant doit être supérieur à zéro")
        super().save(*args, **kwargs)