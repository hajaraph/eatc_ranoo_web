from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import schema_context
from django.db import connection

from Tenants.models import Entreprise, Domain, Role, Utilisateur


class PublicSchemaOnlyAdminMixin:
    @schema_context('public')
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    @schema_context('public')
    def delete_model(self, request, obj):
        schema_name = obj.schema_name
        # Suppression de l'entreprise d'abord
        super().delete_model(request, obj)
        # Suppression du schéma PostgreSQL
        with connection.cursor() as cursor:
            # On s'assure que le schéma n'est pas public
            if schema_name != 'public':
                cursor.execute(f'DROP SCHEMA IF EXISTS {schema_name} CASCADE')

    @schema_context('public')
    def get_queryset(self, request):
        return super().get_queryset(request)

    @schema_context('public')
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self.delete_model(request, obj)


@admin.register(Entreprise)
class EntrepriseAdmin(PublicSchemaOnlyAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    list_display = ('nom_entreprise', 'schema_name', 'created_on')
    search_fields = ('nom_entreprise', 'schema_name')

    @schema_context('public')
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id_role', 'role')
    search_fields = ('role',)


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('id_utilisateur', 'nom_utilisateur', 'prenom_utilisateur', 'num_utilisateur', 'username', 'entreprise', 'role')
    search_fields = ('nom_utilisateur', 'prenom_utilisateur', 'num_utilisateur', 'entreprise__nom_entreprise', 'role__role')
    exclude = ('groups', 'user_permissions', 'last_token', 'date_joined', 'last_login')

    def save_model(self, request, obj, form, change):
        obj.save(utilisateur_createur=request.user)
