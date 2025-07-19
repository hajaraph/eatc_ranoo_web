from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from Acommune.models import Commune, Region, Province
from Login.views import authentification_requis, role_requis
from Tenants.middleware import schema_use


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def region(request):
    titre = 'Ranoo Config | Région'
    active = 'active'
    font = 'custom-font'
    commune = Commune.objects.all().order_by('region__province')
    context = {
        'titre_region': titre,
        'active_region': active,
        'font_rano': font,
        'communes': commune
    }
    return render(request, 'all_page/ranoo_config/content.html', context)


class CommuneNew(View):
    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def get(request):
        titre = 'Ranoo Config | Région | Nouveau Département'
        active = 'active'
        font = 'custom-font'
        province = Province.objects.all().order_by('province')
        regions = Region.objects.all().order_by('region')
        context = {
            'titre_departement': titre,
            'active_region': active,
            'font_rano': font,
            'regions': regions,
            'province': province,
        }
        return render(request, 'all_page/ranoo_config/content.html', context)

    @staticmethod
    @authentification_requis
    @role_requis('Administrateur', 'Gestionnaire')
    @schema_use
    def post(request):
        regions = request.POST['region']
        commune = request.POST['commune']
        cp_commune = request.POST['cp_commune']
        code = Commune.objects.filter(pk=cp_commune)
        if code.exists():
            code = Commune.objects.get(pk=cp_commune)
            messages.warning(request, f'Le code postal {code.cp_commune} est déjà utilisé !')
            return redirect('commune_new')
        else:
            Commune.objects.create(
                cp_commune=cp_commune,
                commune=commune,
                region_id=regions
            )
            messages.success(request, f'Enregistrer avec succès !')
            return redirect('region')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def supp_commune(request, pk):
    commune = Commune.objects.get(pk=pk)
    commune.delete()
    messages.success(request, 'Supprimer avec succès !')
    return redirect('region')


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
@schema_use
def commune_list(request, province, *args, **kwargs):
    # Récupérer les régions distinctes pour la province
    regions = Region.objects.filter(province__province=province).order_by('region').distinct('region').values('region')

    # Récupérer toutes les communes associées à cette province
    communes = Commune.objects.filter(region__province__province=province).order_by('commune').values('commune',
                                                                                                      'cp_commune',
                                                                                                      'region__region')

    return JsonResponse({
        'regions': list(regions),  # Liste des régions sans doublons
        'communes': list(communes)  # Liste des communes avec leur région associée
    })