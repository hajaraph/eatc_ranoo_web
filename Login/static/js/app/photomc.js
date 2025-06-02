$(document).ready(function () {
    $("#photo").click(function (e){
        e.preventDefault();
        $("#afficher").append('' +
            '<div class="form-floating">\n' +
            '    <input type="file" name="photo_anomalie" id="photo_anomalie" class="form-control rounded-0 shadow-none border-start-0 border-top-0 border-end-0" accept="image/jpeg, image/png, application/pdf">\n' +
            '</div>\n'
        )
    });
})