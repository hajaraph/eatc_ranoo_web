$(document).ready(function() {
    // Écouteur d'événement sur le changement de la sélection du numéro de client début
    $('#num_client_deb').on('change', function() {
        const numClientDeb = $(this).val();
        const $numClientFin = $('#num_client_fin');

        // Vider la liste actuelle
        $numClientFin.empty();

        if (numClientDeb) {
            // Faire un appel AJAX pour récupérer les numéros de client >= à celui sélectionné
            $.ajax({
                url: `/clients/liste/num_client_deb=${numClientDeb}`,
                method: 'GET',
                dataType: 'json',
                success: function(data) {
                    // Ajouter l'option vide par défaut
                    $numClientFin.append($('<option>', {
                        value: '',
                        text: ''
                    }));

                    // Ajouter chaque numéro de client dans la liste déroulante
                    if (data.clients && data.clients.length > 0) {
                        $.each(data.clients, function(index, client) {
                            $numClientFin.append($('<option>', {
                                value: client.client__num_client,
                                text: client.client__num_client
                            }));
                        });
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Erreur lors du chargement des numéros de client:', error);
                }
            });
        } else {
            // Si aucun numéro n'est sélectionné, vider la liste
            $numClientFin.empty().append($('<option>', {
                value: '',
                text: ''
            }));
        }
    });
});