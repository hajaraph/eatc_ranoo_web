document.addEventListener('DOMContentLoaded', function() {
    const exportDepenseModal = document.getElementById('exportDepenseModal');
    const openExportDepenseModalBtn = document.getElementById('openExportDepenseModalBtn');
    const confirmExportDepenseBtn = document.getElementById('confirmExportDepenseBtn');
    const exportDepenseDatedebInput = document.getElementById('exportDepenseDatedeb');
    const exportDepenseDatefinInput = document.getElementById('exportDepenseDatefin');

    // When the modal is opened, pre-fill the date inputs with current filter values
    if (openExportDepenseModalBtn) {
        openExportDepenseModalBtn.addEventListener('click', function() {
            const currentDatedeb = document.querySelector('input[name="datedeb"]').value;
            const currentDatefin = document.querySelector('input[name="datefin"]').value;

            if (exportDepenseDatedebInput) {
                exportDepenseDatedebInput.value = currentDatedeb;
            }
            if (exportDepenseDatefinInput) {
                exportDepenseDatefinInput.value = currentDatefin;
            }
        });
    }

    // Handle the export button click inside the modal
    if (confirmExportDepenseBtn) {
        confirmExportDepenseBtn.addEventListener('click', function() {
            const datedeb = exportDepenseDatedebInput ? exportDepenseDatedebInput.value : '';
            const datefin = exportDepenseDatefinInput ? exportDepenseDatefinInput.value : '';

            let exportUrl = '/depense/export/';
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
            const modal = bootstrap.Modal.getInstance(exportDepenseModal);
            if (modal) {
                modal.hide();
            }
        });
    }
});
