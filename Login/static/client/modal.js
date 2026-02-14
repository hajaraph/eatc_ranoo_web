$(document).ready(function () {
    //Ajouter un autre champ pour le fichier
    $("#add").click(function (e) {
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

    // ===== Fonction générique pour gérer la cascade Province → Région → Commune =====
    function initCascadeFiltre(formSelector) {
        const form = $(formSelector);
        const formRegion = form.find("#region");
        const formCommune = form.find("#commune");
        const formCP = form.find("#cp_commune");

        let allCommunes = [];

        form.find("#province").on('change', function () {
            if ($(this).val()) {
                $.ajax({
                    url: '/ranoo_config/nouveau/province/' + $(this).val(),
                    type: 'GET',
                    success: function (resp) {
                        let regionOption = '';
                        resp.regions.forEach(region => {
                            regionOption += `<option value="${region.region}">${region.region}</option>`;
                        });
                        formRegion.html(regionOption);

                        allCommunes = resp.communes;

                        let communeOption = '';
                        let cpOption = '';
                        allCommunes.forEach(commune => {
                            communeOption += `<option value="${commune.cp_commune}">${commune.commune}</option>`;
                            cpOption += `<option value="${commune.cp_commune}">${commune.cp_commune}</option>`;
                        });
                        formCommune.html(communeOption);
                        formCP.html(cpOption);

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

        formRegion.on('change', function () {
            const selectedRegion = $(this).val();
            let communeOption = '';
            let cpOption = '';

            if (selectedRegion) {
                const filteredCommunes = allCommunes.filter(commune => commune.region__region === selectedRegion);
                filteredCommunes.forEach(commune => {
                    communeOption += `<option value="${commune.cp_commune}">${commune.commune}</option>`;
                    cpOption += `<option value="${commune.cp_commune}">${commune.cp_commune}</option>`;
                });
            }

            formCommune.html(communeOption);
            formCP.html(cpOption);

            if (formCommune.find('option').length > 0) {
                formCommune.val(formCommune.find('option:first').val()).trigger('change');
            }
        });

        formCommune.on('change', function () {
            const selectedCp = $(this).val();
            formCP.val(selectedCp);
        });
    }

    // Initialiser la cascade pour les modals d'export (formNew)
    initCascadeFiltre("#formNew");

    // Initialiser la cascade pour le formulaire de filtre principal
    initCascadeFiltre("#formFiltre");
})
