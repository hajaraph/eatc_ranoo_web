// Login/static/utils_blocage_date_precedant.js

/**
 * Configure la validation des dates entre deux champs de formulaire
 * @param {string} debutId - ID du champ de date de début
 * @param {string} finId - ID du champ de date de fin
 */
function setupDateValidation(debutId, finId) {
    const dateDebutInput = document.getElementById(debutId);
    const dateFinInput = document.getElementById(finId);

    if (!dateDebutInput || !dateFinInput) return;

    // Configuration initiale
    if (dateDebutInput.value) {
        dateFinInput.min = dateDebutInput.value;
    }

    // Mettre à jour la date minimale de fin quand la date de début change
    dateDebutInput.addEventListener('change', function() {
        if (!this.value) return;
        
        // Mettre à jour l'attribut min de la date de fin
        dateFinInput.min = this.value;
        
        // Si la date de fin est antérieure à la nouvelle date de début
        if (dateFinInput.value && new Date(dateFinInput.value) < new Date(this.value)) {
            dateFinInput.value = this.value;
        }
    });

    // Validation supplémentaire au moment de la soumission
    const form = dateDebutInput.closest('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (dateDebutInput.value && dateFinInput.value) {
                const dateDebut = new Date(dateDebutInput.value);
                const dateFin = new Date(dateFinInput.value);
                
                if (dateFin < dateDebut) {
                    e.preventDefault();
                    alert('La date de fin ne peut pas être antérieure à la date de début');
                    dateFinInput.focus();
                }
            }
        });
    }
}

// Configuration au chargement du DOM
document.addEventListener('DOMContentLoaded', function() {
    // Configuration pour le formulaire principal
    setupDateValidation('datedeb', 'datefin');
    
    // Configuration pour le formulaire d'export
    setupDateValidation('date_deb', 'date_fin');

    // configuration pour le export recouvrement
    setupDateValidation('recouvrementStartMonth', 'recouvrementEndMonth');
});