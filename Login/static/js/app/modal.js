// Import des fonctions utilitaires
const { formaterNombreDecimal, formaterNombreEntier } = window.utils || {};

$(document).ready(function(){
    // Initialisation de DataTable
    $('#myTable').DataTable({
        searching: true,
        "order": [],
        language: {
            url: '/static/fr-FR.json',
        },
    });
    $('.dataTables_filter input[type="search"]').css('height', '500px');
    
    // Gestion des messages d'alerte
    $("#alert").animate({
        opacity: 1,
    }, 2000, function() {
        $("#alert").delay(4000).fadeOut();
    });

    // Configuration des champs numériques décimaux
    const champsDecimaux = $('#paiement, #tva, #taux_taxe, #num_compteur');
    champsDecimaux.on('input', function() {
        formaterNombreDecimal($(this));
    }).trigger('input');

    // Configuration des champs numériques entiers (téléphones, etc.)
    $('#num_utilisateur, #tel1_client, #tel2_client, #id_client').on('input', function() {
        formaterNombreEntier($(this), 10);
    });

    // Gestion de l'export Excel pour les clients
    $('#confirmer-export-client-excel').click(function() {
        const commune = $('#commune').val();
        const url = `/clients/excel?commune=${commune}`;
        window.open(url, '_blank');
        $('#export-client-excel').modal('hide');
    });

    // Gestion de l'export Excel pour le main courante
    $('#confirmer-exportmc-excel').click(function() {
        const date_deb = $('#date_deb').val();
        const date_fin = $('#date_fin').val();
        const statut = $('#statut').val();
        const url = `/main_courante/excel?date_deb=${date_deb}&date_fin=${date_fin}&statut=${statut}`;
        window.open(url, '_blank');
        $('#exportmc-excel').modal('hide');
    });
});
