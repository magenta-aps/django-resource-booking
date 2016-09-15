$(function(){
    var currentDates = [];

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
        clearBtn: false,
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

        if(start_date_val) {
            options.dtstart = datestr_to_date(start_date_val);
        }

        if(end_date_val) {
            options.until = datestr_to_date(end_date_val);
        } else if(count_val.match(/^\d+$/)) {
            options.count = count_val;
        }

        if(freq_val) {
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
        if(options.byweekday.length === 0) {
            delete options.byweekday;
        }

        var $start = $('#interval_widgets .start-input input').first(),
            $end = $('#interval_widgets .end-input input').first(),
            $specific_time = $(
                '#interval_widgets .specific-time select'
            ).first(),
            start_time = $start.val().substr(11, 5),
            end_time = $end.val().substr(11, 5),
            time_str = $specific_time.val().toLowerCase() !== 'false' ?
                       [start_time, end_time].join(" - ") :
                       ''
            ;

        rule = new RRule(options);
        var outputEl = $('.rrule-datelist');
        outputEl.html('');
        if(rule.options.count || rule.options.until) {
            list = rule.all();
            for (var i=0; i<list.length; i++) {
                var r = list[i];

                value_str = [
                    pad(r.getUTCDate()),
                    pad(r.getUTCMonth() + 1),
                    r.getUTCFullYear()
                ].join(".");
                if(time_str) {
                    value_str = value_str + " " + time_str;
                }

                outputEl.append([
                    '<li>',
                    '  <input type="hidden" name="selecteddate" value="' + value_str + '" />',
                       value_str,
                    '</li>'
                ].join(""));
            }
        }
    };

    updateRRDates();

    // RRule input methods
    rrdatepickStart.datepicker().on('hide', updateRRDates);
    rrdatepick.datepicker().on('hide', updateRRDates);
    $('#input-weekdays input').on('change', updateRRDates);
    $('#input-frequency').on('change', updateRRDates);
    $('#input-count').on('keyup', updateRRDates);
});
