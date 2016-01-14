//Search-list.html start:
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
//Booking form validation start...
// $('#startbookingform').validator().on('submit', function (e) {
//   if (e.isDefaultPrevented()) {
//     // handle the invalid form...
//   } else {
//     // everything looks good!
//   }
// });
//Booking form validation end...
//Clear serch field
$('#reset-btn').click(function() {
    $('#searchBox').val('');
});
