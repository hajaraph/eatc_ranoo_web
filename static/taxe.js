$("#add_taxe").click(function (e){
    e.preventDefault();
    const index = $("#afficher_taxe .taxe-group").length;
    $("#afficher_taxe").append('<div></div>' +
        '<div class="col-md-4 mt-4" id="nom_taxes-' + index + '">\n' +
        '   <div class="form-floating">\n' +
        '       <input type="text" name="nom_taxe" id="nom_taxe" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="" required>\n' +
        '       <label for="nom_taxe">Nom Taxe</label>\n' +
        '   </div>\n' +
        '</div>\n' +
        '<div class="col-md-4 mt-4" id="taux_taxes">\n' +
        '   <div class="form-floating">\n' +
        '       <input type="text" name="taux_taxe" id="taux_taxe" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="" required>\n' +
        '       <label for="taux_taxe">Taux (%)</label>\n' +
        '   </div>\n' +
        '<div class="btn btn-sm btn-warning rounded-circle" id="retirer"><i class="fas fa-minus"></i></div>\n'+
        '</div>'
)
});
$("#afficher_taxe").on("click", "#retirer", function (e) {
    e.preventDefault();
    $(this).closest('#nom_taxes').remove();
    $(this).closest('#taux_taxes').remove();
});