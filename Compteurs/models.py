from django.db import models

from Tenants.models import Utilisateur
from Rel_Compteur.mixins import SyncMixin, SyncManager
from django.utils import timezone


def upload_to_compteur(instance, filename):
    return f'compteurs/{instance.num_compteur_id}/{filename}'


class CompteurPrincipale(models.Model):
    num_compteur_principale = models.CharField(max_length=255, primary_key=True, blank=False, verbose_name='Numéro')
    marque_compteur_principale = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marque')
    modele_compteur_principale = models.CharField(max_length=100, blank=True, null=True, verbose_name='Modèle')
    DN_compteur_principale = models.CharField(max_length=100, blank=True, null=True, verbose_name='DN')
    origin_compteur_principale = models.CharField(max_length=100, blank=True, null=True, verbose_name='Origine')

    class Meta:
        verbose_name = 'Compteur Principal'
        verbose_name_plural = 'Compteurs Principaux'

    def __str__(self):
        return f"CP-{self.num_compteur_principale}"

    def get_total_conso_sous_compteurs(self, date_releve=None):
        """Calcule la somme des consommations de tous les sous-compteurs pour une date donnée"""
        total = 0
        for compteur in self.compteurs.all():
            # Exclure les compteurs sans contrat
            if not compteur.contrats.exists():
                continue
            if date_releve:
                # Prendre le relevé le plus récent à la date ou avant la date spécifiée
                releve = compteur.relevecompteurs.filter(date_releve__lte=date_releve).order_by('-date_releve').first()
            else:
                releve = compteur.relevecompteurs.order_by('-date_releve').first()
            if releve and releve.conso:
                total += releve.conso
        return total

    def get_ecart_consommation(self, date_releve=None):
        """Calcule l'écart entre le compteur principal et la somme des sous-compteurs"""
        releve_principal = self.releves.filter(date_releve=date_releve).first() if date_releve else self.releves.order_by('-date_releve').first()
        if not releve_principal:
            return None
        total_sous_compteurs = self.get_total_conso_sous_compteurs(date_releve or releve_principal.date_releve)
        return releve_principal.conso - total_sous_compteurs


class ReleveCompteurPrincipale(models.Model):
    id_releve = models.BigAutoField(primary_key=True)
    date_releve = models.DateField(blank=True, null=True, verbose_name='Date du relevé')
    volume = models.IntegerField(blank=True, null=True, verbose_name='Volume (m³)')
    conso = models.IntegerField(blank=True, null=True, verbose_name='Consommation (m³)')
    image_compteur = models.ImageField(upload_to='compteurs_principaux/', blank=True, verbose_name='Photo')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=True, null=True)
    num_compteur_principale = models.ForeignKey(
        CompteurPrincipale, 
        blank=False, 
        related_name='releves', 
        on_delete=models.CASCADE,
        verbose_name='Compteur Principal'
    )

    class Meta:
        verbose_name = 'Relevé Compteur Principal'
        verbose_name_plural = 'Relevés Compteurs Principaux'
        ordering = ['-date_releve']

    def __str__(self):
        return f"Relevé {self.num_compteur_principale} - {self.date_releve}"


class Compteur(SyncMixin, models.Model):
    """
    Modèle représentant un compteur d'eau.
    
    Hérite de SyncMixin pour les champs de synchronisation:
    - sync_id: UUID unique pour l'identification cross-platform
    - version: Numéro de version pour la détection de conflits
    - created_at, updated_at: Horodatage de création/modification
    - is_deleted, deleted_at: Support du soft delete
    """
    num_compteur = models.CharField(max_length=255, primary_key=True, blank=False)
    marque_compteur = models.CharField(max_length=100, blank=True, null=True)
    modele_compteur = models.CharField(max_length=100, blank=True, null=True)
    DN_compteur = models.CharField(max_length=100, blank=True, null=True)
    origin_compteur = models.CharField(max_length=100, blank=True, null=True)
    num_compteur_principale = models.ForeignKey(CompteurPrincipale, blank=True, null=True, related_name='compteurs', on_delete=models.CASCADE)
    
    # Managers pour la synchronisation
    objects = SyncManager()  # Exclut automatiquement les éléments supprimés
    all_objects = models.Manager()  # Accès à tous les éléments, y compris supprimés


