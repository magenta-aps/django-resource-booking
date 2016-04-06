$(function(){
    $('input.datepicker').each(function() {
        var options = {
            language: 'da',
            format: 'dd-mm-yyyy',
            weekStart: 1,
            calendarWeeks: true,
            todayHighlight: true,
            clearBtn: true,
            autoclose: true
        };
        if (!$(this).hasClass('datepicker-admin')) {
            options['startDate'] = 'Date';
        }
        $(this).datepicker(options);
    });
});