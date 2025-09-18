from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from Login.views import role_requis
from Rel_Compteur.utils import get_month_range, get_default_month_range
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
    page = request.GET.get('page', 1)

    # Récupérer et filtrer les recettes
    recettes_qs = Recette.objects.all().select_related('type_recette', 'facture').order_by('date_encaissement')

    date_debut = None
    date_fin = None
    try:
        # Dates par défaut (mois en cours)
        default_start, default_end = get_default_month_range(timezone.now())
        
        # Gestion des dates de début et fin
        if mois_debut:
            date_debut, _ = get_month_range(mois_debut)
        else:
            date_debut = default_start
            mois_debut = date_debut.strftime('%Y-%m')
            
        if mois_fin:
            _, date_fin = get_month_range(mois_fin)
        else:
            date_fin = default_end
            mois_fin = date_fin.strftime('%Y-%m')
            
        # Appliquer le filtre
        recettes_filtrees = recettes_qs.filter(date_encaissement__range=(date_debut, date_fin))
        
    except (ValueError, IndexError):
        recettes_filtrees = recettes_qs.filter(date_encaissement__range=(date_debut, date_fin))
        mois_debut = date_debut.strftime('%Y-%m')
        mois_fin = date_fin.strftime('%Y-%m')
    
    # Conserver les valeurs pour le formulaire
    datedeb = mois_debut
    datefin = mois_fin

    # Calculer le total des recettes et le nombre de recettes
    total_recettes_mois = recettes_filtrees.aggregate(total=Sum('montant'))['total'] or 0
    nombre_recettes = recettes_filtrees.count()

    # Pagination avec préservation des paramètres de date
    paginator = Paginator(recettes_filtrees, 10)

    try:
        recettes = paginator.page(page)
        # Ajouter les paramètres de date à chaque numéro de page
        if datedeb or datefin:
            recettes.paginator.url_template = '?page={0}&datedeb={1}&datefin={2}'.format(
                '{0}', datedeb, datefin
            )
    except PageNotAnInteger:
        recettes = paginator.page(1)
    except EmptyPage:
        recettes = paginator.page(paginator.num_pages)

    context = {
        'title_recette_list': title_recette_list,
        'active_recette': active_recette,
        'font_recette': font_recette,
        'datedeb': datedeb,  # Mois de début format YYYY-MM
        'datefin': datefin,  # Mois de fin format YYYY-MM
        'mois_actuel': timezone.now(),
        'total_recettes_mois': total_recettes_mois,
        'nombre_recettes': nombre_recettes,
        'recettes': recettes,
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
