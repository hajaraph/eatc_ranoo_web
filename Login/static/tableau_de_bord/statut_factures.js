// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/statut_factures.js

async function loadStatutFactures(queryParams) {
    const chartId = 'paiement';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/statut-factures/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            // CORRECTION : Utiliser la nouvelle fonction pour l'absence de données
            showNoDataMessage(chartId, 'Aucune donnée de facturation à afficher.');
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
