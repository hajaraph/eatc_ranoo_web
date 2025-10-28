from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from Acommune.models import Province
from Login.views import role_requis
from Rubrique.models import DebitEau, Marnage
from Tenants.middleware import  SchemaAwareView


class DebitList(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'
    
    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Rubrique | Débit'
        active = 'active'
        font = 'custom-font'
        debit_liste = DebitEau.objects.all()
        context = {
            'title_debit': title,
            'active_debit': active,
            'font_rubrique': font,
            'debit': debit_liste
        }
        return render(request, self.template_name, context)


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
            'font_rubrique': font,
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
            messages.error(request, f"Ce débit n'existe pas")
            return redirect('debit')

        provinces = Province.objects.all()

        context = {
            'title_debit_mod': title,
            'active_debit': active,
            'font_rubrique': font,
            'debit_mod': debit_mod,
            'provinces': provinces
        }
        return render(request, self.template_name, context)

    @role_requis('Administrateur')
    def post(self, request, pk):
        try:
            debit = DebitEau.objects.get(pk=pk)
            date_creation = request.POST.get('date_creation')
            debit_valeur = request.POST.get('debit')
            cp_commune = request.POST.get('commune')

            # Vérifier si un autre débit existe déjà pour cette date et cette commune
            if DebitEau.objects.filter(date_creation=date_creation, cp_commune_id=cp_commune).exclude(pk=pk).exists():
                messages.error(request, "Un débit existe déjà pour cette date et cette commune.")
                return redirect('debit_mod', pk=pk)

            debit.date_creation = date_creation
            debit.debit = debit_valeur
            debit.cp_commune_id = cp_commune
            debit.save()  # La date_modification sera mise à jour automatiquement grâce à la méthode save() du modèle
            
            messages.success(request, "Modification effectuée avec succès !")
            return redirect('debit')
            
        except DebitEau.DoesNotExist:
            messages.error(request, "Ce débit n'existe pas")
            return redirect('debit')
        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
            return redirect('debit_mod', pk=pk)


class DebitDelete(SchemaAwareView):

    @role_requis('Administrateur')
    def get(self, request, pk):
        try:
            debit = get_object_or_404(DebitEau, pk=pk)
            debit.delete()
            messages.success(request, "Le débit a été supprimé avec succès.")
        except DebitEau.DoesNotExist:
            messages.error(request, "Ce débit n'existe pas")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de la suppression: {str(e)}")
        
        return redirect('debit')


class MarnageList(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Rubrique | Marnage'
        active = 'active'
        font = 'custom-font'
        marnage_liste = Marnage.objects.all()
        context = {
            'title_marnage': title,
            'active_marnage': active,
            'font_rubrique': font,
            'marnage': marnage_liste
        }
        return render(request, self.template_name, context)


class MarnageNew(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'

    @role_requis('Administrateur', 'Gestionnaire')
    def get(self, request):
        title = 'Rubrique | Marnage | Nouveau'
        active = 'active'
        font = 'custom-font'
        provinces = Province.objects.all()
        context = {
            'title_marnage_new': title,
            'active_marnage': active,
            'font_rubrique': font,
            'provinces': provinces
        }
        return render(request, self.template_name, context)

    @role_requis('Administrateur', 'Gestionnaire')
    def post(self, request):
        date_creation = request.POST.get('date_creation')
        marnage_valeur = request.POST.get('marnage')
        cp_commune = request.POST.get('commune')

        # Vérifier si un marnage existe déjà pour cette date et cette commune
        if Marnage.objects.filter(date_creation=date_creation, cp_commune_id=cp_commune).exists():
            messages.error(request, "Un marnage existe déjà pour cette date et cette commune.")
            return redirect('marnage_new')

        Marnage.objects.create(
            date_creation=date_creation,
            marnage=marnage_valeur,
            cp_commune_id=cp_commune
        )
        messages.success(request, "Marnage enregistré avec succès !")
        return redirect('marnage')


class MarnageMod(SchemaAwareView):
    template_name = 'all_page/rubrique/rubrique.html'

    @role_requis('Administrateur')
    def get(self, request, pk):
        title = 'Rubrique | Marnage | Modification'
        active = 'active'
        font = 'custom-font'

        try:
            marnage_mod = get_object_or_404(Marnage, pk=pk)
        except Marnage.DoesNotExist:
            messages.error(request, "Ce marnage n'existe pas")
            return redirect('marnage')

        provinces = Province.objects.all()

        context = {
            'title_marnage_mod': title,
            'active_marnage': active,
            'font_rubrique': font,
            'marnage_mod': marnage_mod,
            'provinces': provinces
        }
        return render(request, self.template_name, context)

    @role_requis('Administrateur')
    def post(self, request, pk):
        try:
            marnage = Marnage.objects.get(pk=pk)
            date_creation = request.POST.get('date_creation')
            marnage_valeur = request.POST.get('marnage')
            cp_commune = request.POST.get('commune')

            # Vérifier si un autre marnage existe déjà pour cette date et cette commune
            if Marnage.objects.filter(date_creation=date_creation, cp_commune_id=cp_commune).exclude(pk=pk).exists():
                messages.error(request, "Un marnage existe déjà pour cette date et cette commune.")
                return redirect('marnage_mod', pk=pk)

            marnage.date_creation = date_creation
            marnage.marnage = marnage_valeur
            marnage.cp_commune_id = cp_commune
            marnage.save()

            messages.success(request, "Mise à jour du marnage effectuée avec succès !")
            return redirect('marnage')

        except Marnage.DoesNotExist:
            messages.error(request, "Ce marnage n'existe pas")
            return redirect('marnage')
        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
            return redirect('marnage_mod', pk=pk)


class MarnageDelete(SchemaAwareView):
    @role_requis('Administrateur')
    def get(self, request, pk):
        try:
            marnage = get_object_or_404(Marnage, pk=pk)
            marnage.delete()
            messages.success(request, "Le marnage a été supprimé avec succès.")
        except Marnage.DoesNotExist:
            messages.error(request, "Ce marnage n'existe pas")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de la suppression: {str(e)}")

        return redirect('marnage')
