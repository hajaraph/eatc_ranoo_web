// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/kpi.js

/**
 * Formate un nombre en ajoutant des espaces comme séparateurs de milliers.
 * @param {number} number - Le nombre à formater.
 */
function formatNumberWithSpaces(number) {
    if (number === null || number === undefined) return '0';
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/**
 * Charge et affiche les indicateurs de performance clés (KPIs).
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadKpiData(queryParams) {
    const kpiContainer = document.getElementById('kpi-container');
    if (!kpiContainer) return;

    kpiContainer.querySelectorAll('.stats-value').forEach(el => {
        el.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">...</span></div>';
    });

    try {
        const response = await fetch(`/tableau_bord/api/kpi-globaux/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        updateKpiElement('kpi-chiffres', data.chiffres, (val) => `${formatNumberWithSpaces(val)}`);
        updateKpiElement('kpi-clients-actuelle', data.nb_client_actuelle);
        updateKpiElement('kpi-clients-prec', data.nb_client_prec);
        
        const anneePrecEl = document.getElementById('kpi-annee-prec');
        if(anneePrecEl) anneePrecEl.textContent = data.annee_contrat_prec;

        const anneeActuelleEl = document.getElementById('kpi-annee-actuelle');
        if(anneeActuelleEl) anneeActuelleEl.textContent = data.annee_contrat_actuelle || new Date().getFullYear();

    } catch (error) {
        console.error('Erreur lors du chargement des KPIs:', error);
        kpiContainer.querySelectorAll('.stats-value').forEach(el => {
            el.innerHTML = '<span class="text-sm text-danger">Erreur</span>';
        });
    }
}

/**
 * Met à jour la valeur d'un élément KPI avec une animation.
 * @param {string} elementId - L'ID de l'élément HTML à mettre à jour.
 * @param {number} endValue - La valeur finale à afficher.
 * @param {function} formatter - Fonction optionnelle pour formater la valeur.
 */
function updateKpiElement(elementId, endValue, formatter) {
    const element = document.getElementById(elementId);
    if (element) {
        const finalFormatter = typeof formatter === 'function' 
            ? formatter 
            : val => formatNumberWithSpaces(val);

        const finalEndValue = Number(endValue) || 0;

        animateValue(element, 0, finalEndValue, 1500, finalFormatter);
    }
}

/**
 * Anime la transition d'une valeur numérique.
 * @param {HTMLElement} element - L'élément HTML à mettre à jour.
 * @param {number} start - La valeur de départ.
 * @param {number} end - La valeur de fin.
 * @param {number} duration - La durée de l'animation en ms.
 * @param {function} formatter - La fonction de formatage.
 */
function animateValue(element, start, end, duration, formatter) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const current = Math.floor(progress * (end - start) + start);
        
        element.textContent = formatter(current);
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
