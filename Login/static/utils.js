// Fonctions utilitaires communes

/**
 * Formate un champ pour n'accepter que des nombres avec un point décimal optionnel
 * @param {jQuery} champ - L'élément jQuery à formater
 */
function formaterNombreDecimal(champ) {
    const inputValue = champ.val();
    let numericValue = inputValue.replace(/,/g, '.'); // Remplace virgule par point
    numericValue = numericValue.replace(/[^\d.]/g, ''); // Supprime tout sauf chiffres et point

    // Si la saisie commence par un point, le supprimer
    if (numericValue.startsWith('.')) {
        numericValue = numericValue.replace('.', '');
    }

    // Limiter à un seul point décimal
    const parts = numericValue.split('.');
    if (parts.length > 2) {
        numericValue = parts[0] + '.' + parts.slice(1).join('');
    }

    champ.val(numericValue);
}

/**
 * Formate un champ pour n'accepter que des chiffres (entiers)
 * @param {jQuery} champ - L'élément jQuery à formater
 * @param {number} maxLength - Longueur maximale (optionnelle)
 */
function formaterNombreEntier(champ, maxLength = null) {
    let numericValue = champ.val().replace(/\D/g, '');
    
    if (maxLength !== null) {
        numericValue = numericValue.slice(0, maxLength);
    }
    
    champ.val(numericValue);
}

// Export des fonctions pour utilisation dans d'autres fichiers
if (typeof module !== 'undefined' && module.exports) {
    // Pour les tests Node.js
    module.exports = { formaterNombreDecimal, formaterNombreEntier };
}
