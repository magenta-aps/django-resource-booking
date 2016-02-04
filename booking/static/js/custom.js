//Search-list.html start:
$('.input-daterange input').each(function() {
    $(this).datepicker({
        language: 'da',
        format: 'dd-mm-yyyy',
        weekStart: 1,
        todayHighlight: true,
        startDate: 'Date',
        clearBtn: true,
        autoclose: true
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
//Search-list.html end
$("#reset-btn").click(function() {
    $("#searchBox").val("");
    $("form").trigger("submit")
});

// Automatically submit the search form whenever the filters are changed
$(function() {
    $('#filter-search-results input[type=checkbox]').on('change', function() {
        $(this.form).trigger("submit")
    });
    $('#filter-search-results input.datepicker').on('changeDate', function() {
        $(this.form).trigger("submit")
    });
});
