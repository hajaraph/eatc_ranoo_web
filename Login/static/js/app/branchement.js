// Import des fonctions utilitaires
const { formaterNombreDecimal } = window.utils || {};

$(document).ready(function() {
    // Appel AJAX pour récupérer la liste des ConfigBranchement
    $.ajax({
        url: '/ranoo_config/branchement/liste',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            const configs = response.configs;
            const rowBranchement = $('#rowBranchement');

            // Parcourir chaque configuration et générer un input
            $.each(configs, function(index, config) {
                const inputId = `prix_m3_${config.id_config_branchement}`;
                const inputHtml = `
                    <div class="col-md-4 col-sm-12 mt-4">
                        <div class="form-floating">
                            <input type="text" 
                                   name="${inputId}" 
                                   id="${inputId}"
                                   class="form-control shadow-none border-start-0 border-top-0 border-end-0 rounded-0 prix-m3" 
                                   placeholder="" 
                                   required>
                            <label for="${inputId}">
                                Prix / m³ (${config.type_client__designation_client || 'N/A'})*
                            </label>
                        </div>
                    </div>
                `;
                rowBranchement.append(inputHtml);
            });

            // Si aucune config, ajouter un message
            if (configs.length === 0) {
                rowBranchement.append('<p class="text-muted">Aucun branchement configuré.</p>');
            } else {
                // Configurer la validation pour les champs de prix
                $('.prix-m3').on('input', function() {
                    formaterNombreDecimal($(this));
                }).trigger('input');
            }
        },
        error: function(xhr, status, error) {
            console.error('Erreur AJAX :', error);
            $('#rowBranchement').append(
                '<div class="alert alert-danger">Erreur lors du chargement des configurations de branchement.</div>'
            );
        }
    });
});
