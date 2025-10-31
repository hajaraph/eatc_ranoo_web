// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/factures_par_type_client.js

async function loadFacturesParTypeClient(queryParams) {
    const chartId = 'facturesParTypeClient';
    showLoading(chartId);

    try {
        const response = await fetch(`/tableau_bord/api/factures-par-type-client/?${queryParams}`);
        if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
        const data = await response.json();

        if (!data || data.length === 0) {
            // CORRECTION : Utiliser la nouvelle fonction pour l'absence de données
            showNoDataMessage(chartId, 'Aucune donnée de paiement à afficher.');
            return;
        }

        renderFacturesParTypeClientChart(chartId, data);

    } catch (error) {
        console.error('Erreur lors du chargement des factures par type de client:', error);
        showError(chartId, 'Impossible de charger les données.');
    } finally {
        hideLoading(chartId);
    }
}

function renderFacturesParTypeClientChart(elementId, apiData) {
    const facturesData = {
        labels: apiData.map(f => `${f.commune_nom} - ${f.type_client} - ${String(f.mois).padStart(2, '0')}/${f.annee}`),
        payees: apiData.map(f => f.payees || 0),
        impayees: apiData.map(f => f.impayees || 0),
        montantTotal: apiData.map(f => f.montant_total || 0),
        montantPaye: apiData.map(f => f.montant_paye || 0),
        volumePaye: apiData.map(f => f.volume_paye || 0),
        volumeImpaye: apiData.map(f => f.volume_impaye || 0),
        montantTotalPayees: apiData.map(f => f.montant_total_payees || 0),
        montantTotalImpayees: apiData.map(f => f.montant_total_impayees || 0),
    };

    new Chart(document.getElementById(elementId).getContext('2d'), {
        type: 'bar',
        data: {
            labels: facturesData.labels,
            datasets: [
                {
                    label: 'Factures payées',
                    data: facturesData.payees,
                    backgroundColor: successColor,
                    stack: 'Stack 0',
                },
                {
                    label: 'Factures impayées',
                    data: facturesData.impayees,
                    backgroundColor: dangerColor,
                    stack: 'Stack 0',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false },
                    ticks: { maxRotation: 90, minRotation: 45, font: { size: 11 }, autoSkip: false },
                    title: { display: true, text: 'Commune - Type de Branchement - Période', font: { weight: '600', size: 12 } }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' },
                    ticks: { stepSize: 1, font: { size: 11 } },
                    title: { display: true, text: 'Nombre de factures', font: { weight: '600', size: 12 } }
                }
            },
            interaction: { mode: 'index', intersect: false },
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
                        title: (context) => context[0].label,
                        label: (context) => {
                            const value = context.parsed.y;
                            return `${context.dataset.label}: ${value} facture${value > 1 ? 's' : ''}`;
                        },
                        afterLabel: (context) => {
                            const index = context.dataIndex;
                            const total = facturesData.payees[index] + facturesData.impayees[index];
                            const percentage = total > 0 ? Math.round((context.parsed.y / total) * 100) : 0;
                            let tooltipText = [`${percentage}% du total (${total} factures)`];

                            const montantTotal = facturesData.montantTotal[index];
                            const montantPaye = facturesData.montantPaye[index];
                            const tauxPaiement = montantTotal > 0 ? Math.round((montantPaye / montantTotal) * 100) : 0;

                            const volumePaye = facturesData.volumePaye[index];
                            const volumeImpaye = facturesData.volumeImpaye[index];
                            const volumeTotal = volumePaye + volumeImpaye;

                            if (context.datasetIndex === 0) {
                                const montantPayees = facturesData.montantTotalPayees[index];
                                tooltipText.push(`💰 Montant factures payées: ${montantPayees.toLocaleString('fr-FR')} AR`);
                                tooltipText.push(`💧 Volume payé: ${volumePaye.toLocaleString('fr-FR')} m³`);
                            } else {
                                const montantImpayees = facturesData.montantTotalImpayees[index];
                                tooltipText.push(`💰 Montant factures impayées: ${montantImpayees.toLocaleString('fr-FR')} AR`);
                                tooltipText.push(`💧 Volume impayé: ${volumeImpaye.toLocaleString('fr-FR')} m³`);
                            }

                            tooltipText.push(`💧 Volume total: ${volumeTotal.toLocaleString('fr-FR')} m³`);
                            tooltipText.push(`📊 Taux de recouvrement: ${tauxPaiement}%`);

                            return tooltipText;
                        }
                    }
                }
            }
        }
    });
}
