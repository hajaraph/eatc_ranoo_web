document.addEventListener('DOMContentLoaded', function() {
    const exportRecetteModal = document.getElementById('exportRecetteModal');
    const openExportRecetteModalBtn = document.getElementById('openExportRecetteModalBtn');
    const confirmExportRecetteBtn = document.getElementById('confirmExportRecetteBtn');
    const exportDatedebInput = document.getElementById('exportDatedeb');
    const exportDatefinInput = document.getElementById('exportDatefin');

    // When the modal is opened, pre-fill the date inputs with current filter values
    if (openExportRecetteModalBtn) {
        openExportRecetteModalBtn.addEventListener('click', function() {
            const currentDatedeb = document.querySelector('input[name="datedeb"]').value;
            const currentDatefin = document.querySelector('input[name="datefin"]').value;

            if (exportDatedebInput) {
                exportDatedebInput.value = currentDatedeb;
            }
            if (exportDatefinInput) {
                exportDatefinInput.value = currentDatefin;
            }
        });
    }

    // Handle the export button click inside the modal
    if (confirmExportRecetteBtn) {
        confirmExportRecetteBtn.addEventListener('click', function() {
            const datedeb = exportDatedebInput ? exportDatedebInput.value : '';
            const datefin = exportDatefinInput ? exportDatefinInput.value : '';

            let exportUrl = '/recette/export/';
            const params = new URLSearchParams();

            if (datedeb) {
                params.append('datedeb', datedeb);
            }
            if (datefin) {
                params.append('datefin', datefin);
            }

            if (params.toString()) {
                exportUrl += '?' + params.toString();
            }

            window.open(exportUrl, '_blank');

            // Close the modal
            const modal = bootstrap.Modal.getInstance(exportRecetteModal);
            if (modal) {
                modal.hide();
            }
        });
    }
});
