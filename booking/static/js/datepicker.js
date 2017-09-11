$(function(){
    $('input.datepicker').each(function() {
      var date = new Date();
      date.setDate(date.getDate());
        var options = {
            language: 'da',
            format: 'dd-mm-yyyy',
            weekStart: 1,
            startDate: date,
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
