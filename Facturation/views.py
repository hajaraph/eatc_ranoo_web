import base64
from datetime import timedelta, datetime
from io import BytesIO

import qrcode
from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone

from django.http import JsonResponse, HttpResponse
from num2words import num2words
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from xhtml2pdf import pisa

from Clients.communes import Region
from Clients.models import Contrat
from Clients.views import generate_pdf
from Compteurs.models import ReleveCompteur, Compteur
from Facturation.models import Facture, MontantHT, Tarif, Avoir, Paiement, Restant, MontantTTC, Taxe
from Login.views import authentification_requis, role_requis
from Parametre.views import exporter_en_excel, enregistre_historique


def date_range(request, model, datedeb, datefin, date_field, statut):
    if datedeb and datefin:
        if datedeb > datefin:
            messages.warning(request, f'La Date Début ne doit pas être supérieure à la Date Fin !')
            return model.objects.all().order_by(f'-{date_field}')
        else:
            if statut == 'paye':
                return model.objects.filter(statut=True)
            elif statut == 'impaye':
                return model.objects.filter(statut=False)
            else:
                filter_query = Q(**{f"{date_field}__range": [datedeb, datefin]})
                return model.objects.filter(filter_query)
    else:
        if statut == 'paye':
            return model.objects.filter(statut=True)
        elif statut == 'impaye':
            return model.objects.filter(statut=False)
        else:
            return model.objects.all().order_by(f'-{date_field}')


def date_range_fact_pdf(date_deb, date_fin, commune, model):
    if date_deb and date_fin and commune:
        return model.filter(date_facture__range=[date_deb, date_fin], num_contrat__cp_commune_id=commune)
    elif date_deb and date_fin:
        return model.filter(date_facture__range=[date_deb, date_fin])
    elif date_deb and commune:
        return model.filter(date_facture=date_deb, num_contrat__cp_commune_id=commune)
    elif date_deb or date_fin:
        return model.filter(date_facture=date_deb or date_fin)
    elif commune:
        return model.filter(num_contrat__cp_commune_id=commune)
    else:
        return model


