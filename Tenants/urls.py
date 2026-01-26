from django.urls import path
from Tenants.views import export_database

urlpatterns = [
    path('export-database', export_database, name='export_database'),
]
