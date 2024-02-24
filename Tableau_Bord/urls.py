from django.urls import path

from Tableau_Bord.views import tableau_bord, export

urlpatterns = [
    path('', tableau_bord, name='tableau_bord'),
    path('export', export, name='export')
]
