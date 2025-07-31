from datetime import datetime

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect

from Depense.models import Transactions, Categories
from Tenants.middleware import schema_use, SchemaAwareView


@schema_use
def depense(request):
    title_depense_list = "Dépenses"
    active_depense = "active"
    font_depense = "custom-font"

    now = datetime.now()
    mois_actuel = now.month

    transaction = Transactions.objects.all().order_by('pk')
    transactions_mois = transaction.filter(date_transaction__month=mois_actuel)

    total_depenses_mois = transactions_mois.aggregate(Sum('montant'))['montant__sum']
    nombre_transactions = transactions_mois.count()

    context = {
        'title_depense_list': title_depense_list,
        'active_depense': active_depense,
        'font_depense': font_depense,
        'transaction': transaction,
        'mois_actuel': now,
        'total_depenses_mois': total_depenses_mois,
        'nombre_transactions': nombre_transactions,
    }
    return render(request, 'all_page/depense/depense.html', context)


class DepenseNew(SchemaAwareView):
    template_name = 'all_page/depense/depense.html'

    @staticmethod
    def get_context_data(**kwargs):
        context = {
            'title_depense_new': "Dépense | Nouvelle Dépense",
            'active_depense': "active",
            'font_depense': 'custom-font',
            'categories': Categories.objects.all().order_by('pk')
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
                utilisateur_id=request.session.get('id_utilisateur')
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
