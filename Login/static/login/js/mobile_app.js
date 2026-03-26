// Mobile App Download Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Animation d'apparition des cartes
    const cards = document.querySelectorAll('.current-version-card, .changelog-card, .instructions-card, .support-card, .versions-list');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        observer.observe(card);
    });

    // Gestion du modal QR Code
    window.showQRCode = function() {
        const modal = document.getElementById('qrModal');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    };

    window.hideQRCode = function() {
        const modal = document.getElementById('qrModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    };

    // Fermer le modal avec la touche Echap
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideQRCode();
        }
    });

    // Détection de l'OS pour afficher un message personnalisé
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    let osInfo = '';

    if (/android/i.test(userAgent)) {
        osInfo = 'Android';
    } else if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) {
        osInfo = 'iOS';
    } else if (/Windows/i.test(userAgent)) {
        osInfo = 'Windows';
    } else if (/Mac/i.test(userAgent)) {
        osInfo = 'macOS';
    }

    console.log('Système d\'exploitation détecté :', osInfo);

    // Si l'utilisateur est sur mobile, afficher un badge
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        const downloadBtn = document.querySelector('.btn-download');
        if (downloadBtn) {
            const badge = document.createElement('span');
            badge.className = 'mobile-badge';
            badge.textContent = 'Mobile';
            badge.style.cssText = 'margin-left: 0.5rem; background: rgba(255,255,255,0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;';
            downloadBtn.appendChild(badge);
        }
    }
});
