(function($) {
    $('#bookingform').on("submit", function() {
        $('#submitbutton').html("Tilmelder...");
        $('#booking-spinner').show();
    });
})(jQuery);

(function($) {
    $('input[disablepaste=true]').on('paste', function (e) {
        e.preventDefault();
    });
})(jQuery);