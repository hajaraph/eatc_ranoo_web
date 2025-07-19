$(document).ready(function(){
    $('#myTable').DataTable({
        searching: true,
        "order": [],
        language: {
            url: '/static/fr-FR.json',
        },
    });
    $('.dataTables_filter input[type="search"]').css('height', '500px');
    // Hide automatique le message après quelque seconde
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
    let champ = $('#paiement, #tva, #taux_taxe, #num_compteur')

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

    $('#confirmer-export-client-excel').click(function() {
        const commune = $('#commune').val();
        // Construire l'URL avec les paramètres GET
        let url = '/clients/excel';
        url += `?commune=${commune}`;
        // Ouvrir une nouvelle onglet avec l'URL générée
        window.open(url, '_blank');
        $('#export-client-excel').modal('hide');
    });

    $('#confirmer-exportmc-excel').click(function() {
        const date_deb = $('#date_deb').val();
        const date_fin = $('#date_fin').val();
        const statut = $('#statut').val();
        // Construire l'URL avec les paramètres GET
        let url = '/main_courante/excel';
        url += `?date_deb=${date_deb}&date_fin=${date_fin}&statut=${statut}`;
        // Ouvrir une nouvelle onglet avec l'URL générée
        window.open(url, '_blank');
        $('#exportmc-excel').modal('hide');
    });

    // Gestion du changement de région dans le modal de facture (export PDF)
    $('#export-pdf #region').on('change', function() {
        const regionName = $(this).val();
        const communeSelect = $('#export-pdf #commune');

        // Vider la liste des communes
        communeSelect.empty();
        communeSelect.append('<option value="" selected hidden></option>');

        if (regionName) {
            // Faire une requête AJAX pour récupérer les communes de cette région
            $.ajax({
                url: `/commune/region/${regionName}`,
                type: 'GET',
                success: function(data) {
                    if (data.communes && data.communes.length > 0) {
                        data.communes.forEach(function(commune) {
                            communeSelect.append(`<option value="${commune.cp_commune}">${commune.commune}</option>`);
                        });
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Erreur lors du chargement des communes:', error);
                }
            });
        }
    });

    // Gestion du changement de région dans le modal de facture (export Excel)
    $('#export-excel #region').on('change', function() {
        const regionName = $(this).val();
        const communeSelect = $('#export-excel #commune');

        // Vider la liste des communes
        communeSelect.empty();
        communeSelect.append('<option value="" selected hidden></option>');

        if (regionName) {
            // Faire une requête AJAX pour récupérer les communes de cette région
            $.ajax({
                url: `/commune/region/${regionName}`,
                type: 'GET',
                success: function(data) {
                    if (data.communes && data.communes.length > 0) {
                        data.communes.forEach(function(commune) {
                            communeSelect.append(`<option value="${commune.cp_commune}">${commune.commune}</option>`);
                        });
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Erreur lors du chargement des communes:', error);
                }
            });
        }
    });

    // Gestion du bouton de confirmation pour l'export PDF
    $('#confirmer-export').click(function() {
        const date_deb = $('#export-pdf #date_deb').val();
        const date_fin = $('#export-pdf #date_fin').val();
        const commune = $('#export-pdf #commune').val();

        // Construire l'URL avec les paramètres GET
        let url = '/facturation/pdf';
        const params = [];
        if (date_deb) params.push(`date_deb=${date_deb}`);
        if (date_fin) params.push(`date_fin=${date_fin}`);
        if (commune) params.push(`commune=${commune}`);

        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        // Ouvrir une nouvelle onglet avec l'URL générée
        window.open(url, '_blank');
        $('#export-pdf').modal('hide');
    });

    // Gestion du bouton de confirmation pour l'export Excel
    $('#confirmer-export-excel').click(function() {
        const date_deb = $('#export-excel #date_deb').val();
        const date_fin = $('#export-excel #date_fin').val();
        const commune = $('#export-excel #commune').val();

        // Construire l'URL avec les paramètres GET
        let url = '/facturation/excel';
        const params = [];
        if (date_deb) params.push(`date_deb=${date_deb}`);
        if (date_fin) params.push(`date_fin=${date_fin}`);
        if (commune) params.push(`commune=${commune}`);

        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        // Ouvrir une nouvelle onglet avec l'URL générée
        window.open(url, '_blank');
        $('#export-excel').modal('hide');
    });
});