// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/main.js

// Configurations et constantes globales
// =================================================================
const primaryColor = '#1976d2';
const successColor = '#2e7d32';
const warningColor = '#ed6c02';
const dangerColor = '#d32f2f';
const infoColor = '#0288d1';

const modernColors = [
    '#1976d2', '#2e7d32', '#0288d1', '#ed6c02', '#d32f2f',
    '#9c27b0', '#ff9800', '#4caf50', '#ef5350', '#ba68c8',
    '#343a40', '#42a5f5', '#4caf50', '#ff9800', '#ef5350'
];

// Configuration globale pour Chart.js
Chart.defaults.font.family = 'Inter';
Chart.defaults.color = '#6b7280';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 15;


// Fonctions utilitaires
// =================================================================

/**
 * Affiche une animation de chargement sur un conteneur de graphique.
 * @param {string} elementId - L'ID de l'élément canvas du graphique.
 */
function showLoading(elementId) {
    const container = document.getElementById(elementId)?.parentNode;
    if (container) {
        if (container.querySelector('.spinner-border')) return; // Évite les doublons
        container.style.position = 'relative';
        const spinner = document.createElement('div');
        spinner.className = 'd-flex justify-content-center align-items-center';
        spinner.style.cssText = 'position:absolute; top:0; left:0; width:100%; height:100%; background-color:rgba(255,255,255,0.7); z-index:10;';
        spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        container.appendChild(spinner);
    }
}

/**
 * Masque l'animation de chargement.
 * @param {string} elementId - L'ID de l'élément canvas du graphique.
 */
function hideLoading(elementId) {
    const container = document.getElementById(elementId)?.parentNode;
    const spinner = container?.querySelector('.d-flex.justify-content-center');
    if (spinner) {
        container.removeChild(spinner);
    }
}

/**
 * Affiche un message d'erreur dans un conteneur de graphique.
 * @param {string} elementId - L'ID de l'élément canvas du graphique.
 * @param {string} message - Le message d'erreur à afficher.
 */
function showError(elementId, message) {
    const container = document.getElementById(elementId)?.parentNode;
    if (container) {
        container.innerHTML = `<div class="alert alert-danger text-center d-flex align-items-center justify-content-center" style="height:100%;"><i class="fas fa-exclamation-triangle me-2"></i>${message}</div>`;
    }
}

// Orchestrateur principal
// =================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Récupérer les paramètres de l'URL pour les filtres
    const urlParams = new URLSearchParams(window.location.search);
    const queryParams = urlParams.toString();

    // Lancer le chargement de toutes les données du tableau de bord
    loadKpiData(queryParams);
    loadEvoConsoCharts(queryParams);
    loadStatutFactures(queryParams);
    loadStatutMainCourante(queryParams);
    loadFacturesParTypeClient(queryParams);
    loadConsoParTypeClient(queryParams);
    loadDebitParCommune(queryParams);
    loadMarnageParCommune(queryParams);

    // Animer les conteneurs de graphiques lorsqu'ils apparaissent à l'écran
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target); // Animer une seule fois
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.chart-card').forEach(el => observer.observe(el));
});
