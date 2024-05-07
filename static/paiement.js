$(document).ready(function () {
    $(".paiement-valide").on('click', function (event) {
        const id_releve = $(this).attr('id');

        $('#confirmer-paiement').on('click', function () {
            const paiementValue = $('#paiement').val();
            const csrfToken = $('#id_facture').val();
            $.ajax({
                url: '/facture/paiement',
                type: 'POST',
                data: {
                    'id_releve' : id_releve,
                    'paiement': paiementValue, // Envoie la valeur du paiement
                    'csrfmiddlewaretoken': csrfToken, // Assure la protection CSRF
                },
                success: function (response) {
                    $('#paiement-valide').modal("hide");
                    location.reload();
                },
                error: function (error) {
                    console.log("Il y a une erreur !");
                }
            });
        });
    });
});