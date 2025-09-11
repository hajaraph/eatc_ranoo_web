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
        
        // Validation des dates pour le recouvrement
        if (exportType === 'recouvrement') {
            if (!startMonth || !endMonth) {
                alert('Veuillez sélectionner une plage de dates valide pour le recouvrement.');
                return;
            }
            
            if (startMonth > endMonth) {
                alert('La date de début doit être antérieure à la date de fin.');
                return;
            }
        }
        
        // Construire l'URL en fonction du type d'export
        let url;
        if (exportType === 'fiche_releve') {
            // Pour les relevés, on utilise l'URL d'export des compteurs
            url = '/compteurs/exporte/compteur';
            
            // Récupérer l'ID de la commune si spécifiée
            const communeId = $('#commune').val();
            if (communeId) {
                url += `?commune=${communeId}`;
            }
        } else {
            // Pour le recouvrement, on utilise les dates au format YYYY-MM et la commune
            const startDate = startMonth + '-01';
            const endDate = endMonth + '-01';
            const communeId = $('#commune').val();
            
            // Construire l'URL de base
            url = `/compteurs/exporte/recouvrement?date_debut=${startDate}&date_fin=${endDate}`;
            
            // Ajouter le filtre de commune si une commune est sélectionnée
            if (communeId) {
                url += `&commune=${communeId}`;
            }
        }
        
        // Rediriger vers l'URL d'export
        window.location.href = url;
    });
    
    // Fonction utilitaire pour obtenir l'ID du compteur sélectionné
    function getSelectedCompteurId() {
        return $('table tbody tr:first-child td:first-child a').text().trim() || '';
    }
});
