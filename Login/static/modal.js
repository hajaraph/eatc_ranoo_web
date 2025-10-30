$(document).ready(function(){
    $('#myTable').DataTable({
        searching: true,
        "order": [],
        language: {
            url: '/static/fr-FR.json',
        },
    });
    // Hide automatique le message après quelques secondes
    $("#alert").animate({
        opacity: 1,
        }, 2000, function() {
            $("#alert").delay(4000).fadeOut();
    });

    function traiterChamp(champ) {
        const inputValue = champ.val();
        let numericValue = inputValue.replace(/,/g, '.'); // Remplace virgule par point
            numericValue = numericValue.replace(/[^\d.]/g, ''); // Supprime tout sauf chiffres et point

            // Si la saisie commence par un point, le supprimer
            if (numericValue.startsWith('.')) {
                numericValue = numericValue.replace('.', '');
            }

            // Limiter à un seul point décimal de manière plus robuste
            const parts = numericValue.split('.');
            if (parts.length > 2) {
                numericValue = parts[0] + '.' + parts.slice(1).join(''); // Garde le premier point seulement
            }

            champ.val(numericValue);
    }
    let champ = $('#paiement, #tva, #taux_taxe, #num_compteur, #nb_personne_menage, #debit')

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

    $('#confirmer-export-client').click(function() {
        const format = $('#export-format').val();
        const commune = $('#commune').val();
        
        // Construire l'URL avec les paramètres GET
        let url = format === 'pdf' ? 'pdf/client' : 'excel';
        
        // Ajouter le paramètre de commune si sélectionné
        if (commune) {
            url += `?commune=${commune}`;
        }
        
        // Ouvrir un nouvel onglet avec l'URL générée
        window.open(url, '_blank');
        $('#export-client').modal('hide');
    });

    $('#confirmer-exportmc-excel').click(function() {
        const date_deb = $('#date_deb').val();
        const date_fin = $('#date_fin').val();
        const statut = $('#statut').val();
        // Construire l'URL avec les paramètres GET
        let url = '/main_courante/excel';
        url += `?date_deb=${date_deb}&date_fin=${date_fin}&statut=${statut}`;
        // Ouvrir un nouvel onglet avec l'URL générée
        window.open(url, '_blank');
        $('#exportmc-excel').modal('hide');
    });
});