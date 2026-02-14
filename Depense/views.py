from datetime import datetime

from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect

from Acommune.models import Province
from Depense.models import Transactions, Categories
from Rel_Compteur.utils import filter_by_month_range, get_default_month_range, filter_by_user_role, generate_pdf_export
from Tenants.middleware import schema_use, SchemaAwareView


@schema_use
def depense(request):
    title_depense_list = "Dépenses"
    active_depense = "active"
    font_depense = "custom-font"

    datedeb_query = request.GET.get('datedeb')
    datefin_query = request.GET.get('datefin')
    commune_filtre = request.GET.get('commune')  # cp_commune

    now = datetime.now()
    mois_actuel = now.month

    # Récupérer et filtrer les transactions
    transactions_qs = Transactions.objects.all().order_by('date_transaction')

    # Appliquer le filtre par rôle utilisateur
    transactions_qs = filter_by_user_role(request, transactions_qs, 'cp_commune_id')

    # Filtrage par commune (cp_commune)
    if commune_filtre:
        transactions_qs = transactions_qs.filter(cp_commune_id=commune_filtre)

    transactions_mois, date_start, date_end = filter_by_month_range(
        queryset=transactions_qs,
        date_field='date_transaction',
        date_start=datedeb_query,
        date_end=datefin_query,
        default_month=mois_actuel
    )
    datedeb, datefin = get_default_month_range()
    datedeb = datedeb.strftime('%Y-%m')
    datefin = datefin.strftime('%Y-%m')

    # Calculer le total des dépenses et le nombre de transactions
    total_depenses_mois = transactions_mois.aggregate(Sum('montant'))['montant__sum'] or 0
    nombre_transactions = transactions_mois.count()

    context = {
        'title_depense_list': title_depense_list,
        'active_depense': active_depense,
        'font_depense': font_depense,
        'transaction': transactions_mois,
        'mois_actuel': now,
        'total_depenses_mois': total_depenses_mois,
        'nombre_transactions': nombre_transactions,
        'datedeb': datedeb,  # Pour préremplir les champs de date dans le formulaire
        'datefin': datefin,   # Pour préremplir les champs de date dans le formulaire
        'categories': Categories.objects.all().order_by('nom_categorie'), # Pour le calculateur
        'provinces': Province.objects.order_by('province').all(),
    }
    return render(request, 'all_page/depense/depense.html', context)


