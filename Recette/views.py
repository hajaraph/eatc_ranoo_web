from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum
from django.shortcuts import redirect
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP

from Login.views import role_requis
from Tenants.middleware import schema_use, SchemaAwareView
from Recette.models import Recette, TypeRecette
from Facturation.models import Facture
from Tenants.models import Utilisateur

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@schema_use
def recette(request):
    title_recette_list = "Recette"
    active_recette = "active"
    font_recette = "custom-font"

    # Dates de filtre : du 1er jour du mois courant à aujourd'hui si non fournis
    today = timezone.now().date()
    first_day = today.replace(day=1)

    datedeb_str = request.GET.get('datedeb')
    datefin_str = request.GET.get('datefin')
    page = request.GET.get('page', 1)

    try:
        datedeb = datetime.strptime(datedeb_str, '%Y-%m-%d').date() if datedeb_str else first_day
    except ValueError:
        datedeb = first_day
    try:
        datefin = datetime.strptime(datefin_str, '%Y-%m-%d').date() if datefin_str else today
    except ValueError:
        datefin = today

    # Liste et statistiques des recettes sur la période
    recettes_qs = Recette.objects.filter(date_encaissement__range=(datedeb, datefin)).select_related('type_recette', 'facture')
    total_recettes_mois = recettes_qs.aggregate(total=Sum('montant'))['total'] or 0
    nombre_recettes = recettes_qs.count()

    # Pagination
    paginator = Paginator(recettes_qs, 10)

    try:
        recettes = paginator.page(page)
    except PageNotAnInteger:
        recettes = paginator.page(1)
    except EmptyPage:
        recettes = paginator.page(paginator.num_pages)

    context = {
        'title_recette_list': title_recette_list,
        'active_recette': active_recette,
        'font_recette': font_recette,
        'datedeb': datedeb,
        'datefin': datefin,
        'mois_actuel': today,
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
