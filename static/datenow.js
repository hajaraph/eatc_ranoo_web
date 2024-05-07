$(document).ready(function () {
    let today = new Date();
    let day = today.getDate();
    let month = today.getMonth() + 1;
    let year = today.getFullYear();
    if (day < 10) {
        day = '0' + day
    }
    if (month < 10) {
        month = '0' + month
    }
    let date = year + '-' + month + '-' + day;
    $('#date_releve').val(date);

    $("#date_releve").change(function() {
        const selectedDate = new Date($(this).val());
        const formattedDate = `${selectedDate.getDate()}/${selectedDate.getMonth() + 1}/${selectedDate.getFullYear()}`;
        $("#custom-date-input").val(formattedDate);
    });

    $('#volume').on('input', function() {
        // Obtenir la valeur actuelle du champ de texte
        const inputValue = $(this).val();

        // Remplacer tout sauf les chiffres par une chaîne vide
        let numericValue = inputValue.replace(/[^\d.]/g, '');

        // Mettre à jour la valeur du champ avec les chiffres uniquement
        const decimalCount = numericValue.split('.').length - 1;
        if (decimalCount > 1) {
            numericValue = numericValue.slice(0, -1); // Supprimer le dernier caractère (point en trop)
        }

        // Mettre à jour la valeur du champ avec les chiffres et le point uniquement
        $(this).val(numericValue);
    });
});