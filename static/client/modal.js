$(document).ready(function () {
    //Ajouter un autre champ pour le fichier
    $("#add").click(function (e){
        e.preventDefault();
        $("#afficher").append('<div></div>' +
            '<div class="col-md-4 mt-4">\n' +
            '  <div class="form-floating">\n' +
            '     <input type="file" name="piece_client" id="piece_client" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" accept="image/jpeg, image/png, application/pdf">\n' +
            '  </div>\n' +
            '</div>\n' +
            '<div class="col-md-4 mt-4">\n' +
            '  <div class="form-floating">\n' +
            '     <input type="text" name="designation" id="designation" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="">\n' +
            '     <label for="designation">Designation</label>\n' +
            '  </div>\n' +
            '</div>'
        )
    });

    const formCommune = $("#formNew #commune");
    const formCP = $("#formNew #cp_commune");

    $("#formNew #region").on('change', function () {
        if ($(this).val()) {
            $.ajax({
                url: '/clients/nouveau/' + $(this).val(),
                type: 'GET',
                success: function (resp) {
                    let communeOption = '';
                    let cpOption = '';
                    resp.data.forEach(Commune => {
                        communeOption += `<option value="${Commune.cp_commune}">${Commune.commune}</option>`;
                        cpOption += `<option value="${Commune.cp_commune}">${Commune.cp_commune}</option>`;
                    });

                    formCommune.html(communeOption);
                    formCP.html(cpOption);
                },
            });
        } else {
            formCommune.empty();
            formCP.empty();
        }
    });

    formCommune.on('change', function () {
        const selectedCommune = $(this).val();
        const selectedCpCommune = $("#formNew #cp_commune option[value='" + selectedCommune + "']").val();
        formCP.val(selectedCpCommune);
    });
})
