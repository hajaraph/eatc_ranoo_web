// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/debit.js

/**
 * Charge et affiche le graphique de l'évolution du débit.
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadDebitParCommune(queryParams) {
    const chartId = 'debitChart';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/debit-par-commune/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data || !data.communes || data.communes.length === 0) {
            showError(chartId, 'Aucune donnée de débit disponible.');
            return;
        }

        renderDebitChart(chartId, data);

    } catch (error) {
        console.error('Erreur lors du chargement des données de débit:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

/**
 * Rend le graphique en ligne de l'évolution du débit.
 * @param {string} elementId - ID de l'élément canvas.
 * @param {object} data - Données formatées de l'API.
 */
function renderDebitChart(elementId, data) {
    const datasets = data.communes.map((commune, index) => ({
        label: commune.nom,
        data: commune.valeurs,
        borderColor: modernColors[index % modernColors.length],
        backgroundColor: modernColors[index % modernColors.length] + '1A',
        borderWidth: 2,
        tension: 0.3,
        fill: false,
    }));

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'line',
        data: {
            labels: data.periodes || [],
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
                        label: (context) => `${context.dataset.label}: ${context.raw.toLocaleString()} Litre/Sec`
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Débit (Litre/Sec)' } },
                x: { title: { display: true, text: 'Période (Mois/Année)' }, grid: { display: false } }
            }
        }
    });
}
