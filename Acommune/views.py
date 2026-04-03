from django.http import JsonResponse
from Login.views import authentification_requis
from Acommune.models import Commune, Region


@authentification_requis
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