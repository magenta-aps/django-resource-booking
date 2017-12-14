(function($) {
    $('#bookingform').on("submit", function() {
        $('#submitbutton').html("Tilmelder...");
        $('#booking-spinner').show();
    });
})(jQuery);