class ReleveCompteur(SyncMixin, models.Model):
    """
    Modèle représentant un relevé de compteur.
    
    Hérite de SyncMixin pour les champs de synchronisation:
    - sync_id: UUID unique pour l'identification cross-platform
    - version: Numéro de version pour la détection de conflits
    - created_at, updated_at: Horodatage de création/modification
    - is_deleted, deleted_at: Support du soft delete
    """
    
    # Choix pour le statut de validation
    STATUT_VALIDATION_CHOICES = [
        ('EN_ATTENTE', 'En attente de validation'),
        ('CONFIRME', 'Confirmé'),
        ('REJETE', 'Rejeté'),
    ]
    
    id_releve = models.BigAutoField(primary_key=True)
    date_releve = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    conso = models.IntegerField(blank=True, null=True)
    image_compteur = models.ImageField(upload_to=upload_to_compteur, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=True, null=True, related_name='releves_effectues', verbose_name='Agent')
    num_compteur = models.ForeignKey(Compteur, blank=False, related_name='relevecompteurs', on_delete=models.CASCADE)
    
    # Champs de validation
    statut_validation = models.CharField(
        max_length=15, 
        choices=STATUT_VALIDATION_CHOICES, 
        default='EN_ATTENTE',
        verbose_name='Statut de validation'
    )
    date_validation = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name='Date de validation'
    )
    valideur = models.ForeignKey(
        Utilisateur, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='releves_valides',
        verbose_name='Validé par'
    )
    motif_rejet = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Motif du rejet'
    )
    
    # Managers pour la synchronisation
    objects = SyncManager()  # Exclut automatiquement les éléments supprimés
    all_objects = models.Manager()  # Accès à tous les éléments, y compris supprimés


