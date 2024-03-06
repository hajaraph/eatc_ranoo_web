$(document).ready(function () {
    $('#image').change(function(event) {
        const file = event.target.files[0];
        const reader = new FileReader();

        reader.onload = function(e) {
            const image_preview = $('#image_preview');
            image_preview.removeAttr('src')
            image_preview.attr('src', e.target.result);
            image_preview.removeClass('invisible');
            $('#image_icon').hide();
        }
        reader.readAsDataURL(file);
    });
    const volumeInput = $('#volume');
    const volumeValue = volumeInput.val();
    volumeInput.val(volumeValue.replace('.', ','));
})