from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from Acommune.models import Province
from Login.views import role_requis
from Rubrique.models import DebitEau
from Tenants.middleware import schema_use, SchemaAwareView


@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def debit(request):
    title = 'Rubrique | Débit'
    active = 'active'
    font = 'custom-font'
    debit_liste = DebitEau.objects.all()
    context = {
        'title_debit': title,
        'active_debit': active,
        'font_debit': font,
        'debit': debit_liste
    }
    return render(request, 'all_page/rubrique/rubrique.html', context)


class DebitNew(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Rubrique | Débit | Nouveau'
        active = 'active'
        font = 'custom-font'
        pronvince = Province.objects.all()
        context = {
            'title_debit_new': title,
            'active_debit': active,
            'font_debit': font,
            'provinces': pronvince
        }
        return render(request, self.template_name, context)

    @role_requis('Administrateur', 'Gestionnaire')
    def post(self, request):
        date_creation = request.POST.get('date_creation')
        debit_valeur = request.POST.get('debit')
        cp_commune = request.POST.get('commune')

        # Vérifier si un débit existe déjà pour cette date et cette commune
        if DebitEau.objects.filter(date_creation=date_creation, cp_commune_id=cp_commune).exists():
            messages.error(request, "Un débit existe déjà pour cette date et cette commune.")
            return redirect('debit_new')

        DebitEau.objects.create(
            date_creation=date_creation,
            debit=debit_valeur,
            cp_commune_id=cp_commune
        )
        messages.success(request, "Enregistré avec succès !")
        return redirect('debit')


class DebitMod(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'

    @role_requis('Administrateur')
    def get(self, request, pk):
        title = 'Rubrique | Débit | Modification'
        active = 'active'
        font = 'custom-font'

        try:
            debit_mod = get_object_or_404(DebitEau, pk=pk)
        except DebitEau.DoesNotExist:
            messages.error(request, f"Ce débit n'exist pas")
            return redirect('debit')

        pronvince = Province.objects.all()

        context = {
            'title_debit_mod': title,
            'active_debit': active,
            'font_debit': font,
            'debit_mod': debit_mod,
            'provinces': pronvince
        }
        return render(request, self.template_name, context)