@authentification_requis
def facture(request):
    title = 'Facturation | Etat Facture'
    font = 'custom-font'
    active = 'active'
    avoir = Avoir.objects.count()
    restant = Restant.objects.count()
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    factures = date_range(request, Facture, datedeb, datefin, 'date_facture', None)
    region = Region.objects.order_by('region').all()
    impayer_exist = Facture.objects.filter(statut=False).exists()
    context = {
        'title_etat': title,
        'active_etat': active,
        'font_facture': font,
        'factures': factures,
        'impayer_exist': impayer_exist,
        'avoir_count': avoir,
        'restant': restant,
        'regions': region,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else '',
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_etat_detail(request, num_facture):
    title = 'Facturation | Etat Facture | Détail'
    font = 'custom-font'
    active = 'active'

    # Requete pour chaque detail
    factures = Facture.objects.get(num_facture=num_facture)
    paiements = Paiement.objects.filter(facture__num_facture=num_facture)
    montant = MontantTTC.objects.get(montant_ht__facture__num_facture=num_facture)
    typeclient = factures.num_contrat.client.type_client_id

    if paiements.exists():
        paiements = Paiement.objects.get(facture__num_facture=num_facture)

    context = {
        'title_etat_detail': title,
        'active_etat': active,
        'font_facture': font,
        'factures': factures,
        'paiement': paiements,
        'montant': montant,
        'typeclient': typeclient,
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_paye(request):
    title = 'Facturation | Payé'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    paye = date_range(request, Facture, datedeb, datefin, 'date_restant', 'paye')

    context = {
        'title_facture_paye': title,
        'active_facture_paye': active,
        'font_facture': font,
        'payes': paye,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_impaye(request):
    title = 'Facturation | Impayé'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    impaye = date_range(request, Facture, datedeb, datefin, 'date_restant', 'impaye')
    context = {
        'title_facture_impaye': title,
        'active_facture_impaye': active,
        'font_facture': font,
        'impayes': impaye,
        'datedeb': datedeb,
        'datefin': datefin
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_restant(request):
    title = 'Facturation | Facture'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    restants = date_range(request, Restant, datedeb, datefin, 'date_restant', None)
    context = {
        'title_facture': title,
        'active_facture': active,
        'font_facture': font,
        'restants': restants,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_retard(request):
    title = 'Facturation | Retard'
    font = 'custom-font'
    active = 'active'
    context = {
        'title_retard': title,
        'active_retard': active, 'font_facture': font}
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_avoir(request):
    title = 'Facturation | Avoir'
    font = 'custom-font'
    active = 'active'
    datedeb = request.GET.get('datedeb')
    datefin = request.GET.get('datefin')
    avoir = date_range(request, Avoir, datedeb, datefin, 'date_avoir', None)
    context = {
        'title_avoir': title,
        'active_avoir': active,
        'font_facture': font,
        'avoirs': avoir,
        'datedeb': datedeb if datedeb else '',
        'datefin': datefin if datefin else ''
    }
    return render(request, 'all_page/facturation/facturation.html', context)


class Calcule:

    @staticmethod
    def montantht(total_conso_ht, tarif, factures):
        try:
            return MontantHT.objects.create(
                total_conso_ht=round(total_conso_ht, 0),
                tarif_id=tarif,
                facture=factures,
            )
        except Exception as e:
            return HttpResponse(f"Error creating MontantHT: {e}")

    @staticmethod
    def montantttc(total_conso_ttc, montant_ht):
        try:
            return MontantTTC.objects.create(
                total_conso_ttc=total_conso_ttc,
                montant_ht=montant_ht
            )
        except Exception as e:
            return HttpResponse(f"Error creating MontantTTC: {e}")

    @staticmethod
    def calculate_total_conso_ht(typeclient, tarif, consommation):
        if typeclient == 1:
            return tarif.prix_m3_bs * consommation
        elif typeclient == 2:
            return tarif.prix_m3_bp * consommation
        elif typeclient == 3:
            return tarif.prix_m3_k * consommation
        else:
            raise ValueError("Invalid typeclient")

    @staticmethod
    def cree_montant(typeclient, tarif, consommation, factures):
        try:
            total_conso_ht = Calcule.calculate_total_conso_ht(typeclient, tarif, consommation)
            montant_taxe = sum(Calcule.montant_taxe(typeclient, tarif, consommation))
            montant_ht = Calcule.montantht(total_conso_ht, tarif.pk, factures)
            if montant_ht:
                Calcule.montantttc(total_conso_ht + montant_taxe, montant_ht)
        except Exception as e:
            return HttpResponse(f"Error in cree_montant: {e}")

    @staticmethod
    def montant_taxe(typeclient, tarif, consommation):
        try:
            montant_ht = Calcule.calculate_total_conso_ht(typeclient, tarif, consommation)
            taxes = Taxe.objects.filter(tarif=tarif)
            montants_taxes = [montant_ht * (taxe.taux_taxe / 100) for taxe in taxes]
            return montants_taxes
        except Exception as e:
            return HttpResponse(f"Erreur lors de calcule des taxes: {e}")


def precess_avoir_restant(contrat, factures):
    try:
        montant = MontantTTC.objects.get(montant_ht__facture_id=factures.pk)
        montant_total_ttc = montant.total_conso_ttc

        # Check if there is a credit note (avoir)
        avoir = Avoir.objects.filter(num_contrat=contrat.num_contrat).first()
        if avoir:
            factures.avoir_avant = avoir.montant_avoir
            if montant_total_ttc >= avoir.montant_avoir:
                montant_total_ttc -= avoir.montant_avoir
                factures.avoir_utilise = avoir.montant_avoir
                factures.montant_total_ttc = round(montant_total_ttc, 0)
                avoir.delete()
            else:
                factures.avoir_utilise = round(montant_total_ttc, 0)
                avoir.montant_avoir -= montant_total_ttc
                montant_total_ttc = 0
                avoir.save()
                factures.montant_total_ttc = 0

        # Check if there is a remaining balance (restant)
        restant = Restant.objects.filter(num_contrat=contrat.num_contrat).first()
        if restant:
            montant_total_ttc += restant.restant
            factures.restant_precedant = round(restant.restant, 0)
            factures.montant_total_ttc = round(montant_total_ttc, 0)
            restant.delete()
        else:
            factures.montant_total_ttc = round(montant_total_ttc, 0)

    except Exception as e:
        return HttpResponse(f"Error processing credit and remaining balance: {e}")


def facture_creation(date_facture, num_compteur, releve):
    try:
        contrat = get_object_or_404(Contrat, num_compteur_id=num_compteur)
        tarif = Tarif.objects.get(cp_commune_id=contrat.cp_commune_id)
        taxes = Taxe.objects.filter(tarif_id=tarif.id_tarif)

        typeclient = contrat.client.type_client.pk
        consommation = releve.conso
        montant_ht = Calcule.calculate_total_conso_ht(typeclient, tarif, consommation)
        relever = ReleveCompteur.objects.filter(num_compteur_id=num_compteur)
        dernier_releve = relever.order_by('-date_releve')[1]
        date_relever = relever.latest('date_releve').date_releve

        date_echeance = date_relever + timedelta(days=tarif.nb_jour_echeance_fct)

        taxes_appliquees = [
            {
                "id_taxe": taxe.id_taxe,
                "nom_taxe": taxe.nom_taxe,
                "montant_taxe": montant_ht * (taxe.taux_taxe / 100)
            }
            for taxe in taxes
        ]

        date_facture_str = date_facture.strftime("%Y%m%d")
        num_facture = f"FACT{date_facture_str}{num_compteur}"
        factures = Facture.objects.create(
            num_facture=num_facture,
            date_facture_precedant=dernier_releve.date_releve,
            date_facture=date_facture,
            taxes_appliquees=taxes_appliquees,
            date_echeance=date_echeance,
            num_contrat_id=contrat.num_contrat,
            relevecompteur_id=releve.pk
        )

        # Calcul montant TTC selon client type
        if typeclient == 1 or (typeclient == 2 and consommation < tarif.conso_tva_app) or typeclient == 3:
            Calcule.cree_montant(typeclient, tarif, consommation, factures)

        elif typeclient == 2 and consommation >= tarif.conso_tva_app:
            total_conso_ht = tarif.prix_m3_bp * consommation
            tva = (total_conso_ht * tarif.tva) / 100
            total_conso_ttc = total_conso_ht + tva
            montant_ht = Calcule.montantht(total_conso_ht, tarif.pk, factures)
            factures.tva_appliquer = tva

            if montant_ht:
                taxe = sum(Calcule.montant_taxe(typeclient, tarif, consommation))
                Calcule.montantttc(total_conso_ttc + taxe, montant_ht)

        precess_avoir_restant(contrat, factures)
        factures.save()
        return factures
    except Contrat.DoesNotExist:
        raise ValueError(f"Pas de contrat trouvé pour le numéro de compteur: {num_compteur}")
    except Exception as e:
        return HttpResponse(f"Error creating invoice: {e}")


def facture_context_pdf(request, factures):
    try:
        montant = MontantHT.objects.get(facture=factures.pk)
        typeclient = factures.num_contrat.client.type_client_id
        num_compteur = factures.num_contrat.num_compteur_id
        compteur = Compteur.objects.get(pk=num_compteur)
        reveler_precedant = get_object_or_404(compteur.relevecompteurs, date_releve=factures.date_facture_precedant)
        relever_actuel = get_object_or_404(compteur.relevecompteurs, date_releve=factures.date_facture)

        try:
            nombre = float(factures.montant_total_ttc)
            lettre = num2words(nombre, lang='fr')
            lettre = lettre[0].upper() + lettre[1:]
        except ValueError:
            lettre = "Nombre invalide"

        qr_code = generate_qr_code(request, factures.num_facture)
        paiement_exist = Paiement.objects.filter(facture_id=factures.pk).exists()

        context = {
            'instance': factures,
            'montant': montant,
            'typeclient': typeclient,
            'lettre': lettre,
            'reveler_precedant': reveler_precedant,
            'relever_actuel': relever_actuel,
            'montant_ht_total': round(montant.total_conso_ht, 0),
            'paiement_exist': paiement_exist,
            'qr_code': qr_code
        }
        return context

    except MontantHT.DoesNotExist:
        return HttpResponse(f"MontantHT n'exist pas pour le facture {factures.num_facture}", content_type='text/plain')
    except ReleveCompteur.DoesNotExist:
        return HttpResponse(f"ReleveCompteur n'exist pas pour le numéro de compteur "
                            f"{factures.num_contrat.num_compteur_id}", content_type='text/plain')
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", content_type='text/plain')


@authentification_requis
def facture_genere_pdf(request, num_facture):
    factures = Facture.objects.get(num_facture=num_facture)
    context = facture_context_pdf(request, factures)

    if isinstance(context, HttpResponse):
        # Si context est une réponse HTTP, retourne-la (cela signifie qu'une erreur est survenue)
        return context

    template_path = 'all_page/facturation/facture/templatepdf.html'
    filename_prefix = f"{factures.num_facture}-({datetime.now().strftime('%d/%m/%Y')})"
    return generate_pdf(request, context, template_path, filename_prefix)


def render_html_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    return html


@authentification_requis
def generate_multiple_pages_pdf(request):
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    commune = request.GET.get('commune')

    factures = Facture.objects.filter(statut=False)
    html_sections = []

    if factures:
        factures = date_range_fact_pdf(date_deb, date_fin, commune, factures)

        for fact in factures:
            context = facture_context_pdf(request, fact)

            if isinstance(context, HttpResponse):
                # Si context est une réponse HTTP, retourne-la (cela signifie qu'une erreur est survenue)
                return context

            html = render_html_to_pdf('all_page/facturation/facture/templatepdf.html', context)
            if html:
                html_sections.append(html)
            else:
                return HttpResponse(f"Erreur lors de la génération du HTML pour la facture {fact.num_facture}")

        if not html_sections:
            return HttpResponse("Aucune facture valide pour générer un PDF")

        combined_html = '<div style="page-break-after: always;"></div>'.join(html_sections)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(combined_html.encode("UTF-8")), result)

        if not pdf.err:
            filename = f"Factures({datetime.now().strftime('%d/%m/%Y')}).pdf"
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return HttpResponse("Erreur lors de la génération du PDF.")
    else:
        messages.warning(request, f"Pas de facture impayé !")
        return redirect('facture')


def paiement(id_releve, montant_payer, utilisateur):
    fact_paiement = Facture.objects.get(relevecompteur_id=id_releve)
    net_paye = fact_paiement.montant_total_ttc - montant_payer
    num_contrat = fact_paiement.num_contrat_id

    fact_paiement.statut = True
    if net_paye == 0:
        Paiement.objects.create(
            montant_payer=montant_payer,
            facture_id=fact_paiement.pk
        )

    elif net_paye < 0:
        net_paye = montant_payer - fact_paiement.montant_total_ttc
        Paiement.objects.create(
            montant_payer=fact_paiement.montant_total_ttc,
            facture_id=fact_paiement.pk
        )

        avoir = Avoir.objects.filter(num_contrat=num_contrat)
        if avoir.exists():
            avoir = Avoir.objects.get(num_contrat_id=num_contrat)
            avoir.montant_avoir += round(net_paye, 0)
            avoir.utilisateur_id = utilisateur,
            fact_paiement.avoir_nouveau = avoir.montant_avoir
            avoir.save()
        else:
            fact_paiement.avoir_nouveau = round(net_paye, 0)
            Avoir.objects.create(
                montant_avoir=round(net_paye, 2),
                utilisateur_id=utilisateur,
                num_contrat_id=num_contrat
            )

    else:
        restant = Restant.objects.filter(num_contrat=num_contrat)
        paiements = Paiement.objects.filter(facture_id=fact_paiement.pk)
        restant_value = round(net_paye, 0)
        fact_paiement.restant_nouvel = restant_value

        # Verifie si il exist déjà un restant et un paiement déjà fait
        if restant.exists() and paiements.exists():
            restant_exist = Restant.objects.get(num_contrat=num_contrat)
            paiement_restant = Paiement.objects.get(facture_id=fact_paiement.pk)

            if montant_payer == restant_exist.restant:
                restant_exist.delete()
                paiement_restant.montant_payer += montant_payer
                fact_paiement.restant_nouvel = None

            elif montant_payer < restant_exist.restant:
                restant_exist.restant -= montant_payer
                restant_exist.restant = round(restant_exist.restant, 0)
                restant_exist.date_restant = timezone.now()
                fact_paiement.restant_nouvel = restant_exist.restant
                restant_exist.save()

                paiement_restant.montant_payer += montant_payer
                paiement_restant.date_paiement = timezone.now()

                fact_paiement.restant = round(restant_exist.restant, 0)
            else:
                paiement_restant.montant_payer += restant_exist.restant
                fact_paiement.restant_nouvel = None
                # creation d'une nouvel avoir
                avoir = montant_payer - restant_exist.restant
                Avoir.objects.create(
                    montant_avoir=round(avoir, 0),
                    utilisateur_id=utilisateur,
                    num_contrat_id=num_contrat
                )
                restant_exist.delete()
            paiement_restant.save()
        else:
            Restant.objects.create(
                restant=round(net_paye, 0),
                num_contrat_id=num_contrat,
                utilisateur_id=utilisateur
            )
            Paiement.objects.create(
                montant_payer=round(montant_payer, 0),
                facture_id=fact_paiement.pk
            )
    fact_paiement.save()


@authentification_requis
def facture_paiement(request, *args, **kwargs):
    id_releve = request.POST['id_releve']
    montant_payer = float(request.POST['paiement'])
    utilisateur = request.session.get('id_utilisateur')
    paiement(id_releve, montant_payer, utilisateur)
    messages.success(request, 'Facture payé avec succès !')
    return JsonResponse({'message': 'Paiement effectué avec succès'})


@authentification_requis
@role_requis('Administrateur', 'Gestionnaire')
def facture_export_excel(request):
    date_deb = request.GET.get('date_deb')
    date_fin = request.GET.get('date_fin')
    commune = request.GET.get('commune')

    factures = Facture.objects.all()
    nom_fichier = f"facture.xlsx"
    factures = date_range_fact_pdf(date_deb, date_fin, commune, factures)

    champs = [
        'num_facture',
        'date_facture',
        'montant_total_ttc',
        'avoir_avant',
        'avoir_utilise',
        'restant_precedant',
        'restant_nouvel',
        'statut',
        'num_contrat',
    ]

    nom_colonnes = [
        'Numéro Facture',
        'Date Facture',
        'Montant Total TTC',
        'Avoir avant',
        'Avoir Utilisé',
        'Restant Precedant',
        'Restant Nouvel',
        'Status',
        'Numéro Contrat'
    ]
    response = exporter_en_excel(factures, nom_fichier, champs, nom_colonnes)
    message = f"Export de tout de facture"
    enregistre_historique(message, request.session.get('id_utilisateur'))
    return response


def generate_qr_code(request, num_facture):
    # Les données que vous voulez encoder dans le QR code (peut être un lien, du texte, etc.)
    data = num_facture

    # Création de l'objet QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Création de l'image QR code
    img = qr.make_image(fill_color="black", back_color="white")

    # Conversion de l'image en réponse HTTP
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()
