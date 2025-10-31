// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/statut_factures.js

/**
 * Charge et affiche le graphique de l'état des factures (payées/impayées).
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadStatutFactures(queryParams) {
    const chartId = 'paiement';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/statut-factures/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data || data.length === 0) {
            showError(chartId, 'Aucune donnée de facturation disponible.');
            return;
        }

        const labels = data.map(item => `${String(item.mois).padStart(2, '0')}/${item.annee}`);
        const payeesData = data.map(item => item.nombre_factures_payees);
        const impayeesData = data.map(item => item.nombre_factures_impayees);

        renderStatutFacturesChart(chartId, labels, payeesData, impayeesData);

    } catch (error) {
        console.error('Erreur lors du chargement du statut des factures:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

/**
 * Rend le graphique en barres du statut des factures.
 * @param {string} elementId - ID de l'élément canvas.
 * @param {string[]} labels - Labels pour l'axe X.
 * @param {number[]} payeesData - Données pour les factures payées.
 * @param {number[]} impayeesData - Données pour les factures impayées.
 */
function renderStatutFacturesChart(elementId, labels, payeesData, impayeesData) {
    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Factures payées',
                    backgroundColor: successColor,
                    borderRadius: 6,
                    data: payeesData
                },
                {
                    label: 'Factures impayées',
                    backgroundColor: dangerColor,
                    borderRadius: 6,
                    data: impayeesData
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
