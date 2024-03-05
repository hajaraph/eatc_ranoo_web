import base64
from datetime import timedelta
from io import BytesIO

import qrcode
from django.db.models import Q
from django.utils import timezone

from django.http import JsonResponse
from num2words import num2words
from django.contrib import messages
from django.shortcuts import render

from Clients.models import Contrat
from Clients.views import generate_pdf
from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, MontantHT, Tarif, Avoir, Paiement, Restant, MontantTTC, Taxe
from Login.views import authentification_requis


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
    context = {
        'title_etat': title,
        'active_etat': active,
        'font_facture': font,
        'factures': factures,
        'avoir_count': avoir,
        'restant': restant
    }
    return render(request, 'all_page/facturation/facturation.html', context)


@authentification_requis
def facture_etat_detail(request, num_facture):
    title = 'Facturation | Etat Facture | Détail'
    font = 'custom-font'
    active = 'active'

    # Requete pour chaque detail
    factures = Facture.objects.get(num_facture=num_facture)
    fact_dernier = Facture.objects.filter(
        num_contrat__num_compteur_id=factures.num_contrat.num_compteur_id).latest('date_facture')
    paiement = Paiement.objects.filter(facture__num_facture=num_facture)
    montant = MontantTTC.objects.get(montant_ht__facture__num_facture=num_facture)
    tarif = Tarif.objects.get(cp_commune_id=factures.num_contrat.cp_commune_id)
    taxes = tarif.taxes.all()
    montant_taxes = calcule_montant_taxe(tarif, factures.relevecompteur.conso)
    taxes_montants = list(zip(taxes, montant_taxes))

    date_echeance = factures.relevecompteur.date_releve + timedelta(days=tarif.nb_jour_echeance_fct)
    if paiement.exists():
        paiement = Paiement.objects.get(facture__num_facture=num_facture)

    context = {
        'title_etat_detail': title,
        'active_etat': active,
        'font_facture': font,
        'facture': factures,
        'paiement': paiement,
        'montant': montant,
        'fact': fact_dernier,
        'taxes_montants': taxes_montants,
        'date_echeance': date_echeance
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
        'impayes': impaye
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
        'restants': restants
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
        'avoirs': avoir
    }
    return render(request, 'all_page/facturation/facturation.html', context)


def montantht(total_conso_ht, tarif, factures):
    return MontantHT.objects.create(
        total_conso_ht=round(total_conso_ht, 2),
        tarif_id=tarif,
        facture=factures,
    )


def montantttc(total_conso_ttc, montant_ht):
    return MontantTTC.objects.create(
        total_conso_ttc=total_conso_ttc,
        montant_ht=montant_ht
    )


def cree_montant_objet(tarif, consommation, factures):
    total_conso_ht = tarif.prix_m3 * consommation
    montant_taxe = sum(calcule_montant_taxe(tarif, consommation))
    montant_ht = montantht(total_conso_ht, tarif.pk, factures)
    montantttc(total_conso_ht + montant_taxe, montant_ht)


def calcule_montant_taxe(tarif, consommation):
    montant_ht = tarif.prix_m3 * consommation
    taxes = Taxe.objects.filter(tarif=tarif)
    montants_taxes = [montant_ht * (taxe.taux_taxe / 100) for taxe in taxes]
    return montants_taxes


