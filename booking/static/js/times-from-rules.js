$(function($){
    var $start_time = $('#id_start_time'),
        $end_time = $('#id_end_time'),
        $extra_days = $('#id_extra_days');

    function pad(number) {
        var r = String(number);
        if (r.length === 1) {
            r = '0' + r;
        }
        return r;
    }

    if (!Date.prototype.toISOString) {
        (function() {
            Date.prototype.toISOString = function() {
                return this.getUTCFullYear() +
                    '-' + pad( this.getUTCMonth() + 1 ) +
                    '-' + pad( this.getUTCDate() ) +
                    'T' + pad( this.getUTCHours() ) +
                    ':' + pad( this.getUTCMinutes() ) +
                    ':' + pad( this.getUTCSeconds() ) +
                    '.' + String(
                        (this.getUTCMilliseconds()/1000).toFixed(3)
                    ).slice( 2, 5 ) +
                    'Z';
            };
        }());
    }

    // =============================================================================
    // Adding several dates using RRule.js
    // =============================================================================

    var rrdatepickStart = $('#input-start').datepicker({
        language: 'da',
        format: 'dd.mm.yyyy',
        weekStart: 1,
        calendarWeeks: true,
        todayHighlight: true,
        startDate: 'Date',
        clearBtn: false,
        autoclose: true
    });

    var rrdatepick = $('#input-until').datepicker({
        language: 'da',
        format: 'dd.mm.yyyy',
        weekStart: 1,
        calendarWeeks: true,
        todayHighlight: true,
        startDate: 'Date',
        clearBtn: true,
        autoclose: true
    });


    function datestr_to_date(datestr) {
        var d = new Date(),
            dparts = datestr.split(/[\/.-]/);

        d.setUTCDate(dparts[0]);
        d.setUTCMonth(parseInt(dparts[1]) - 1);
        d.setUTCFullYear(dparts[2]);
        d.setUTCHours(0, 0, 0, 0);

        return d;
    }

    function format_time(d) {
        return [pad(d.getUTCHours()), pad(d.getUTCMinutes())].join(":");
    }

    function format_date(d) {
        return [
            pad(d.getUTCDate()),
            pad(d.getUTCMonth() + 1),
            d.getUTCFullYear()
        ].join(".");
    }

    function format_interval(d1, d2) {
        var datestr1 = format_date(d1),
            datestr2 = format_date(d2);
        if(datestr1 == datestr2) {
            return datestr1 + " " + format_time(d1) + " - " + format_time(d2);
        } else {
            return datestr1 + " " + format_time(d1) +
                   " - " +
                   datestr2 + " " + format_time(d2);
        }
    }


    var weekday_map = {
        'RRule.MO': RRule.MO,
        'RRule.TU': RRule.TU,
        'RRule.WE': RRule.WE,
        'RRule.TH': RRule.TH,
        'RRule.FR': RRule.FR,
        'RRule.SA': RRule.SA,
        'RRule.SU': RRule.SU
    };

    var freq_map = {
        "weekly": [RRule.WEEKLY, 1],
        "montly": [RRule.MONTHLY, 1],
        "trimonthly": [RRule.MONTHLY, 3],
        "halfyearly": [RRule.MONTHLY, 6],
        "yearly": [RRule.YEARLY, 1]
    };

    // RRule update
    var updateRRDates = function() {
        var options = {
                freq: RRule.WEEKLY,
                interval: 1,
                wkst: RRule.MO,
                byweekday: []
            },
            start_date_val = $('#input-start').val(),
            end_date_val = $('#input-until').val(),
            count_val = $('#input-count').val() || '',
            freq_val = $('#input-frequency').val();

        if (start_date_val) {
            options.dtstart = datestr_to_date(start_date_val);
        }

        if (end_date_val) {
            options.until = datestr_to_date(end_date_val);
        } else if(count_val.match(/^\d+$/)) {
            options.count = count_val;
        }

        if (freq_val) {
            var mapped = freq_map[freq_val];
            if(mapped) {
                options.freq = mapped[0];
                options.interval = mapped[1];
            }
        }

        $('#input-weekdays input:checked').each(function() {
            var val = weekday_map[$(this).attr('name')];
            if(val)
                options.byweekday.push(val);
        });
        if (options.byweekday.length === 0) {
            delete options.byweekday;
        }

        var start_hhmm = ($start_time.val() || '00:00').split(":"),
            end_hhmm = ($end_time.val() || '00:00').split(":"),
            start_hours = parseInt(start_hhmm[0], 10),
            start_minutes = parseInt(start_hhmm[1], 10),
            end_hours = parseInt(end_hhmm[0], 10),
            end_minutes = parseInt(end_hhmm[1], 10),
            extra_days = parseInt($extra_days.val() || 0);
        if (extra_days < 0) {
            extra_days = 0;
        }

        // If end offset was less than start offset we've wrapped around
        // midnight.
        if (end_hours < start_hours || (end_hours === start_hours && end_minutes < start_minutes)) {
            extra_days += 1;
        }

        if (extra_days > 0) {
            end_hours += extra_days * 24;
        }
        var rule = new RRule(options);
        var outputEl = $('.rrule-datelist');
        outputEl.html('');
        if (rule.options.count || rule.options.until) {
            var list = rule.all();
            for (var i=0; i<list.length; i++) {
                var time = list[i].getTime(),
                    d1 = new Date(time);
                    d2 = new Date(time);
                d1.setHours(start_hours, start_minutes - d1.getTimezoneOffset());
                d2.setHours(end_hours, end_minutes - d2.getTimezoneOffset());
                var value_str = format_interval(d1, d2);

                outputEl.append([
                    '<li>',
                    '  <input type="hidden" name="selecteddate" value="' + value_str + '" />',
                       value_str,
                    '</li>'
                ].join(""));
            }
        }
        return true;
    };

    updateRRDates();

    // RRule input methods
    rrdatepickStart.datepicker().on('hide', updateRRDates);
    rrdatepick.datepicker().on('hide', function() {
        if ($(this).val()) {
            $('#input-count').val('');
        }
        updateRRDates();
    });
    $('#input-weekdays input').on('change', updateRRDates);
    $('#input-frequency').on('change', updateRRDates);
    $('#input-count').on('keyup', function() {
        if ($(this).val()) {
            rrdatepick.val('');
        }
        updateRRDates();
    });

    $('.clockpicker').clockpicker({
        'donetext': "Opdater",
        'autoclose': true,
        'afterDone': updateRRDates
    });

    $extra_days.on("change", updateRRDates);
});
