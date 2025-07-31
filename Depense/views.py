from django.shortcuts import render

from Depense.models import Transactions
from Tenants.middleware import schema_use


# Create your views here.

@schema_use
def depense(request):
    title_depense_list = "Dépenses"
    active_depense_list = "active"
    font_depense = "custom-font"

    transaction = Transactions.objects.all().order_by('pk')

    context = {
        'title_depense_list': title_depense_list,
        'active_depense_list': active_depense_list,
        'font_depense': font_depense,
        'transaction': transaction,
    }
    return render(request, 'all_page/depense/depense.html', context)