def facture_creation(date_facture, num_compteur, releve):
    contrat = Contrat.objects.filter(num_compteur=num_compteur).first()
    typeclient = contrat.client.type_client.pk
    consommation = releve.conso

    date_facture1 = date_facture.strftime("%Y%m%d")
    num_facture = f"FACT{date_facture1}{contrat.client.pk}"
    factures = Facture.objects.create(
        num_facture=num_facture,
        date_facture=date_facture,
        num_contrat=contrat,
        relevecompteur_id=releve.pk
    )

    cp_commune = contrat.cp_commune_id
    tarif = Tarif.objects.get(cp_commune_id=cp_commune)

    if typeclient == 1:
        cree_montant_objet(tarif, consommation, factures)

    elif typeclient == 2:
        if consommation >= 10:
            total_conso_ht = tarif.prix_m3 * consommation
            total_conso_ttc = (total_conso_ht * tarif.tva) / 100
            total_conso_ttc += total_conso_ht
            montant_ht = montantht(total_conso_ht, tarif.pk, factures)
            taxe = sum(calcule_montant_taxe(tarif, consommation))
            montantttc(total_conso_ttc + taxe, montant_ht)

        else:
            cree_montant_objet(tarif, consommation, factures)

    num_contrat = contrat.num_contrat
    avoir = Avoir.objects.filter(num_contrat=num_contrat)
    restant = Restant.objects.filter(num_contrat=num_contrat)
    montant = MontantTTC.objects.get(montant_ht__facture_id=factures.pk)

    montant_total_ttc = montant.total_conso_ttc
    # Pour verifie si le contrat a un avoir
    if avoir.exists():
        avoir = Avoir.objects.get(num_contrat=num_contrat)
        factures.avoir_avant = avoir.montant_avoir

        if montant_total_ttc >= avoir.montant_avoir:
            montant_total_ttc -= avoir.montant_avoir
            factures.avoir_utilise = avoir.montant_avoir
            factures.montant_total_ttc = round(montant_total_ttc, 2)
            avoir.delete()
        elif montant_total_ttc < avoir.montant_avoir:
            factures.avoir_utilise = round(montant_total_ttc, 2)
            montant_total_ttc = avoir.montant_avoir - montant_total_ttc
            avoir.montant_avoir = round(montant_total_ttc, 2)
            factures.montant_total_ttc = 0
            avoir.save()

    # Pour verifié si le client a un restant d'une facture avant
    elif restant.exists():
        restant = Restant.objects.get(num_contrat=num_contrat)
        montant_total_ttc += restant.restant
        factures.restant_precedant = round(restant.restant, 2)
        factures.montant_total_ttc = round(montant_total_ttc, 2)
        restant.delete()
    else:
        factures.montant_total_ttc = round(montant_total_ttc, 2)
    factures.save()


# def calculer_montants(tarif, consommation, factures, tva=False):
#     total_conso_ht = tarif.prix_m3 * consommation
#
#     if tva:
#         total_conso_ht = (total_conso_ht * tarif.tva) / 100 + total_conso_ht
#
#     montant_ht = montantht(total_conso_ht, tarif.pk, factures)
#     montantttc(total_conso_ht, montant_ht)
#
#     return montant_ht


@authentification_requis
def facture_genere_pdf(request, pk):
    factures = Facture.objects.get(pk=pk)
    montant = MontantHT.objects.get(facture=pk)

    num_compteur = factures.num_contrat.num_compteur_id
    dernier_releve = ReleveCompteur.objects.filter(num_compteur_id=num_compteur).last()

    # Recupère le 2ème dernier date de relevé
    releve_avant = ReleveCompteur.objects.filter(num_compteur_id=num_compteur).order_by('-date_releve')

    tarif = montant.tarif
    taxes = tarif.taxes.all()
    montant_taxes = calcule_montant_taxe(tarif, factures.relevecompteur.conso)
    taxes_montants = list(zip(taxes, montant_taxes))
    date_paiment = dernier_releve.date_releve + timedelta(days=tarif.nb_jour_echeance_fct)

    if len(releve_avant) >= 2:
        releve_avant = releve_avant[1]
    else:
        releve_avant = ReleveCompteur.objects.first()

    typeclient = factures.num_contrat.client.type_client.pk

    if typeclient == 2:
        if dernier_releve.conso >= 10:
            tva_montant = (montant.total_conso_ht * montant.tarif.tva) / 100
        else:
            tva_montant = 0
    else:
        tva_montant = 0

    # Transforme le chiffre en lettre
    try:
        nombre = float(factures.montant_total_ttc)
        lettre = num2words(nombre, lang='fr')
        lettre = lettre[0].upper() + lettre[1:]
    except ValueError:
        lettre = "Nombre invalide"

    template_path = 'all_page/facturation/facture/templatepdf.html'
    filename_prefix = f'Facture_Numero_{factures.num_facture}'
    qr_code = generate_qr_code(request, factures.num_facture)
    context = {
        'instance': factures,
        'montant': montant,
        'lettre': lettre,
        'dernier_releve': dernier_releve,
        'releve_avant': releve_avant,
        'montant_ht_total': round(montant.total_conso_ht, 2),
        'montant_tva': round(tva_montant, 2),
        'taxes_montants': taxes_montants,
        'date_paiment': date_paiment,
        'qr_code': qr_code
    }
    return generate_pdf(request, context, template_path, filename_prefix)


