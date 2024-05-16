$(document).ready(function(){
    $('#myTable').DataTable({
        searching: true,
        "order": [],
        language: {
            url: '/static/fr-FR.json',
        },
    });
    // Hide automatique le message après quelque seconde
    $("#alert").animate({
        opacity: 1,
        }, 2000, function() {
            $("#alert").delay(4000).fadeOut();
    });

    function traiterChamp(champ) {
        const inputValue = champ.val();
        let numericValue = inputValue.replace(/,/g, '.');
        numericValue = numericValue.replace(/[^\d.]/g, '');
        const decimalCount = numericValue.split('.').length - 1;
        if (decimalCount > 1) {
            numericValue = numericValue.slice(0, -1);
        }
        champ.val(numericValue);
    }
    let champ = $('#paiement, #prix_m3, #tva, #taux_taxe')
    champ.on('input',function() {
        traiterChamp($(this));
    });
    champ.trigger('input');

    $('#num_utilisateur, #tel1_client, #tel2_client').on('input', function() {
        // Obtenir la valeur actuelle du champ de texte
        const inputValue = $(this).val();

        // Remplacer tout sauf les chiffres par une chaîne vide
        let numericValue = inputValue.replace(/\D/g, '');

        numericValue = numericValue.slice(0, 10);

        const decimalCount = numericValue.split('.').length - 1;
        if (decimalCount > 1) {
            numericValue = numericValue.slice(0, -1); // Supprimer le dernier caractère (point en trop)
        }
        $(this).val(numericValue);
    });

});