class DepenseNew(SchemaAwareView):
    template_name = 'all_page/depense/depense.html'

    @staticmethod
    def get_context_data(**kwargs) -> dict:
        context = {
            'title_depense_new': "Dépense | Nouvelle Dépense",
            'active_depense': "active",
            'font_depense': 'custom-font',
            'categories': Categories.objects.all().order_by('pk'),
            'provinces': Province.objects.order_by('province').all(),
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Get form data
        date_transaction = request.POST.get('date_transaction')
        libelle = request.POST.get('libelle', '').strip()
        montant = request.POST.get('montant')
        categorie_id = request.POST.get('categorie')
        numero_recu = request.POST.get('numero_recu', '').strip() or None
        cp_commune_id = request.POST.get('commune')
        
        # Fallback auto pour les non-admins si pas rempli
        if not cp_commune_id:
            user_id = request.session.get('id_utilisateur')
            if user_id:
                user = Utilisateur.objects.filter(pk=user_id).first()
                if user and user.role and user.role.role != 'Administrateur':
                    cp_commune_id = user.cp_commune_id

        # Basic validation
        errors = []
        if not date_transaction:
            errors.append("La date de la transaction est requise.")
        if not libelle:
            errors.append("Le libellé est requis.")
        if not montant or float(montant) <= 0:
            errors.append("Un montant valide est requis.")
        if not categorie_id:
            errors.append("Une catégorie doit être sélectionnée.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = self.get_context_data()
            return render(request, self.template_name, context)

        try:
            # Create and save the transaction
            transaction = Transactions(
                date_transaction=date_transaction,
                libelle=libelle,
                montant=montant,
                categorie_id=categorie_id,
                numero_recu=numero_recu,
                utilisateur_id=request.session.get('id_utilisateur'),
                cp_commune_id=cp_commune_id
            )
            transaction.save()

            messages.success(request, "La dépense a été enregistrée avec succès.")
            return redirect('depense')

        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de l'enregistrement : {str(e)}")
            context = self.get_context_data()
            return render(request, self.template_name, context)


@schema_use
def depense_suppression(request, pk):
    try:
        transaction = Transactions.objects.get(pk=pk)
        transaction.delete()
        messages.success(request, "La dépense a été supprimée avec succès.")
    except Transactions.DoesNotExist:
        messages.error(request, "La dépense demandée n'existe pas.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la suppression : {str(e)}")

    return redirect('depense')


@schema_use
def export_depense(request):
    return generate_pdf_export(
        request=request,
        queryset=Transactions.objects.all().select_related('categorie', 'utilisateur').order_by('date_transaction'),
        date_field='date_transaction',
        total_field='montant',
        template_path='all_page/depense/export_depense_pdf.html',
        filename_prefix='Depenses',
        title_key='periode_depense',
        item_name='transactions',
    )


@schema_use
def calculate_depense_total(request):
    """
    Pour calculer le total des dépenses selon critères (Date, Catégorie)
    """
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    categorie_id = request.GET.get('categorie_id')

    queryset = Transactions.objects.all()

    # Filtrer par rôle (Commune)
    queryset = filter_by_user_role(request, queryset, 'utilisateur__cp_commune_id')

    # Filtrer par date
    if date_debut:
        queryset = queryset.filter(date_transaction__gte=date_debut)
    if date_fin:
        queryset = queryset.filter(date_transaction__lte=date_fin)

    # Filtrer par catégorie
    if categorie_id:
        queryset = queryset.filter(categorie_id=categorie_id)

    # Calculer le total
    total = queryset.aggregate(Sum('montant'))['montant__sum'] or 0
    count = queryset.count()

    return JsonResponse({
        'total': total,
        'count': count,
        'formatted_total': f"{total:,.2f}".replace(",", " ").replace(".", ",") + " Ar"
    })


@schema_use
def categorie_liste(request):
    title_categorie_list = "Dépense | Liste Catégorie"
    active_categorie = "active"
    font_depense = "custom-font"

    categories = Categories.objects.all().order_by('id_category')

    context = {
        'title_categorie_list': title_categorie_list,
        'active_categorie': active_categorie,
        'font_depense': font_depense,
        'categories': categories
    }
    return render(request, 'all_page/depense/depense.html', context)


class CategorieNew(SchemaAwareView):
    template_name = 'all_page/depense/depense.html'

    @staticmethod
    def get_context_data(**kwargs) -> dict:
        context = {
            'title_categorie_new': "Dépense | Nouvelle Catégorie",
            'active_categorie': "active",
            'font_depense': 'custom-font',
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        id_category = request.POST.get('id_category', '').strip()
        nom_categorie = request.POST.get('nom_categorie', '').strip()

        if Categories.objects.filter(id_category=id_category).exists():
             messages.error(request, "Ce code catégorie existe déjà.")
        
        if Categories.objects.filter(nom_categorie=nom_categorie).exists():
             messages.error(request, "Ce nom de catégorie existe déjà.")

        try:
            category = Categories(
                id_category=id_category,
                nom_categorie=nom_categorie
            )
            category.save()
            messages.success(request, "La catégorie a été créée avec succès.")
            return redirect('categorie_liste')

        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
            context = self.get_context_data()
            return render(request, self.template_name, context)


@schema_use
def categorie_suppression(request, pk):
    try:
        category = Categories.objects.get(pk=pk)
        category.delete()
        messages.success(request, "La catégorie a été supprimée avec succès.")
    except Categories.DoesNotExist:
        messages.error(request, "La catégorie n'existe pas.")
    except Exception as e:
        # Probablement une ProtectedError si utilisée dans des transactions
        messages.error(request, f"Impossible de supprimer cette catégorie car elle est utilisée : {str(e)}")

    return redirect('categorie_liste')
