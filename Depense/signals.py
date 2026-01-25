from django.dispatch import receiver
from django_tenants.signals import post_schema_sync
from django_tenants.utils import schema_context

from Depense.models import Categories


@receiver(post_schema_sync)
def create_default_categories(sender, tenant, **kwargs):
    if tenant.schema_name != 'public':
        with schema_context(tenant.schema_name):
            default_categories = [
                ("D101", "Réparation et maintenance réseau"),
                ("D102", "Loyer bureau"),
                ("D103", "Fourniture de bureau"),
                ("D104", "Communication"),
                ("D105", "Electricité"),
                ("D106", "Intéressement variable des fontainiers "),
                ("D107", "Intéressement fixe des fontainiers "),
                ("D108", "Déplacement / transport"),
                ("D109", "Analyse qualité "),
                ("D110", "Frais administratifs"),
                ("D111", "Charges diverses"),
                ("D201", "Technicien"),
                ("D202", "recouvrement"),
                ("D203", "Gardien"),
                ("D204", "Main d'œuvre"),
                ("D205", "RAF"),
                ("D301", "Equipement BP (a part compteurs et robinets)"),
                ("D302", "Achats robinets pour nouveau BP"),
                ("D303", "Achats robinets  à vendre"),
                ("D304", "Achats compteurs"),
                ("D401", "CNaPS"),
                ("D402", "OSIEF"),
                ("D501", "Facture impayés"),
                ("D502", "Devis impayés"),
                ("D601", "Impôt sur le revenu salarié"),
                ("D602", "Taxe communale"),
                ("D603", "Impôt sur les bénéfices (24%)"),
            ]

            for cat_id, cat_name in default_categories:
                Categories.objects.get_or_create(
                    id_category=cat_id,
                    defaults={'nom_categorie': cat_name}
                )
