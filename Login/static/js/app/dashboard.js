/**
 * Tableau de bord - Gestion des graphiques et de l'interface
 */

class Dashboard {
    constructor() {
        this.colorPalette = [
            '#2c3e50', '#c0392b', '#27ae60', '#666666', '#dc3545',
            '#007bff', '#2ecc71', '#343a40', '#8e44ad', '#3498db',
            '#28a745', '#f39c12', '#6c757d', '#ffc107', '#17a2b8'
        ];
        
        this.init();
    }

    /**
     * Initialisation du tableau de bord
     */
    init() {
        this.formatNumberWithSpaces();
        this.initializeCharts();
        this.setupEventListeners();
    }

    /**
     * Formatage des nombres avec séparateur de milliers
     */
    formatNumberWithSpaces() {
        const numberElements = document.querySelectorAll('.chiffre');
        numberElements.forEach(element => {
            const value = element.textContent.trim();
            if (value) {
                element.textContent = this.addThousandSeparator(value);
            }
        });
    }

    /**
     * Ajoute un séparateur de milliers
     * @param {string} number - Nombre à formater
     * @returns {string} Nombre formaté
     */
    addThousandSeparator(number) {
        const parts = number.toString().split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
        return parts.join('.');
    }

    /**
     * Initialisation des graphiques
     */
    initializeCharts() {
        if (document.getElementById('RecapConso')) {
            this.initConsumptionChart();
        }
        
        if (document.getElementById('EvoConso')) {
            this.initEvolutionChart();
        }
        
        if (document.getElementById('paiement')) {
            this.initPaymentChart();
        }
        
        if (document.getElementById('main')) {
            this.initMainCouranteChart();
        }
    }

    /**
     * Graphique de consommation par réseau
     */
    initConsumptionChart() {
        const ctx = document.getElementById('RecapConso').getContext('2d');
        const dataValues = JSON.parse(document.getElementById('recap-conso-data').textContent);
        const total = dataValues.reduce((a, b) => a + b, 0);
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: JSON.parse(document.getElementById('recap-conso-labels').textContent),
                datasets: [{
                    data: dataValues.map(value => ((value / total) * 100).toFixed(2)),
                    backgroundColor: this.colorPalette,
                    borderWidth: 1
                }]
            },
            options: this.getDoughnutOptions()
        });
    }

    /**
     * Graphique d'évolution de la consommation
     */
    initEvolutionChart() {
        const ctx = document.getElementById('EvoConso').getContext('2d');
        const datasets = JSON.parse(document.getElementById('evo-conso-data').textContent);
        
        // Assigner des couleurs uniques à chaque jeu de données
        datasets.forEach((dataset, index) => {
            dataset.borderColor = this.colorPalette[index % this.colorPalette.length];
            dataset.backgroundColor = `${this.colorPalette[index % this.colorPalette.length]}40`;
            dataset.fill = false;
            dataset.tension = 0.4;
        });
        
        new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    /**
     * Graphique des paiements
     */
    initPaymentChart() {
        const ctx = document.getElementById('paiement').getContext('2d');
        const data = JSON.parse(document.getElementById('payment-data').textContent);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Factures payées',
                    data: data.paid,
                    backgroundColor: '#28a745',
                    borderColor: '#28a745',
                    borderWidth: 1
                }, {
                    label: 'Factures impayées',
                    data: data.unpaid,
                    backgroundColor: '#e74c3c',
                    borderColor: '#e74c3c',
                    borderWidth: 1
                }]
            },
            options: this.getBarChartOptions()
        });
    }

    /**
     * Graphique des mains courantes
     */
    initMainCouranteChart() {
        const ctx = document.getElementById('main').getContext('2d');
        const data = JSON.parse(document.getElementById('main-courante-data').textContent);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Non traitée',
                    data: data.notProcessed,
                    backgroundColor: '#f39c12',
                    borderColor: '#f39c12',
                    borderWidth: 1
                }, {
                    label: 'Réalisées',
                    data: data.done,
                    backgroundColor: '#28a745',
                    borderColor: '#28a745',
                    borderWidth: 1
                }, {
                    label: 'En cours',
                    data: data.inProgress,
                    backgroundColor: '#007bff',
                    borderColor: '#007bff',
                    borderWidth: 1
                }]
            },
            options: this.getBarChartOptions()
        });
    }

    /**
     * Options communes pour les graphiques en anneau
     */
    getDoughnutOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value}%`;
                        }
                    }
                }
            },
            cutout: '70%',
            animation: {
                animateScale: true,
                animateRotate: true
            }
        };
    }

    /**
     * Options communes pour les graphiques en barres
     */
    getBarChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            animation: {
                duration: 1000
            }
        };
    }

    /**
     * Configuration des écouteurs d'événements
     */
    setupEventListeners() {
        // Rafraîchir les graphiques lors du redimensionnement de la fenêtre
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                // Les graphiques se mettent à jour automatiquement grâce à responsive: true
            }, 250);
        });
    }
}

// Initialisation du tableau de bord quand le DOM est chargé
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
