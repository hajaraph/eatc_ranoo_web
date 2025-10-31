// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/conso_par_type_client.js

/**
 * Charge et affiche le graphique de la consommation par type de client.
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadConsoParTypeClient(queryParams) {
    const chartId = 'typeClientConso';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/conso-par-type-client/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            showError(chartId, 'Aucune donnée de consommation par type de client disponible.');
            return;
        }

        renderConsoParTypeClientChart(chartId, data);

    } catch (error) {
        console.error('Erreur lors du chargement de la consommation par type de client:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

/**
 * Rend le graphique en barres de la consommation par type de client.
 * @param {string} elementId - ID de l'élément canvas.
 * @param {object[]} data - Données brutes de l'API.
 */
function renderConsoParTypeClientChart(elementId, data) {
    const dataByMonth = {};
    const totalsByMonth = {};
    const typesClient = new Set();

    // Préparer les données
    data.forEach(item => {
        const monthKey = `${String(item.mois).padStart(2, '0')}/${item.annee}`;
        const typeClient = item.designation_client;
        const consommation = item.conso_mensuelle || 0;

        if (!dataByMonth[monthKey]) {
            dataByMonth[monthKey] = {};
            totalsByMonth[monthKey] = 0;
        }
        dataByMonth[monthKey][typeClient] = consommation;
        totalsByMonth[monthKey] += consommation;
        typesClient.add(typeClient);
    });

    const labels = Object.keys(dataByMonth).sort((a, b) => {
        const [monthA, yearA] = a.split('/').map(Number);
        const [monthB, yearB] = b.split('/').map(Number);
        return (yearA * 12 + monthA) - (yearB * 12 + monthB);
    });

    const sortedTypesClient = Array.from(typesClient).sort();
    const datasets = sortedTypesClient.map((typeClient, index) => {
        const datasetData = labels.map(monthKey => dataByMonth[monthKey][typeClient] || 0);
        return {
            label: typeClient,
            backgroundColor: modernColors[index % modernColors.length],
            borderColor: modernColors[index % modernColors.length],
            borderWidth: 2,
            borderRadius: 6,
            data: datasetData,
            hoverBackgroundColor: modernColors[index % modernColors.length] + 'dd',
            hoverBorderWidth: 3
        };
    });

    // Créer le graphique
    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    beginAtZero: true,
                    stacked: false,
                    title: { display: true, text: 'Consommation (m³)', font: { weight: '600', size: 12 } },
                    grid: { color: '#f1f5f9' },
                    ticks: {
                        font: { size: 11 },
                        callback: (value) => value.toLocaleString('fr-FR') + ' m³'
                    }
                },
                x: {
                    stacked: false,
                    title: { display: true, text: 'Période (Mois/Année)', font: { weight: '600', size: 12 } },
                    grid: { display: false },
                    ticks: { font: { size: 11 } }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, padding: 15, font: { size: 12, weight: '500' } }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: primaryColor,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        title: (context) => 'Période: ' + context[0].label,
                        label: (context) => {
                            const value = context.parsed.y;
                            return context.dataset.label + ': ' + value.toLocaleString('fr-FR') + ' m³';
                        },
                        afterBody: (context) => {
                            const monthKey = context[0].label;
                            const total = totalsByMonth[monthKey] || 0;
                            return ['---', 'Total du mois: ' + total.toLocaleString('fr-FR') + ' m³'];
                        }
                    }
                }
            }
        }
    });
}
