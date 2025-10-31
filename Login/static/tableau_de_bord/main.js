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

function showLoading(elementId) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    const container = canvas.parentNode;
    if (container) {
        if (container.querySelector('.chart-overlay')) return;
        container.style.position = 'relative';
        const overlay = document.createElement('div');
        overlay.className = 'chart-overlay d-flex justify-content-center align-items-center';
        overlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        container.appendChild(overlay);
    }
}

function hideLoading(elementId) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    const container = canvas.parentNode;
    const overlay = container?.querySelector('.chart-overlay');
    if (overlay) {
        container.removeChild(overlay);
    }
}

function showError(elementId, message) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    const container = canvas.parentNode;
    if (container) {
        container.innerHTML = ''; 
        container.style.position = 'relative';
        container.style.display = 'flex';
        container.style.justifyContent = 'center';
        container.style.alignItems = 'center';
        container.style.minHeight = '250px';

        const errorContent = document.createElement('div');
        errorContent.className = 'text-center text-muted';
        errorContent.innerHTML = `
            <div style="font-size: 2.5rem; color: ${dangerColor}; opacity: 0.6;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <p class="mt-2 mb-0" style="font-weight: 500;">Erreur de chargement</p>
            <small>${message}</small>
        `;
        container.appendChild(errorContent);
    }
}

/**
 * Affiche un message stylisé pour l'absence de données.
 * @param {string} elementId - L'ID de l'élément canvas du graphique.
 * @param {string} message - Le message à afficher.
 */
function showNoDataMessage(elementId, message) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    const container = canvas.parentNode;
    if (container) {
        container.innerHTML = '';
        container.style.position = 'relative';
        container.style.display = 'flex';
        container.style.justifyContent = 'center';
        container.style.alignItems = 'center';
        container.style.minHeight = '250px';

        const noDataContent = document.createElement('div');
        noDataContent.className = 'text-center text-muted';
        noDataContent.innerHTML = `
            <div style="font-size: 2.5rem; opacity: 0.5;">
                <i class="fas fa-info-circle"></i>
            </div>
            <p class="mt-2 mb-0" style="font-weight: 500;">Aucune donnée</p>
            <small>${message}</small>
        `;
        container.appendChild(noDataContent);
    }
}

// Orchestrateur principal
// =================================================================
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const queryParams = urlParams.toString();

    loadKpiData(queryParams);
    loadEvoConsoCharts(queryParams);
    loadStatutFactures(queryParams);
    loadStatutMainCourante(queryParams);
    loadFacturesParTypeClient(queryParams);
    loadConsoParTypeClient(queryParams);
    loadDebitParCommune(queryParams);
    loadMarnageParCommune(queryParams);

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.chart-card').forEach(el => observer.observe(el));
});
