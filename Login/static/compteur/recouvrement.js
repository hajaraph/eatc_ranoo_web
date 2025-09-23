$(document).ready(function() {
    // Initialiser les dates par défaut (mois courant et mois précédent)
    const today = new Date();
    const currentMonth = today.toISOString().slice(0, 7);
    
    const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const lastMonthFormatted = lastMonth.toISOString().slice(0, 7);
    
    // Récupérer les éléments une seule fois
    const $exportType = $('#recouvrementExportType');
    const $dateRangeSection = $('#recouvrementDateRangeSection');
    
    // Définir les valeurs par défaut
    $('#recouvrementStartMonth').val(lastMonthFormatted);
    $('#recouvrementEndMonth').val(currentMonth);
    
    // Fonction pour gérer la visibilité de la section des dates
    function updateDateRangeVisibility() {
        if ($exportType.val() === 'recouvrement') {
            $dateRangeSection.show();
        } else {
            $dateRangeSection.hide();
        }
    }
    
    // Gérer le changement de type d'export
    $exportType.on('change', updateDateRangeVisibility);
    
    // Initialiser l'affichage au chargement
    updateDateRangeVisibility();
    
    // Gérer le clic sur le bouton d'export
    $('#btnRecouvrementExport').on('click', function() {
        const exportType = $exportType.val();
        const startMonth = $('#recouvrementStartMonth').val();
        const endMonth = $('#recouvrementEndMonth').val();
        const numClientDeb = $('#num_client_deb').val();
        const numClientFin = $('#num_client_fin').val();

        // Construire l'URL en fonction du type d'export
        let url;
        if (exportType === 'fiche_releve') {
            // Pour les relevés, on utilise l'URL d'export des compteurs
            url = '/compteurs/exporte/compteur';
            
            // Récupérer l'ID de la commune si spécifiée
            const communeId = $('#commune').val();
            if (communeId) {
                url += `?commune=${communeId}`;
            } else {
                url += '?';
            }
        } else {
            // Pour le recouvrement, on utilise les dates au format YYYY-MM uniquement
            // startMonth et endMonth sont déjà au format YYYY-MM
            const communeId = $('#commune').val();
            
            // Construire l'URL de base avec les dates au format YYYY-MM
            url = `/compteurs/exporte/recouvrement?date_debut=${startMonth}&date_fin=${endMonth}`;
            
            // Ajouter le filtre de commune si une commune est sélectionnée
            if (communeId) {
                url += `&commune=${communeId}`;
            }
        }
        if (numClientDeb) url += `&num_client_deb=${numClientDeb}`;
        if (numClientFin) url += `&num_client_fin=${numClientFin}`;
        
        // Rediriger vers l'URL d'export
        window.location.href = url;
    });
    
    // Fonction utilitaire pour obtenir l'ID du compteur sélectionné
    function getSelectedCompteurId() {
        return $('table tbody tr:first-child td:first-child a').text().trim() || '';
    }
});
