import base64
import gc
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO

from celery import shared_task
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='facturation.generate_pdf_task')
def generate_pdf_task(self, facture_ids, entreprise_id, schema_name):
    """
    Tâche Celery pour générer un PDF multi-pages des factures.
    Reçoit des IDs sérialisables au lieu d'objets request.
    """
    from django_tenants.utils import schema_context

    try:
        with schema_context(schema_name):
            from Facturation.models import Facture, MontantHT
            from Facturation.views import (
                facture_context_pdf_no_request, get_prix_m3_client,
                get_derniers_montants_impayees, calculer_total_net_a_payer
            )
            from Tenants.models import Entreprise

            # Récupérer l'entreprise pour déterminer le template
            entreprise = Entreprise.objects.get(pk=entreprise_id)
            is_eatc = entreprise.schema_name == "eatc"

            template_name = 'all_page/facturation/facture/{}'.format(
                'templatepdf.html' if is_eatc else 'templatenoeatc.html'
            )
            template = get_template(template_name)

            # Récupérer les factures
            factures = Facture.objects.filter(
                pk__in=facture_ids
            ).select_related(
                'num_contrat',
                'num_contrat__client',
                'relevecompteur'
            ).prefetch_related(
                'montantht_set',
                'montantht_set__montantttc'
            ).order_by("num_contrat_id__adresse_contrat")

            total_factures = len(facture_ids)
            html_sections = []
            batch_size = 4

            factures_list = list(factures)

            for i in range(0, len(factures_list), batch_size):
                batch = factures_list[i:i + batch_size]
                temp_group = []

                for idx, fact in enumerate(batch):
                    try:
                        # Mettre à jour la progression
                        current = i + idx + 1
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'current': current,
                                'total': total_factures,
                                'percent': int((current / total_factures) * 100)
                            }
                        )

                        # Préparer le contexte sans request
                        context = _prepare_facture_context_for_task(
                            fact, entreprise_id, is_eatc
                        )
                        if context is None:
                            continue

                        html = template.render(context)
                        temp_group.append(html)
                        del context

                    except Exception as e:
                        logger.error(
                            f"Erreur facture {getattr(fact, 'num_facture', 'inconnu')}: {e}"
                        )
                        continue

                if temp_group:
                    for j in range(0, len(temp_group), 4):
                        group = temp_group[j:j + 4]
                        html_sections.append(''.join(group))

                del temp_group
                gc.collect()

            if not html_sections:
                return {'status': 'error', 'message': 'Aucun contenu généré'}

            # Générer le PDF
            pdf_options = {
                'quiet': True,
                'encoding': 'UTF-8',
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'load_file': False,
                'raise_exception': True,
                'default_font': 'Helvetica'
            }

            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>@page {{ size: A4; margin: 1cm; }}</style>
            </head>
            <body>
                {0}
            </body>
            </html>
            """.format('<div style="page-break-after: always;"></div>'.join(html_sections))

            result = BytesIO()
            pdf = pisa.pisaDocument(
                BytesIO(html_content.encode('utf-8')),
                result,
                **pdf_options
            )

            if pdf.err:
                raise ValueError(f"Erreur Pisa lors de la génération")

            if not result.getvalue():
                raise ValueError("Le PDF généré est vide")

            # Sauvegarder le PDF dans un fichier temporaire
            pdf_dir = os.path.join(settings.MEDIA_ROOT, 'temp_pdf')
            os.makedirs(pdf_dir, exist_ok=True)

            filename = f"Factures_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
            filepath = os.path.join(pdf_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(result.getvalue())

            # Nettoyage mémoire
            del html_sections
            del html_content
            result.close()
            gc.collect()

            return {
                'status': 'success',
                'filename': filename,
                'filepath': f'/media/temp_pdf/{filename}',
                'total_factures': total_factures
            }

    except Exception as e:
        logger.error(f"Erreur critique tâche PDF: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}


def _prepare_facture_context_for_task(facture, entreprise_id, is_eatc):
    """
    Version de prepare_facture_context qui ne dépend pas de request.
    """
    from Facturation.views import (
        facture_context_pdf_no_request, get_prix_m3_client,
        get_derniers_montants_impayees, calculer_total_net_a_payer
    )
    from Tenants.models import Entreprise
    from django.http import HttpResponse

    try:
        context = facture_context_pdf_no_request(facture)
        if isinstance(context, HttpResponse):
            return None

        context['prix_m3'] = get_prix_m3_client(facture)

        montants_impayees = get_derniers_montants_impayees(
            facture.num_contrat_id,
            facture.date_facture
        )
        context['montants_impayees_precedents'] = montants_impayees

        total_net_a_payer = calculer_total_net_a_payer(
            facture.montant_total_ttc,
            montants_impayees
        )
        context['total_net_a_payer'] = total_net_a_payer

        # Gestion spécifique au schéma non-EATC
        if not is_eatc:
            try:
                entreprise = Entreprise.objects.get(pk=entreprise_id)
                context.update({
                    'nif': f"{entreprise.nif}" if entreprise.nif else '-',
                    'stat': f"{entreprise.stat}" if hasattr(entreprise, 'stat') and entreprise.stat else '-',
                    'num_mvola': f"{entreprise.numero_mvola}" if hasattr(entreprise, 'numero_mvola') and entreprise.numero_mvola else '-',
                    'nom_mvola': f"{entreprise.nom_mvola}" if hasattr(entreprise, 'nom_mvola') and entreprise.nom_mvola else '-',
                })

                if hasattr(entreprise, 'logo_entreprise') and entreprise.logo_entreprise:
                    with open(entreprise.logo_entreprise.path, 'rb') as img_file:
                        context['logo_entreprise'] = base64.b64encode(img_file.read()).decode('utf-8')

                if hasattr(entreprise, 'signature_entreprise') and entreprise.signature_entreprise:
                    with open(entreprise.signature_entreprise.path, 'rb') as img_file:
                        context['signature_entreprise'] = base64.b64encode(img_file.read()).decode('utf-8')

            except Exception:
                pass

        return context

    except Exception as e:
        logger.error(f"Erreur préparation contexte facture {facture.num_facture}: {e}")
        return None
