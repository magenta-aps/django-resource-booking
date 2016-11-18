var KU = KU || {};
(function() {
    KU.initialize_time_interval = function(root_id, update_callback) {
        var $root = $(root_id),
            $output = $root.find('span.time-interval-output'),
            $start_date = $root.find('input[name=start_date]'),
            $start_time = $root.find('input[name=start_time]'),
            $end_date = $root.find('input[name=end_date]'),
            $end_time = $root.find('input[name=end_time]'),
            $time_mode = $root.find('select.time-mode').first(),
            $start = $root.find('div.start-input input').first(),
            $end = $root.find('div.end-input input').first(),
            $specific = $root.find('div.specific-time-input input').first()
            ;

        function zero_pad(int_val) {
            if(int_val < 10)
                return "0" + int_val;
            else
                return int_val;
        }

        function text_to_jsdate(text_value) {
            var date_parts = text_value.substr(0, 10).split(/[. -]/),
                time_text = text_value.substr(11) || '',
                time_parts = time_text.split(/[:]/);

            if(date_parts[0].length != 4) {
                date_parts = date_parts.reverse();
            }

            return new Date(
                date_parts[0],
                date_parts[1] - 1,
                date_parts[2],
                time_parts[0] || 0,
                time_parts[1] || 0,
                time_parts[2] || 0
            );
        }

        function format_datetime(jsdate) {
            return [
                zero_pad(jsdate.getDate()),
                zero_pad(jsdate.getMonth() + 1),
                jsdate.getFullYear()
            ].join(".") + " " + [
                zero_pad(jsdate.getHours()),
                zero_pad(jsdate.getMinutes()),
                "00"
            ].join(":");
        }

        function update_widgets() {
            var from = text_to_jsdate($start.val()),
                from_txt = format_datetime(from),
                to = text_to_jsdate($end.val()),
                to_txt = format_datetime(to)
                ;

            // If we're using full days we want the widgets to use one day
            // earlier.
            if($time_mode.val() == "full_days") {
                $specific.val("");
                if(from_txt.substr(0, 10) != to_txt.substr(0, 10)) {
                    to.setTime(to.getTime() - 24 * 60 * 60 * 1000);
                    to_txt = format_datetime(to);
                }
            } else {
                $specific.val("True");
            }

            $start_date.val(from_txt.substr(0, 10));
            $start_time.val(from_txt.substr(11, 5));
            $end_date.val(to_txt.substr(0, 10));
            $end_time.val(to_txt.substr(11, 5));
        }

        function next_day(date_val) {

            // Add 24 hours
            date.setTime(date.getTime() + 24 * 60 * 60 * 1000);

            return [
                zero_pad(date.getDate()),
                zero_pad(date.getMonth() + 1),
                date.getFullYear()
            ].join(".");
        }

        function update_datetimes() {
            var start_date_val = $start_date.val() || '',
                time_mode_val = $time_mode.val() || '',
                duration_in_min = $time_mode.attr('data-duration-in-minutes'),
                from, to, from_txt, to_txt;

            if(!start_date_val) {
                $start.val('');
                $end.val('');
                $output.text($output.attr('data-no-date-selected-text'));
            } else if(time_mode_val == 'full_days') {
                from = text_to_jsdate(start_date_val);
                to = text_to_jsdate($end_date.val());

                from_txt = format_datetime(from).substr(0, 10);
                to_txt = format_datetime(to).substr(0, 10);

                if(from_txt != to_txt) {
                    $output.text(from_txt + " - " + to_txt);
                } else {
                    $output.text(from_txt);
                }

                // The end-time we want to save is midnight of the next day
                to.setTime(to.getTime() + 24 * 60 * 60 * 1000);
            } else if(time_mode_val == 'use_duration') {
                from = text_to_jsdate(start_date_val + " " + $start_time.val());
                to = new Date(from.getTime());
                to.setTime(to.getTime() + duration_in_min * 60 * 1000);
                $output.text(
                    format_datetime(from).substr(0, 16) +
                    " - " +
                    format_datetime(to).substr(11, 5)
                );
            } else if(time_mode_val == 'time_and_date') {
                from = text_to_jsdate(
                    start_date_val + " " + $start_time.val()
                );
                to = text_to_jsdate($end_date.val() + " " + $end_time.val());

                from_txt = format_datetime(from).substr(0, 16);
                to_txt = format_datetime(to).substr(0, 16);

                if(from_txt.substr(0, 10) === to_txt.substr(0, 10)) {
                    $output.text(from_txt + " - " + to_txt.substr(11));
                } else {
                    $output.text(from_txt + " - " + to_txt);
                }
            }

            $start.val(format_datetime(from));
            $end.val(format_datetime(to));
            update_widgets();

            if(update_callback) {
                update_callback();
            }
        }

        $root.find('.input-daterange').datepicker({
            language: 'da',
            format: 'dd.mm.yyyy',
            weekStart: 1,
            calendarWeeks: true,
            todayHighlight: true,
            clearBtn: true,
            autoclose: true,
            inputs: $('.input-daterange .rangepicker')
        }).on('changeDate', update_datetimes);

        $('.clockpicker').clockpicker({
            'donetext': "Opdater",
            'autoclose': true,
            'afterDone': update_datetimes
        });

        $time_mode.on("change", function() {
            var val = $(this).val(),
                $time_widgets = $root.find('div.input-group.clockpicker');
            if(val == 'full_days') {
                $time_widgets.hide();
                $end_date.removeAttr('disabled');
                $end_time.removeAttr('disabled');
            } else if(val == 'use_duration') {
                $time_widgets.show();
                $end_date.attr('disabled', 'disabled');
                $end_time.attr('disabled', 'disabled');
            } else if(val == 'time_and_date') {
                $time_widgets.show();
                $end_date.removeAttr('disabled');
                $end_time.removeAttr('disabled');
            }
            update_datetimes();
        });

        update_widgets();
        $time_mode.trigger("change");
    };
})(KU);
