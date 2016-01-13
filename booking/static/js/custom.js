//Search-list.html:
$('.input-daterange input').each(function() {
    $(this).datepicker({
        language: 'da',
        format: 'dd-mm-yyyy',
        todayHighlight: true,
        startDate: 'Date',
        clearBtn: true,
        autoclose: true
    });
});
$(function() {
    $('#filter-search-results input[type=checkbox]').on('change', function() {
        $(this.form).trigger("submit")
    });
    $('#filter-search-results input.datepicker').on('changeDate', function() {
        $(this.form).trigger("submit")
    });
});
$('.collapse').on('show.bs.collapse', function() {
    $(this).parent().find(".caret").addClass("caret-up");
});
$('.collapse').on('hide.bs.collapse', function() {
    $(this).parent().find(".caret").removeClass("caret-up");
});
$('#filters').on('show.bs.collapse', function() {
    $(this).prev().find(".glyphicon").toggleClass("glyphicon-chevron-down glyphicon-chevron-up");
});
$('#filters').on('hide.bs.collapse', function() {
    $(this).prev().find(".glyphicon").toggleClass("glyphicon-chevron-up glyphicon-chevron-down");
});
//Search-list.html
//Keep footer stuck to bottom
var footer = function() {
        $('body').css('margin-bottom', $('footer').height() + 40);
    },
    didResize = false;
footer();
$(window).resize(function() {
    didResize = true;
});
setInterval(function() {
    if (didResize) {
        didResize = false;
        footer();
    }
}, 250);
