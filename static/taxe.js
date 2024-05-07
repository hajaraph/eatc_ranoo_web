$("#add_taxe").click(function (e){
    e.preventDefault();
    $("#afficher_taxe").append('<div></div>' +
        '<div class="col-md-4 mt-4">\n' +
        '   <div class="form-floating">\n' +
        '       <input type="text" name="nom_taxe" id="nom_taxe" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="" required>\n' +
        '       <label for="nom_taxe">Nom Taxe</label>\n' +
        '   </div>\n' +
        '</div>\n' +
        '<div class="col-md-4 mt-4">\n' +
        '   <div class="form-floating">\n' +
        '       <input type="text" name="taux_taxe" id="taux_taxe" class="form-control shadow-none rounded-0 border-start-0 border-top-0 border-end-0" placeholder="" required>\n' +
        '       <label for="taux_taxe">Taux (%)</label>\n' +
        '   </div>\n' +
        '</div>'
    )
});