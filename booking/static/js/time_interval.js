var KU = KU || {};
(function() {
    var MINUTES_PER_STEP = 5,
        STEPS_PER_HOUR = 60 / MINUTES_PER_STEP,
        STEPS_IN_DAY = 24 * STEPS_PER_HOUR,
        START_AT_0800 = STEPS_PER_HOUR * 8,
        END_AT_1600 = STEPS_PER_HOUR * 16,
        DEFAULT_LABELS = ["00:00", "24:00"],
        DEFAULT_TICKS = [0, STEPS_IN_DAY]
        ;

    KU.initialize_time_interval = function(root_id, update_callback) {
        var $root = $(root_id),
            $duration = $root.find('input.product-duration'),
            $output = $root.find('span.time-interval-output'),
            $start_date = $root.find('input.start-date'),
            $start_time = $root.find('input.start-time'),
            $time_range = $root.find('input.time-range'),
            $specific_time = $root.find('.specific-time select').first(),
            $start_input = $root.find('div.start-input input').first(),
            $end_input = $root.find('div.end-input input').first(),

            duration_in_minutes = $duration.val() ?
                                  $duration.val() :
                                  0,
            duration_in_steps = Math.floor(
                                    duration_in_minutes / MINUTES_PER_STEP
                                ),
            interval_values = [0, 0],
            display_values = ["-", "-"],
            time_string = '',
            initial_start_time = START_AT_0800,
            initial_end_time = END_AT_1600
            ;

        function use_specific_time() {
            // No dropdown means no option to disable times, so always use
            // specific
            if(!$specific_time.length)
                return true;

            var val = $specific_time.val() || 'false';
            return val.toLowerCase() != 'false';
        }

        function hhmm_to_steps(hhmm) {
            var parts = hhmm.split(/:/);
            return parseInt(parts[0] * STEPS_PER_HOUR) +
                   parseInt(parts[1] / MINUTES_PER_STEP);
        }

        if($start_input.val()) {
            var parts = $start_input.val().split(/ /),
                date_parts = parts[0].split(/[\/.-]/);
            // If year is first part of date value, reverse the values
            if(date_parts[0].length == 4)
                date_parts = date_parts.reverse();
            $start_date.val(date_parts.join("."));
            if(use_specific_time()) {
                initial_start_time = hhmm_to_steps(parts[1]);
                if($end_input.val()) {
                    parts = $end_input.val().split(/ /);
                    initial_end_time = hhmm_to_steps(parts[1]);
                }
            }
        }

        function zero_pad(int_val) {
            if(int_val < 10)
                return "0" + int_val;
            else
                return int_val;
        }

        function display_time_value(val) {
            var hrs = Math.floor(val / STEPS_PER_HOUR),
                mins = (val % STEPS_PER_HOUR) * MINUTES_PER_STEP;

            return zero_pad(hrs) + ":" + zero_pad(mins);
        }

        function update_time_values(from, to) {
            if(!from || !to)
                return;
            interval_values = [from, to];
            display_values = [
                display_time_value(from),
                display_time_value(to)
            ];
            time_string = display_values.join(" - ");
        }

        function next_day(date_val) {
            var parts = date_val.split(/[.\/-]/);
            var date = new Date();
            date.setFullYear(parts[2]);
            date.setMonth(parts[1] - 1);
            date.setDate(parts[0]);

            // Add 24 hours
            date.setTime(date.getTime() + 24 * 60 * 60 * 1000);

            return [
                zero_pad(date.getDate()),
                zero_pad(date.getMonth() + 1),
                date.getFullYear()
            ].join(".");
        }

        function update_interval_output() {
            var date_val = $start_date.val(),
                time_values, from, to;

            // Output only the date, if that is selected
            if($specific_time.length) {
                if(!use_specific_time()) {
                    if(date_val) {
                        $start_input.val(date_val + " 00:00:00");
                        $end_input.val(next_day(date_val) + " 00:00:00");
                    } else {
                        $start_input.val('');
                        $end_input.val('');
                        date_val = $output.attr('data-no-date-selected-text');
                    }
                    $output.text(date_val);
                    if(update_callback)
                        update_callback();
                    return;
                }
            }
            if(!time_string) {
                if ($duration.is(":checked")) {
                    time_values = [
                        $start_time.slider('getValue'),
                        $start_time.slider('getValue') + duration_in_steps
                    ];
                } else {
                    time_values = $time_range.slider('getValue');
                }

                update_time_values(time_values[0], time_values[1]);
            }

            if(date_val) {
                $start_input.val(date_val + " " + display_values[0] + ":00");
                $end_input.val(date_val + " " + display_values[1] + ":00");
            } else {
                $start_input.val('');
                $end_input.val('');
                date_val = $output.attr('data-no-date-selected-text');
            }

            $output.text(date_val + " " + time_string);
            if(update_callback)
                update_callback();
        }

        
        $start_time.slider({
            min: 0,
            max: STEPS_IN_DAY - duration_in_steps,
            ticks: [0, STEPS_IN_DAY - duration_in_steps],
            ticks_labels: [
                DEFAULT_LABELS[0],
                display_time_value(STEPS_IN_DAY - duration_in_steps)
            ],
            value: initial_start_time,
            formatter: function(value) {
                update_time_values(value, value + duration_in_steps);
                update_interval_output();
                return time_string;
            }
        });

        $time_range.slider({
            min: 0,
            max: STEPS_IN_DAY,
            value: [initial_start_time, initial_end_time],
            ticks: DEFAULT_TICKS,
            ticks_labels: DEFAULT_LABELS,
            formatter: function(values) {
                update_time_values(values[0], values[1]);
                update_interval_output();
                return time_string;
            }
        });

        $duration.on("change", function() {
            if($(this).is(":checked")) {
                $start_time.parents('.timeslider').first().show();
                $time_range.parents('.timeslider').first().hide();
            } else {
                $start_time.parents('.timeslider').first().hide();
                $time_range.parents('.timeslider').first().show();
            }
            // Force update of displayed interval
            time_string = '';
            update_interval_output();
        }).trigger("change");

        $specific_time.on("change", function() {
            if(use_specific_time()) {
                $root.find('div.time-inputs').first().show();
            } else {
                $root.find('div.time-inputs').first().hide();
            }
            update_interval_output();
        }).trigger("change");

        $root.find('.input-group.datefield input').datepicker({
            language: 'da',
            format: 'dd.mm.yyyy',
            weekStart: 1,
            calendarWeeks: true,
            todayHighlight: true,
            startDate: 'Date',
            clearBtn: true,
            autoclose: true,
        }).on('changeDate', update_interval_output);

        $root.find('.input-group.datefield .input-group-addon').on(
            'click',
            function() {
                $(this).parent().find('input').datepicker('show');
            }
        );
    };
})(KU);
