from django.contrib import admin
from django_tenants.utils import schema_context
from .models import Province, Region, Commune

class PublicSchemaOnlyAdminMixin:
    """
    Mixin to ensure that models are only accessed/modified in the public schema.
    """
    @schema_context('public')
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    @schema_context('public')
    def delete_model(self, request, obj):
        super().delete_model(request, obj)

    @schema_context('public')
    def get_queryset(self, request):
        return super().get_queryset(request)

    @schema_context('public')
    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)

@admin.register(Province)
class ProvinceAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('id_province', 'province')
    search_fields = ('province',)

@admin.register(Region)
class RegionAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('id_region', 'region', 'province')
    search_fields = ('region',)
    list_filter = ('province',)

@admin.register(Commune)
class CommuneAdmin(PublicSchemaOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('cp_commune', 'commune', 'region')
    search_fields = ('commune', 'cp_commune')
    list_filter = ('region__province', 'region')
