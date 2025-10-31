// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/evo_conso_charts.js

async function loadEvoConsoCharts(queryParams) {
    const recapChartId = 'RecapConso';
    const evoChartId = 'EvoConso';

    showLoading(recapChartId);
    showLoading(evoChartId);

    try {
        const response = await fetch(`/tableau_bord/api/evo-conso-commune/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            // CORRECTION : Utiliser la nouvelle fonction pour l'absence de données
            showNoDataMessage(recapChartId, 'Aucune donnée de consommation à afficher.');
            showNoDataMessage(evoChartId, 'Aucune donnée de consommation à afficher.');
            return;
        }

        const recapLabels = data.map(item => item.commune);
        const recapData = data.map(item => item.data.reduce((sum, current) => sum + current.total_conso, 0));

        renderRecapChart(recapChartId, recapLabels, recapData);
        renderEvoChart(evoChartId, data);

    } catch (error) {
        console.error('Erreur lors du chargement des données de consommation:', error);
        showError(recapChartId, 'Impossible de charger les données.');
        showError(evoChartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(recapChartId);
        hideLoading(evoChartId);
    }
}

function renderRecapChart(elementId, labels, data) {
    const total = data.reduce((a, b) => a + b, 0);
    const percentageValues = data.map(value => ((value / total) * 100).toFixed(1));

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Consommation par Réseaux',
                data: percentageValues,
                backgroundColor: modernColors,
                borderWidth: 0,
                hoverBorderWidth: 3,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 20, font: { size: 12, weight: '500' } } },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    callbacks: { label: (context) => `${context.label}: ${context.parsed}%` }
                }
            },
            cutout: '60%'
        }
    });
}

function renderEvoChart(elementId, data) {
    const datasets = data.map((row, index) => ({
        label: row.commune,
        data: row.data.map(list => ({
            x: `${String(list.mois_releve).padStart(2, '0')}/${list.annee_releve}`,
            y: list.total_conso
        })),
        backgroundColor: modernColors[index % modernColors.length] + '20',
        borderColor: modernColors[index % modernColors.length],
        borderWidth: 3,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: modernColors[index % modernColors.length],
        pointRadius: 6,
    }));

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: { y: { beginAtZero: true }, x: {} },
            plugins: { legend: { position: 'top' } }
        }
    });
}
