$(document).ready(function () {
    $('#btnLaunchCalc').on('click', function () {
        // Récupérer les valeurs
        const dateDeb = $('#calcDateDeb').val();
        const dateFin = $('#calcDateFin').val();
        const categorieId = $('#calcCategorie').val();

        const $resultArea = $('#calcResultArea');
        const $resultValue = $('#calcResultValue');
        const $resultCount = $('#calcResultCount');

        // Validation basique
        if (!dateDeb || !dateFin || !categorieId) {
            alert("Veuillez remplir tous les champs (Dates et Catégorie).");
            return;
        }

        // État de chargement
        $resultValue.text("Calcul en cours...");
        $resultArea.removeClass('d-none alert-success').addClass('alert-info');

        // Appel AJAX
        $.ajax({
            url: '/depense/calculate_total/',
            method: 'GET',
            data: {
                'date_debut': dateDeb,
                'date_fin': dateFin,
                'categorie_id': categorieId
            },
            success: function (response) {
                // Affichage du résultat
                $resultValue.text(response.formatted_total);

                const countText = response.count > 1 ? `${response.count} transactions` : `${response.count} transaction`;
                $resultCount.text(countText);

                $resultArea.removeClass('d-none alert-info').addClass('alert-success');
            },
            error: function (xhr) {
                console.error("Erreur calcul:", xhr);
                $resultValue.text("Erreur");
                $resultCount.text("Impossible de calculer");
                $resultArea.removeClass('d-none alert-success').addClass('alert-danger');
            }
        });
    });
});
