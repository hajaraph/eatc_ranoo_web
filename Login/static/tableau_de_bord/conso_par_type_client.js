// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/conso_par_type_client.js

async function loadConsoParTypeClient(queryParams) {
    const chartId = 'typeClientConso';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/conso-par-type-client/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            // CORRECTION : Utiliser la nouvelle fonction pour l'absence de données
            showNoDataMessage(chartId, 'Aucune donnée de consommation à afficher.');
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

function renderConsoParTypeClientChart(elementId, data) {
    const dataByGroup = {};
    const totalsByGroup = {};
    const typesClient = new Set();

    data.forEach(item => {
        const groupKey = `${item.commune_nom} - ${String(item.mois).padStart(2, '0')}/${item.annee}`;
        const typeClient = item.designation_client;
        const consommation = item.conso_mensuelle || 0;

        if (!dataByGroup[groupKey]) {
            dataByGroup[groupKey] = {};
            totalsByGroup[groupKey] = 0;
        }
        dataByGroup[groupKey][typeClient] = consommation;
        totalsByGroup[groupKey] += consommation;
        typesClient.add(typeClient);
    });

    const labels = Object.keys(dataByGroup).sort((a, b) => {
        const [communeA, dateA] = a.split(' - ');
        const [communeB, dateB] = b.split(' - ');
        if (communeA !== communeB) return communeA.localeCompare(communeB);
        const [monthA, yearA] = dateA.split('/').map(Number);
        const [monthB, yearB] = dateB.split('/').map(Number);
        return (yearA * 12 + monthA) - (yearB * 12 + monthB);
    });

    const sortedTypesClient = Array.from(typesClient).sort();
    const datasets = sortedTypesClient.map((typeClient, index) => {
        const datasetData = labels.map(groupKey => dataByGroup[groupKey][typeClient] || 0);
        return {
            label: typeClient,
            backgroundColor: modernColors[index % modernColors.length],
            data: datasetData,
        };
    });

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: { display: true, text: 'Consommation (m³)' }
                },
                x: {
                    stacked: true,
                    grid: { display: false },
                    title: { display: true, text: 'Commune - Période' },
                    ticks: { maxRotation: 90, minRotation: 45, autoSkip: false },
                }
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        title: (context) => 'Période: ' + context[0].label,
                        label: (context) => {
                            const value = context.parsed.y;
                            return context.dataset.label + ': ' + value.toLocaleString('fr-FR') + ' m³';
                        },
                        afterBody: (context) => {
                            const groupKey = context[0].label;
                            const total = totalsByGroup[groupKey] || 0;
                            return ['---', 'Total du groupe: ' + total.toLocaleString('fr-FR') + ' m³'];
                        }
                    }
                }
            }
        }
    });
}
