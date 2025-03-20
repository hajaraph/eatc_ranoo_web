$(document).ready(function () {
    //Ajouter un autre champ pour le fichier
    $("#add").click(function (e){
        e.preventDefault();
        $("#afficher").append('<div></div>' +
            '<div class="col-md-4 mt-4">\n' +
            '  <div class="form-floating">\n' +
            '     <input type="file" name="piece_client" id="piece_client" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" accept="image/jpeg, image/png, application/pdf">\n' +
            '  </div>\n' +
            '</div>\n' +
            '<div class="col-md-4 mt-4">\n' +
            '  <div class="form-floating">\n' +
            '     <input type="text" name="designation" id="designation" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="">\n' +
            '     <label for="designation">Designation</label>\n' +
            '  </div>\n' +
            '</div>'
        )
    });

    const formRegion = $("#formNew #region");
    const formCommune = $("#formNew #commune");
    const formCP = $("#formNew #cp_commune");

    let allCommunes = []; // Stocker toutes les communes pour filtrage

    $("#formNew #province").on('change', function () {
        if ($(this).val()) {
            $.ajax({
                url: '/ranoo_config/nouveau/province/' + $(this).val(),
                type: 'GET',
                success: function (resp) {
                    // Remplir les régions sans option par défaut
                    let regionOption = '';
                    resp.regions.forEach(region => {
                        regionOption += `<option value="${region.region}">${region.region}</option>`;
                    });
                    formRegion.html(regionOption);

                    // Stocker toutes les communes
                    allCommunes = resp.communes;

                    // Remplir toutes les communes et codes postaux
                    let communeOption = '';
                    let cpOption = '';
                    allCommunes.forEach(commune => {
                        communeOption += `<option value="${commune.cp_commune}">${commune.commune}</option>`;
                        cpOption += `<option value="${commune.cp_commune}">${commune.cp_commune}</option>`;
                    });
                    formCommune.html(communeOption);
                    formCP.html(cpOption);

                    // Sélectionner la première région par défaut et filtrer les communes
                    const firstRegion = resp.regions[0]?.region;
                    if (firstRegion) {
                        formRegion.val(firstRegion).trigger('change');
                    }
                },
            });
        } else {
            formRegion.empty();
            formCommune.empty();
            formCP.empty();
            allCommunes = [];
        }
    });

    // Filtrer les communes quand une région change
    formRegion.on('change', function () {
        const selectedRegion = $(this).val();
        let communeOption = '';
        let cpOption = '';

        if (selectedRegion) {
            // Filtrer les communes pour la région sélectionnée
            const filteredCommunes = allCommunes.filter(commune => commune.region__region === selectedRegion);
            filteredCommunes.forEach(commune => {
                communeOption += `<option value="${commune.cp_commune}">${commune.commune}</option>`;
                cpOption += `<option value="${commune.cp_commune}">${commune.cp_commune}</option>`;
            });
        }

        formCommune.html(communeOption);
        formCP.html(cpOption);

        // Sélectionner le premier code postal par défaut si disponible
        if (formCommune.find('option').length > 0) {
            formCommune.val(formCommune.find('option:first').val()).trigger('change');
        }
    });

    // Synchroniser cp_commune quand commune change
    formCommune.on('change', function () {
        const selectedCp = $(this).val(); // Récupérer le cp_commune sélectionné
        formCP.val(selectedCp); // Mettre à jour le select cp_commune
    });
})
