from django.forms.widgets import MultiWidget, NumberInput, Select
from datetime import timedelta
from django.utils.safestring import mark_safe


class DurationWidget(MultiWidget):

    def __init__(self, attrs=None,
                 day_type='number', day_attrs={'min': 0},
                 day_choices=[0, 1, 2], day_label=None,
                 hour_type='number', hour_attrs={'min': 0, 'max': 23},
                 hour_choices=[0, 1, 2, 3, 4], hour_label=None,
                 minute_type='select', minute_attrs=None,
                 minute_choices=[0, 15, 30, 45], minute_label=None):
        # create choices for days, months, years
        # example below, the rest snipped for brevity.

        self.daywidget = self._getwidget(day_type, day_attrs, day_choices)
        self.hourwidget = self._getwidget(hour_type, hour_attrs, hour_choices)
        self.minutewidget = self._getwidget(minute_type,
                                            minute_attrs, minute_choices)

        widgets = (self.daywidget, self.hourwidget, self.minutewidget)
        self.day_label = day_label
        self.hour_label = hour_label
        self.minute_label = minute_label
        super(DurationWidget, self).__init__(widgets, attrs)

    @staticmethod
    def _getwidget(type, attrs, choices):
        if type == 'number':
            return NumberInput(attrs=attrs)
        elif type == 'select':
            parsed_choices = []
            for choice in choices:
                if isinstance(choice, (unicode, int)):
                    parsed_choices.append((choice, unicode(choice)))
                elif isinstance(choice, tuple):
                    parsed_choices.append(choice)
            return Select(attrs=attrs, choices=parsed_choices)
        else:
            raise TypeError("type must be either 'number' " +
                            "or 'select', not '%s'" % type)

    def decompress(self, value):
        if value and isinstance(value, timedelta):
            return [value.days, value.seconds / 3600,
                    (value.seconds / 60) % 60]
        return [None, None, None]

    def value_from_datadict(self, data, files, name):
        valuelist = [
            int(widget.value_from_datadict(data, files, name + '_%s' % i))
            for i, widget in enumerate(self.widgets)]
        return timedelta(days=valuelist[0], hours=valuelist[1],
                         minutes=valuelist[2])

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name + '_%s' % i,
                                        widget_value, final_attrs))
        return mark_safe(self.format_output(output, id_))

    def format_output(self, rendered_widgets, id):
        out = ''

        if self.day_label:
            out += "<label for=\"%s\">%s</label>" % (id+"_0", self.day_label)
        out += rendered_widgets[0]

        if self.hour_label:
            out += "<label for=\"%s\">%s</label>" % (id+"_1", self.hour_label)
        out += rendered_widgets[1]

        if self.minute_label:
            out += "<label for=\"%s\">%s</label>" % (id+"_2",
                                                     self.minute_label)
        out += rendered_widgets[2]

        return out
