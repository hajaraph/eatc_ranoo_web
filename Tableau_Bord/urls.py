from django.urls import path

from Tableau_Bord.views import tableau_bord, importe

urlpatterns = [
    path('', tableau_bord, name='tableau_bord'),
    path('import', importe, name='import')
]
