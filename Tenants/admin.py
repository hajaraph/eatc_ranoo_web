from asyncio.log import logger

from django.contrib import admin, messages
from django.db.models import ProtectedError
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import schema_context, get_tenant_model

from Tenants.models import Entreprise, Domain, Role, Utilisateur, Initial


@admin.register(Entreprise)
class EntrepriseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('nom_entreprise', 'schema_name', 'created_on')
    search_fields = ('nom_entreprise', 'schema_name')


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
