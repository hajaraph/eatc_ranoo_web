// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/marnage.js

/**
 * Charge et affiche le graphique de l'évolution du marnage.
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadMarnageParCommune(queryParams) {
    const chartId = 'marnageChart';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/marnage-par-commune/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data || !data.communes || data.communes.length === 0) {
            showError(chartId, 'Aucune donnée de marnage disponible.');
            return;
        }

        renderMarnageChart(chartId, data);

    } catch (error) {
        console.error('Erreur lors du chargement des données de marnage:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

/**
 * Rend le graphique en barres de l'évolution du marnage.
 * @param {string} elementId - ID de l'élément canvas.
 * @param {object} data - Données formatées de l'API.
 */
function renderMarnageChart(elementId, data) {
    const allTimestamps = new Set();
    data.communes.forEach(commune => {
        commune.mesures.forEach(mesure => allTimestamps.add(mesure.timestamp));
    });

    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => {
        const dateA = new Date(a.split(' ')[0].split('/').reverse().join('-') + 'T' + a.split(' ')[1]);
        const dateB = new Date(b.split(' ')[0].split('/').reverse().join('-') + 'T' + b.split(' ')[1]);
        return dateA - dateB;
    });

    const datasets = data.communes.map((commune, index) => {
        const timestampToValue = {};
        commune.mesures.forEach(mesure => {
            timestampToValue[mesure.timestamp] = mesure.valeur;
        });
        const chartData = sortedTimestamps.map(timestamp => timestampToValue[timestamp] !== undefined ? timestampToValue[timestamp] : null);

        return {
            label: commune.nom,
            data: chartData,
            backgroundColor: modernColors[index % modernColors.length],
            borderColor: modernColors[index % modernColors.length],
        };
    });

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: {
            labels: sortedTimestamps,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            if (context.parsed.y !== null) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                            }
                            return null;
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Marnage (%)' } },
                x: { title: { display: true, text: 'Date et Heure' }, grid: { display: false }, ticks: { maxRotation: 90, minRotation: 45, autoSkip: true, maxTicksLimit: 20 } }
            }
        }
    });
}
