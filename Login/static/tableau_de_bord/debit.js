// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/debit.js

async function loadDebitParCommune(queryParams) {
    const chartId = 'debitChart';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/debit-par-commune/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || !data.communes || data.communes.length === 0) {
            // CORRECTION : Utiliser la nouvelle fonction pour l'absence de données
            showNoDataMessage(chartId, 'Aucune donnée de débit à afficher.');
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
