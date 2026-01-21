from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import schema_context
from django.db import connection
from django.db.models import Count, ProtectedError
from django.utils.html import format_html
from django.contrib import messages

from Tenants.models import Entreprise, Domain, Role, Utilisateur
from .forms import UtilisateurInlineForm, UtilisateurCreationForm

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


class UtilisateurInline(admin.StackedInline):
    model = Utilisateur
    form = UtilisateurInlineForm
    extra = 1
    max_num = 1
    exclude = ('groups', 'user_permissions', 'last_token', 'date_joined', 'last_login', 'is_staff', 'is_superuser', 'is_active', 'first_name', 'last_name', 'username')


@admin.register(Entreprise)
class EntrepriseAdmin(PublicSchemaOnlyAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    inlines = [UtilisateurInline]
    list_display = ('logo_preview', 'nom_entreprise', 'schema_name', 'nombre_utilisateurs', 'created_on')
    list_display_links = ('logo_preview', 'nom_entreprise')
    search_fields = ('nom_entreprise', 'schema_name')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(user_count=Count('utilisateur'))
        return queryset

    @admin.display(description='Utilisateurs', ordering='user_count')
    def nombre_utilisateurs(self, obj):
        return obj.user_count

    @admin.display(description='Logo')
    def logo_preview(self, obj):
        if obj.logo_entreprise:
            return format_html('<img src="{}" style="height: 30px; width: auto; border-radius: 4px;" />', obj.logo_entreprise.url)
        return "-"

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
    fieldsets = (
        ('Identité', {
            'fields': ('nom_utilisateur', 'prenom_utilisateur', 'photo_utilisateur')
        }),
        ('Compte & Connexion', {
            'fields': ('username', 'password', 'num_utilisateur')
        }),
        ('Organisation', {
            'fields': ('entreprise', 'role', 'cp_commune')
        }),
        ('Statut', {
            'fields': ('statut',)
        }),
    )


    actions = ['supprimer_utilisateurs']
    form = UtilisateurCreationForm

    def get_form(self, request, obj=None, **kwargs):
        # We generally use the creation form which handles password hashing on save.
        # For the change view, we might want to hide the password field to avoid overwriting it accidentally,
        # or use a different form. But standard ModelAdmin behavior with a custom form 
        # that has a non-required password field works fine usually.
        # Let's stick to the custom form.
        return super().get_form(request, obj, **kwargs)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        # Disable the default delete button on the individual edit page
        return False

    def save_model(self, request, obj, form, change):
        # The form's save method handles password hashing if using UtilisateurCreationForm
        # But save_model calls form.save(), so we are good.
        # We just need to ensure created_by is set.
        obj.save(utilisateur_createur=request.user)

    @admin.action(description="Supprimer les utilisateurs sélectionnés (Sécurisé)")
    def supprimer_utilisateurs(self, request, queryset):
        deleted_count = 0
        errors = []

        for user in queryset:
            if user.entreprise:
                try:
                    # Switch to the tenant's schema to check valid relations
                    with schema_context(user.entreprise.schema_name):
                        user.delete()
                        deleted_count += 1
                except ProtectedError:
                    errors.append(f"{user.nom_utilisateur} {user.prenom_utilisateur} - Lié à des données (ex: Contrats)")
                except Exception as e:
                    errors.append(f"{user.nom_utilisateur} {user.prenom_utilisateur} - Erreur: {e}")
            else:
                # If no entreprise, try standard delete (careful with global checks)
                try:
                    user.delete()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{user.nom_utilisateur} {user.prenom_utilisateur} - Erreur (Pas d'entreprise): {e}")

        if deleted_count > 0:
            self.message_user(request, f"{deleted_count} utilisateur(s) supprimé(s) avec succès.", messages.SUCCESS)
        
        if errors:
            self.message_user(request, f"Erreurs de suppression : {', '.join(errors)}", messages.ERROR)

