from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib import messages

from Login.views import role_requis
from Rel_Compteur.utils import get_default_month_range, filter_by_month_range, filter_by_user_role, get_month_name_fr, generate_pdf_export
from Tenants.middleware import schema_use, SchemaAwareView
from Tenants.models import Utilisateur
from .models import Recette, TypeRecette
from Facturation.models import Facture

@schema_use
def recette(request):
    title_recette_list = "Recette"
    active_recette = "active"
    font_recette = "custom-font"

    # Récupération des paramètres de date (format YYYY-MM)
    mois_debut = request.GET.get('datedeb')
    mois_fin = request.GET.get('datefin')

    # Récupérer et filtrer les recettes
    recettes_qs = Recette.objects.all().select_related('type_recette', 'facture').order_by('date_encaissement')

    # Appliquer le filtre par rôle utilisateur
    recettes_qs = filter_by_user_role(request, recettes_qs, 'facture__num_contrat__cp_commune_id')

    # Utilisation de la fonction utilitaire
    recettes_filtrees, mois_debut, mois_fin = filter_by_month_range(
        queryset=recettes_qs,
        date_field='date_encaissement',
        date_start=mois_debut,
        date_end=mois_fin,
        default_month=timezone.now().month  # Optionnel: mois par défaut
    )

    # Si les dates sont None (cas où le mois par défaut est utilisé)
    if mois_debut is None or mois_fin is None:
        date_debut, date_fin = get_default_month_range()
        mois_debut = date_debut.strftime('%Y-%m')
        mois_fin = date_fin.strftime('%Y-%m')
    
    # Conserver les valeurs pour le formulaire
    datedeb = mois_debut
    datefin = mois_fin

    # Calculer le total des recettes et le nombre de recettes
    total_recettes_mois = recettes_filtrees.aggregate(total=Sum('montant'))['total'] or 0
    nombre_recettes = recettes_filtrees.count()

    context = {
        'title_recette_list': title_recette_list,
        'active_recette': active_recette,
        'font_recette': font_recette,
        'datedeb': datedeb,  # Mois de début format YYYY-MM
        'datefin': datefin,  # Mois de fin format YYYY-MM
        'mois_actuel': timezone.now(),
        'total_recettes_mois': total_recettes_mois,
        'nombre_recettes': nombre_recettes,
        'recettes': recettes_filtrees,
    }

    return render(request, 'all_page/recette/recette.html', context)


class RecetteCreateView(SchemaAwareView):
    template_name = 'all_page/recette/recette.html'

    @staticmethod
    def get_context_data(**kwargs) -> dict:
        context = {
            'title_recette_new': "Recette | Nouvelle Recette",
            'active_recette': 'active',
            'font_recette': 'custom-font',
            'types_recette': TypeRecette.objects.all().order_by('libelle')
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            date_encaissement_str = request.POST.get('date_encaissement')
            type_recette = request.POST.get('type_recette')
            montant_str = request.POST.get('montant')
            description = request.POST.get('description', '').strip()

            # Basic validations
            if not date_encaissement_str or not type_recette or not montant_str:
                raise ValueError("Veuillez remplir les champs obligatoires")

            date_encaissement = datetime.strptime(date_encaissement_str, '%Y-%m-%d').date()
            type_rec, _ = TypeRecette.objects.get_or_create(libelle=type_recette)
            montant = float(montant_str)
            if montant <= 0:
                raise ValueError("Le montant doit être supérieur à 0")

            Recette.objects.create(
                type_recette=type_rec,
                montant=montant,
                date_encaissement=date_encaissement,
                description=description,
                cree_par_id=request.session.get('id_utilisateur'),
            )
            messages.success(request, "Recette créée avec succès.")
            return redirect('recette_list')
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {e}")
            # Re-render form with context
            context = self.get_context_data()
            context['form_values'] = request.POST
            return render(request, self.template_name, context)


def enregistrer_recette_paiement(*, facture_id: int, montant, utilisateur_id: int, date_encaissement=None, description: str = "") -> None:

    montant_dec = Decimal(str(montant)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if montant_dec <= 0:
        raise ValueError("Le montant doit être supérieur à 0")

    date_enc = date_encaissement or timezone.now().date()

    facture = Facture.objects.get(pk=facture_id)
    utilisateur = Utilisateur.objects.get(pk=utilisateur_id)

    # Type de recette par défaut pour paiements facture
    type_rec, _ = TypeRecette.objects.get_or_create(
        libelle='Paiement facture',
        defaults={'description': "Encaissement automatique d'une facture"}
    )

    Recette.objects.create(
        type_recette=type_rec,
        montant=montant_dec,
        reference=None,  # auto-généré dans Recette.save() si None
        date_encaissement=date_enc,
        description=description or f"Encaissement de la facture {facture.num_facture}",
        facture=facture,
        cree_par=utilisateur,
    )


@role_requis('Administrateur')
@schema_use
def supprimer_recette(request, pk):
    try:
        recettes = Recette.objects.get(pk=pk)
        recettes.delete()
        messages.success(request, "La recette a été supprimée avec succès.")
    except Recette.DoesNotExist:
        messages.error(request, "La recette demandée n'existe pas.")
    return redirect('recette_list')

@schema_use
def export_recette(request):
    return generate_pdf_export(
        request=request,
        queryset=Recette.objects.all().select_related('type_recette', 'facture').order_by('date_encaissement'),
        date_field='date_encaissement',
        total_field='montant',
        template_path='all_page/recette/export_recette_pdf.html',
        filename_prefix='Recettes',
        title_key='periode_recette',
        item_name='recettes',
        filter_field='facture__num_contrat__cp_commune_id'
    )
