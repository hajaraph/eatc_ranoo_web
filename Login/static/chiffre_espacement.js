// Fonction d'animation des chiffres
function animateValue(element, start, end, duration) {
    if (!element) return;

    const startTimestamp = performance.now();
    const step = (timestamp) => {
        const elapsed = timestamp - startTimestamp;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(start + (end - start) * easeOut);

        // Formatage avec espaces pour les milliers
        element.textContent = current.toLocaleString('fr-FR');

        if (progress < 1) {
            requestAnimationFrame(step);
        }
    };

    requestAnimationFrame(step);
}

// Fonction pour initialiser toutes les animations de chiffres
function initAllChiffresAnimations() {
    // Recherche tous les éléments avec l'attribut data-animate-to
    const elementsToAnimate = document.querySelectorAll('[data-animate-to]');

    elementsToAnimate.forEach(element => {
        const targetValue = element.getAttribute('data-animate-to');
        const duration = element.getAttribute('data-duration') || 2000;
        const numericValue = parseFloat(targetValue.replace(/\s/g, '')) || 0;

        animateValue(element, 0, numericValue, parseInt(duration));
    });
}

// Initialisation automatique au chargement de la page
document.addEventListener('DOMContentLoaded', initAllChiffresAnimations);
