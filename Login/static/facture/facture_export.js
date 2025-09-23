$(document).ready(function () {
    $('#confirmer-export').click(function() {
        const dateDeb = $('#date_deb').val();
        const dateFin = $('#date_fin').val();
        const commune = $('#commune').val();
        const num_client_deb = $('#num_client_deb').val();
        const num_client_fin = $('#num_client_fin').val();

        // Construire l'URL avec les paramètres GET
        let url = '/facture/pdf';
        url += `?date_deb=${dateDeb}&date_fin=${dateFin}&commune=${commune}`;
        if (num_client_deb) url += `&num_client_deb=${num_client_deb}`;
        if (num_client_fin) url += `&num_client_fin=${num_client_fin}`;

        // Rediriger vers l'URL d'export
        window.location.href = url;
    });
})