// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/statut_main_courante.js

/**
 * Charge et affiche le graphique de l'état des mains courantes.
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadStatutMainCourante(queryParams) {
    const chartId = 'main';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/statut-main-courante/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data || data.length === 0) {
            showError(chartId, 'Aucune donnée de main courante disponible.');
            return;
        }

        const labels = data.map(item => `${String(item.mois).padStart(2, '0')}/${item.annee}`);
        const nonTraiteData = data.map(item => item.nb_non_traite);
        const realiseData = data.map(item => item.nb_realise);
        const enCoursData = data.map(item => item.nb_en_cours);

        renderStatutMainCouranteChart(chartId, labels, nonTraiteData, realiseData, enCoursData);

    } catch (error) {
        console.error('Erreur lors du chargement du statut des mains courantes:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

/**
 * Rend le graphique en barres du statut des mains courantes.
 * @param {string} elementId - ID de l'élément canvas.
 * @param {string[]} labels - Labels pour l'axe X.
 * @param {number[]} nonTraiteData - Données pour les MC non traitées.
 * @param {number[]} realiseData - Données pour les MC réalisées.
 * @param {number[]} enCoursData - Données pour les MC en cours.
 */
function renderStatutMainCouranteChart(elementId, labels, nonTraiteData, realiseData, enCoursData) {
    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Non traitées',
                    backgroundColor: warningColor,
                    borderRadius: 6,
                    data: nonTraiteData
                },
                {
                    label: 'Réalisées',
                    backgroundColor: successColor,
                    borderRadius: 6,
                    data: realiseData
                },
                {
                    label: 'En cours',
                    backgroundColor: infoColor,
                    borderRadius: 6,
                    data: enCoursData
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true }, x: { grid: { display: false } } },
            plugins: { legend: { position: 'top' } }
        }
    });
}
