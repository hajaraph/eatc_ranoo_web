// Fichier: D:/ProjetReleverCompteur/eatc_web/Login/static/tableau_de_bord/kpi.js

/**
 * Formate un nombre en ajoutant des espaces comme séparateurs de milliers.
 * @param {number} number - Le nombre à formater.
 */
function formatNumberWithSpaces(number) {
    if (number === null || number === undefined) return '0';
    const isNegative = number < 0;
    const absNumber = Math.abs(number);
    const formattedNumber = absNumber.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return isNegative ? '-' + formattedNumber : formattedNumber;
}

/**
 * Charge et affiche les indicateurs de performance clés (KPIs).
 * @param {string} queryParams - Les paramètres de requête pour le filtrage.
 */
async function loadKpiData(queryParams) {
    const kpiContainer = document.getElementById('kpi-container');
    if (!kpiContainer) return;

    kpiContainer.querySelectorAll('.stats-value, strong').forEach(el => {
        el.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">...</span></div>';
    });

    try {
        const response = await fetch(`/tableau_bord/api/kpi-globaux/?${queryParams}`);
        if (!response.ok) {
            throw new Error(`Erreur HTTP ${response.status}`);
        }
        const data = await response.json();

        // Carte 1: Résultat Net
        updateKpiElement('kpi-resultat-net', data.resultat_net, val => `${formatNumberWithSpaces(val)} Ar`);
        updateKpiElement('kpi-total-recettes', data.total_recettes, val => `${formatNumberWithSpaces(val)} Ar`);
        updateKpiElement('kpi-total-depenses', data.total_depenses, val => `${formatNumberWithSpaces(val)} Ar`);
        updateResultatNetCard(data.resultat_net);

        // Carte 2: Chiffre d'Affaires
        updateKpiElement('kpi-chiffres', data.chiffres, val => `${formatNumberWithSpaces(val)} Ar`);

        // Carte 3: Évolution des Abonnés
        updateKpiElement('kpi-clients-actuelle', data.nb_client_actuelle);
        updateEvolutionAbonnesCard(data.nb_client_actuelle, data.nb_client_prec, data.annee_contrat_prec);

    } catch (error) {
        console.error('Erreur lors du chargement des KPIs:', error);
        kpiContainer.querySelectorAll('.stats-value, strong').forEach(el => {
            el.innerHTML = '<span class="text-sm text-danger">Erreur</span>';
        });
    }
}

/**
 * Met à jour la couleur de la carte "Résultat Net" en fonction de sa valeur.
 * @param {number} resultatNet - La valeur du résultat net.
 */
function updateResultatNetCard(resultatNet) {
    const card = document.getElementById('resultat-net-card');
    const icon = document.getElementById('resultat-net-icon');
    if (!card || !icon) return;

    card.classList.remove('success', 'danger', 'primary');
    icon.classList.remove('success', 'danger', 'primary');

    if (resultatNet > 0) {
        card.classList.add('success');
        icon.classList.add('success');
    } else if (resultatNet < 0) {
        card.classList.add('danger');
        icon.classList.add('danger');
    } else {
        card.classList.add('primary');
        icon.classList.add('primary');
    }
}

/**
 * Met à jour la carte d'évolution des abonnés.
 * @param {number} nbActuel - Nombre d'abonnés actuels.
 * @param {number} nbPrec - Nombre d'abonnés de l'année précédente.
 * @param {string} anneePrec - L'année précédente.
 */
function updateEvolutionAbonnesCard(nbActuel, nbPrec, anneePrec) {
    const card = document.getElementById('evolution-abonnes-card');
    const icon = document.getElementById('evolution-abonnes-icon');
    const evolutionText = document.getElementById('kpi-clients-evolution');
    if (!card || !icon || !evolutionText) return;

    const difference = nbActuel - nbPrec;
    let evolutionString = `vs ${nbPrec} en ${anneePrec}`;
    
    card.classList.remove('success', 'danger', 'primary');
    icon.classList.remove('success', 'danger', 'primary');

    if (difference > 0) {
        evolutionString = `+${difference} vs ${anneePrec}`;
        card.classList.add('success');
        icon.classList.add('success');
    } else if (difference < 0) {
        evolutionString = `${difference} vs ${anneePrec}`;
        card.classList.add('danger');
        icon.classList.add('danger');
    } else {
        evolutionString = `Aucune évolution vs ${anneePrec}`;
        card.classList.add('primary');
        icon.classList.add('primary');
    }
    evolutionText.textContent = evolutionString;
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