@authentification_requis
def facture_paiement(request, *args, **kwargs):
    id_facture = request.POST['id_facture']
    montant_payer = float(request.POST['paiement'])
    fact_paiement = Facture.objects.get(pk=id_facture)
    net_paye = fact_paiement.montant_total_ttc - montant_payer
    num_contrat = fact_paiement.num_contrat

    if net_paye == 0:
        fact_paiement.statut = True
        Paiement.objects.create(
            montant_payer=montant_payer,
            facture_id=fact_paiement.pk
        )
    elif fact_paiement.montant_total_ttc < montant_payer:
        net_paye = montant_payer - fact_paiement.montant_total_ttc
        fact_paiement.statut = True
        Paiement.objects.create(
            montant_payer=fact_paiement.montant_total_ttc,
            facture_id=fact_paiement.pk
        )

        avoir = Avoir.objects.filter(num_contrat=num_contrat)
        if avoir.exists():
            avoir = Avoir.objects.get(num_contrat=num_contrat)
            avoir.montant_avoir += round(net_paye, 2)
            avoir.utilisateur_id = request.session.get('id_utilisateur'),
            avoir.save()
        else:
            Avoir.objects.create(
                montant_avoir=round(net_paye, 2),
                utilisateur_id=request.session.get('id_utilisateur'),
                num_contrat=num_contrat
            )
    else:
        restant = Restant.objects.filter(num_contrat=num_contrat)
        paiements = Paiement.objects.filter(facture_id=fact_paiement.pk)
        restant_value = round(net_paye, 2)
        fact_paiement.restant_nouvel = restant_value

        # Verifie si il exist déjà un restant et un paiement déjà fait
        if restant.exists() and paiements.exists():
            restant_exist = Restant.objects.get(num_contrat=num_contrat)
            paiement_restant = Paiement.objects.get(facture_id=fact_paiement.pk)

            if montant_payer == restant_exist.restant:
                restant_exist.delete()
                paiement_restant.montant_payer += montant_payer
                fact_paiement.statut = True
                fact_paiement.restant_nouvel = None

            elif montant_payer < restant_exist.restant:
                restant_exist.restant -= montant_payer
                restant_exist.restant = round(restant_exist.restant, 2)
                restant_exist.date_restant = timezone.now()
                fact_paiement.restant_nouvel = restant_exist.restant
                restant_exist.save()

                paiement_restant.montant_payer += montant_payer
                paiement_restant.date_paiement = timezone.now()

                fact_paiement.restant = round(restant_exist.restant, 2)
            else:
                paiement_restant.montant_payer += restant_exist.restant
                fact_paiement.statut = True
                fact_paiement.restant_nouvel = None
                # creation d'une nouvel avoir
                avoir = montant_payer - restant_exist.restant
                Avoir.objects.create(
                    montant_avoir=round(avoir, 2),
                    utilisateur_id=request.session.get('id_utilisateur'),
                    num_contrat=num_contrat
                )
                restant_exist.delete()
            paiement_restant.save()
        else:
            Restant.objects.create(
                restant=round(net_paye, 2),
                num_contrat=num_contrat
            )
            Paiement.objects.create(
                montant_payer=round(montant_payer, 2),
                facture_id=fact_paiement.pk
            )
    fact_paiement.save()
    messages.success(request, 'Facture payé avec succès !')
    return JsonResponse({'message': 'Paiement effectué avec succès'})


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
