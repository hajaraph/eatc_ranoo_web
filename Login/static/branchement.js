$(document).ready(function() {
    // Appel AJAX pour récupérer la liste des ConfigBranchement
    $.ajax({
        url: '/ranoo_config/branchement/liste', // Ajuste l'URL selon ton projet
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            const configs = response.configs;
            const rowBranchement = $('#rowBranchement');

            // Parcourir chaque configuration et générer un input
            $.each(configs, function(index, config) {
                const inputHtml = `
                    <div class="col-md-4 col-sm-12 mt-4">
                        <div class="form-floating">
                            <input type="text" 
                                   name="prix_m3_${config.id_config_branchement}" 
                                   id="prix_m3_${config.id_config_branchement}"
                                   class="form-control shadow-none border-start-0 border-top-0 border-end-0 rounded-0" 
                                   placeholder="" 
                                   required>
                            <label for="prix_m3_${config.id_config_branchement}">
                                Prix / m³ (${config.type_client__designation_client})
                            </label>
                        </div>
                    </div>
                `;
                rowBranchement.append(inputHtml);
            });

            // Si aucune config, ajouter un message ou un input par défaut (optionnel)
            if (configs.length === 0) {
                rowBranchement.append('<p>Aucun branchement configuré.</p>');
            }

            // Ajouter un filtre pour n'accepter que les chiffres et un point décimal
           $('input[name^="prix_m3_"]').on('input', function() {
                const champ = $(this); // Référence à l'input actuel
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

                champ.val(numericValue); // Met à jour la valeur
            });
        },
        error: function(xhr, status, error) {
            console.error('Erreur AJAX :', error);
            $('#rowBranchement').append('<p>Erreur lors du chargement des configurations.</p>');
        }
    });
});