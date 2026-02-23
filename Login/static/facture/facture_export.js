$(document).ready(function () {
    $('#confirmer-export').click(function (e) {
        e.preventDefault(); // Empêcher la soumission classique

        const dateDeb = $('#export-pdf #date_deb').val();
        const dateFin = $('#export-pdf #date_fin').val();
        const commune = $('#export-pdf #commune').val();
        const num_client_deb = $('#export-pdf #num_client_deb').val();
        const num_client_fin = $('#export-pdf #num_client_fin').val();

        // Validation basique
        if (!commune) {
            alert("Veuillez sélectionner une commune.");
            return;
        }

        // Préparer les données
        let url = '/facture/pdf';
        url += `?date_deb=${dateDeb}&date_fin=${dateFin}&commune=${commune}`;
        if (num_client_deb) url += `&num_client_deb=${num_client_deb}`;
        if (num_client_fin) url += `&num_client_fin=${num_client_fin}`;

        let $btn = $(this);
        let originalText = $btn.html();

        // Mettre à jour l'UI du bouton
        $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Lancement...');

        // S'assurer qu'une barre de progression existe
        let $progressContainer = $('#pdf-progress-container');
        if ($progressContainer.length === 0) {
            $('.modal-body', '#export-pdf').append(`
                <div id="pdf-progress-container" class="mt-4" style="display:none;">
                    <p id="pdf-progress-text" class="text-center mb-1 fw-bold">Génération en cours...</p>
                    <div class="progress" style="height: 20px;">
                        <div id="pdf-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated bg-success" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                    </div>
                </div>
            `);
            $progressContainer = $('#pdf-progress-container');
        }

        $progressContainer.fadeIn();
        $('#pdf-progress-bar').css('width', '10%').text('Démarrage...');

        // 1. Lancer la tâche Celery
        $.ajax({
            url: url,
            method: 'GET',
            success: function (response) {
                if (response.task_id) {
                    $('#pdf-progress-text').text(`Génération de ${response.total_factures} facture(s)...`);
                    // 2. Commencer le polling
                    pollTaskStatus(response.task_id, $btn, originalText);
                } else if (response.error) {
                    resetUI($btn, originalText, response.error);
                }
            },
            error: function (xhr) {
                resetUI($btn, originalText, "Erreur lors du lancement de la génération.");
            }
        });
    });

    function pollTaskStatus(taskId, $btn, originalText) {
        $.ajax({
            url: `/facture/pdf/status/${taskId}/`,
            method: 'GET',
            success: function (response) {
                let status = response.status;

                if (status === 'PROGRESS') {
                    // Mettre à jour la barre de progression
                    if (response.progress) {
                        let pct = response.progress.percent || 0;
                        $('#pdf-progress-bar')
                            .css('width', pct + '%')
                            .text(pct + '%');
                        $('#pdf-progress-text').text(`Génération: ${response.progress.current} / ${response.progress.total}`);
                    }
                    // Relancer le polling
                    setTimeout(() => pollTaskStatus(taskId, $btn, originalText), 2000);
                }
                else if (status === 'SUCCESS') {
                    // Fin avec succès
                    $('#pdf-progress-bar').css('width', '100%').text('100%').removeClass('progress-bar-animated');
                    $('#pdf-progress-text').text('Terminé ! Téléchargement en cours...');

                    if (response.result && response.result.status === 'success') {
                        // Télécharger le fichier via iframe cachée pour ne pas quitter la page
                        let downloadUrl = `/facture/pdf/download/${response.result.filename}/`;
                        window.location.href = downloadUrl;

                        setTimeout(() => {
                            $('#export-pdf').modal('hide');
                            resetUI($btn, originalText);
                        }, 2000);
                    } else {
                        // Erreur gérée par la tâche
                        resetUI($btn, originalText, response.result ? response.result.message : "Erreur inconnue");
                    }
                }
                else if (status === 'FAILURE') {
                    resetUI($btn, originalText, "Erreur lors de la génération: " + response.error);
                }
                else {
                    // PENDING ou autre
                    setTimeout(() => pollTaskStatus(taskId, $btn, originalText), 2000);
                }
            },
            error: function () {
                resetUI($btn, originalText, "Erreur de connexion lors du suivi de la tâche.");
            }
        });
    }

    function resetUI($btn, originalText, errorMessage = null) {
        $btn.prop('disabled', false).html(originalText);
        let $p = $('#pdf-progress-container');
        if (errorMessage) {
            $('#pdf-progress-bar').removeClass('bg-success').addClass('bg-danger');
            $('#pdf-progress-text').text(errorMessage).addClass('text-danger');
            setTimeout(() => {
                $p.fadeOut();
                $('#pdf-progress-text').removeClass('text-danger');
                $('#pdf-progress-bar').removeClass('bg-danger').addClass('bg-success').css('width', '0%').text('0%');
            }, 6000);
        } else {
            $p.fadeOut();
        }
    }
});