class AlerteConsommation(models.Model):
    """Modèle pour les alertes de perte/écart de consommation"""
    
    TYPE_ALERTE_CHOICES = [
        ('PERTE', 'Perte détectée'),
        ('ECART_ELEVE', 'Écart élevé'),
        ('ECART_CRITIQUE', 'Écart critique'),
    ]
    
    STATUT_CHOICES = [
        ('NON_LU', 'Non lu'),
        ('LU', 'Lu'),
        ('TRAITE', 'Traité'),
        ('IGNORE', 'Ignoré'),
    ]
    
    id_alerte = models.BigAutoField(primary_key=True)
    compteur_principal = models.ForeignKey(
        CompteurPrincipale, 
        on_delete=models.CASCADE, 
        related_name='alertes',
        verbose_name='Compteur Principal'
    )
    type_alerte = models.CharField(max_length=20, choices=TYPE_ALERTE_CHOICES, default='PERTE')
    message = models.TextField(verbose_name='Message')
    ecart_m3 = models.IntegerField(verbose_name='Écart (m³)')
    pourcentage_ecart = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Pourcentage d\'écart')
    conso_principal = models.IntegerField(verbose_name='Consommation Principal (m³)')
    conso_sous_compteurs = models.IntegerField(verbose_name='Consommation Sous-Compteurs (m³)')
    date_releve = models.DateField(verbose_name='Date du relevé concerné')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='NON_LU')
    utilisateur_traitement = models.ForeignKey(
        Utilisateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Traité par'
    )
    date_traitement = models.DateTimeField(null=True, blank=True, verbose_name='Date de traitement')
    commentaire = models.TextField(blank=True, null=True, verbose_name='Commentaire')
    
    class Meta:
        verbose_name = 'Alerte Consommation'
        verbose_name_plural = 'Alertes Consommation'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Alerte {self.type_alerte} - {self.compteur_principal} ({self.date_releve})"
    
    @classmethod
    def creer_alerte_si_necessaire(cls, compteur_principal, seuil_alerte=None, seuil_critique=None, verifier_doublon=True):
        """
        Crée une alerte si l'écart dépasse le seuil.
        Si aucun seuil n'est fourni, utilise les paramètres configurés en base.
        
        Détecte deux types d'anomalies :
        1. Perte d'eau : Principal > Sous-compteurs (fuite, compteur défectueux)
        2. Surconsommation anormale : Sous-compteurs > Principal (erreur de relevé, fraude)
        
        CRÉE TOUJOURS UNE NOUVELLE ALERTE pour assurer l'historique et la traçabilité.

        Args:
            compteur_principal: Le compteur principal à vérifier
            seuil_alerte: Pourcentage à partir duquel une alerte est créée (défaut: 5% ou valeur configurée)
            seuil_critique: Pourcentage à partir duquel l'alerte est critique (défaut: 10% ou valeur configurée)
            verifier_doublon: Si True, vérifie les doublons sur la même date de relevé (défaut: True)
        """
        # Récupérer les paramètres configurés si non fournis
        if seuil_alerte is None or seuil_critique is None:
            params = ParametreAlerte.get_parametres_actifs()
            seuil_alerte = params.seuil_alerte
            seuil_critique = params.seuil_critique

        ecart = compteur_principal.get_ecart_consommation()
        if ecart is None:
            return None

        dernier_releve = compteur_principal.releves.order_by('-date_releve').first()
        if not dernier_releve or not dernier_releve.conso:
            return None

        conso_principal = dernier_releve.conso
        total_sous_compteurs = compteur_principal.get_total_conso_sous_compteurs(dernier_releve.date_releve)

        if conso_principal == 0:
            return None

        pourcentage = abs(ecart) / conso_principal * 100

        # Vérifier les doublons uniquement si demandé (pour éviter spam lors de modifications mineures)
        if verifier_doublon:
            alerte_existante = cls.objects.filter(
                compteur_principal=compteur_principal,
                date_releve=dernier_releve.date_releve
            ).first()

            if alerte_existante:
                return alerte_existante

        # Créer l'alerte si le seuil est dépassé (en valeur absolue)
        if pourcentage >= seuil_alerte:
            # Déterminer le type d'anomalie
            if ecart > 0:
                # CAS 1 : Principal > Sous-compteurs (Perte d'eau)
                if pourcentage >= seuil_critique:
                    type_alerte = 'ECART_CRITIQUE'
                    message = f"ALERTE CRITIQUE : Écart de {ecart} m³ ({pourcentage:.1f}%) détecté sur le compteur {compteur_principal.num_compteur_principale}. Perte d'eau significative possible."
                else:
                    type_alerte = 'ECART_ELEVE'
                    message = f"Écart de {ecart} m³ ({pourcentage:.1f}%) détecté sur le compteur {compteur_principal.num_compteur_principale}. Perte d'eau à surveiller."
            else:
                # CAS 2 : Sous-compteurs > Principal (Anomalie inverse)
                if pourcentage >= seuil_critique:
                    type_alerte = 'ECART_CRITIQUE'
                    message = f"ALERTE CRITIQUE : Consommation des sous-compteurs ({total_sous_compteurs} m³) dépasse le compteur principal ({conso_principal} m³) de {abs(ecart)} m³ ({pourcentage:.1f}%). Erreur de relevé ou fraude possible."
                else:
                    type_alerte = 'ECART_ELEVE'
                    message = f"Anomalie : Consommation des sous-compteurs ({total_sous_compteurs} m³) dépasse le compteur principal ({conso_principal} m³) de {abs(ecart)} m³ ({pourcentage:.1f}%). Vérification recommandée."

            alerte = cls.objects.create(
                compteur_principal=compteur_principal,
                type_alerte=type_alerte,
                message=message,
                ecart_m3=ecart,
                pourcentage_ecart=pourcentage,
                conso_principal=conso_principal,
                conso_sous_compteurs=total_sous_compteurs,
                date_releve=dernier_releve.date_releve
            )
            return alerte

        return None


class ParametreAlerte(models.Model):
    """
    Paramètres configurables pour les alertes de consommation.
    Un seul enregistrement actif à la fois.
    """
    seuil_alerte = models.FloatField(
        default=5.0,
        verbose_name="Seuil d'alerte (%)",
        help_text="Pourcentage à partir duquel une alerte est créée"
    )
    seuil_critique = models.FloatField(
        default=10.0,
        verbose_name="Seuil critique (%)",
        help_text="Pourcentage à partir duquel l'alerte est critique"
    )
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    utilisateur_modification = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Modifié par"
    )
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Paramètre d'Alerte"
        verbose_name_plural = "Paramètres d'Alerte"

    def __str__(self):
        return f"Alerte: {self.seuil_alerte}% | Critique: {self.seuil_critique}%"

    def save(self, *args, **kwargs):
        """S'assurer qu'un seul enregistrement actif existe"""
        if self.actif:
            ParametreAlerte.objects.exclude(pk=self.pk).update(actif=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_parametres_actifs(cls):
        """Récupère les paramètres actifs ou crée les valeurs par défaut"""
        params = cls.objects.filter(actif=True).first()
        if not params:
            params = cls.objects.create()
        return params

