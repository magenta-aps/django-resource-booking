from datetime import timedelta

from django.forms import widgets
from django.forms.widgets import HiddenInput
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe


class DurationWidget(widgets.MultiWidget):

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
            return widgets.NumberInput(attrs=attrs)
        elif type == 'select':
            parsed_choices = []
            for choice in choices:
                if isinstance(choice, (unicode, int)):
                    parsed_choices.append((choice, unicode(choice)))
                elif isinstance(choice, tuple):
                    parsed_choices.append(choice)
            return widgets.Select(attrs=attrs, choices=parsed_choices)
        else:
            raise TypeError("type must be either 'number' " +
                            "or 'select', not '%s'" % type)

    def decompress(self, value):
        if value and isinstance(value, timedelta):
            return [value.days, value.seconds / 3600,
                    (value.seconds / 60) % 60]
        return [0, 0, 0]

    def value_from_datadict(self, data, files, name):
        valuelist = []
        for i, widget in enumerate(self.widgets):
            value = widget.value_from_datadict(data, files, name + '_%s' % i)
            valuelist.append(int(value or 0))

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


class OrderedMultipleHiddenChooser(widgets.MultipleHiddenInput):

    def __init__(self, attrs=None, choices=[]):
        super(OrderedMultipleHiddenChooser, self).__init__(attrs)
        # choices can be any iterable
        self.choices = choices

    def get_context(self, name, value, attrs):
        context = HiddenInput.get_context(self, name, value, attrs)
        final_attrs = context['widget']['attrs']
        id = context['widget']['attrs'].get('id')
        selected_elements = [None]*len(value)
        unselected_elements = []
        for i, choice in enumerate(self.choices):
            v, label = choice
            widget_attrs = final_attrs.copy()
            selected = v in value

            if not selected:
                widget_attrs['disabled'] = 'disabled'

            if id:
                widget_attrs['id'] = '%s_%s' % (id, i)
            widget = HiddenInput()
            widget.is_required = self.is_required
            widgetcontext = widget.get_context(
                name,
                force_text(v),
                widget_attrs
            )['widget']

            if selected:
                try:
                    index = value.index(v)
                    selected_elements[index] = widgetcontext
                except ValueError:
                    pass
            else:
                unselected_elements.append(widgetcontext)

        prototype_attrs = dict(disabled='disabled', **final_attrs)
        del prototype_attrs['id']
        prototype_attrs['data-prototype'] = 1
        widget = HiddenInput()
        unselected_elements.append(
            widget.get_context(name, '', prototype_attrs)['widget']
        )

        context['widget']['subwidgets'] = [
            e for e in selected_elements + unselected_elements
            if e is not None
        ]
        return context

    # Take the extracted value list and attempt to map them to choices
    # A bug in Django has them as unicodes instead of integers
    # when the form is bound with submitted data
    def value_from_datadict(self, data, files, name):
        value = super(OrderedMultipleHiddenChooser, self).value_from_datadict(
            data, files, name
        )
        choice_map = {
            choice[0]: choice[1]
            for choice in self.choices
        }
        coerced_value = []
        for v in value:
            if int(v) in choice_map:
                coerced_value.append(int(v))
            elif unicode(v) in choice_map:
                coerced_value.append(unicode(v))
            else:
                coerced_value.append(v)
        return coerced_value


class DisabledChoiceMixin(object):
    disabled_values = []

    def create_option(self, name,
                      value, label,
                      selected, index,
                      subindex=None, attrs=None):
        disabled = False
        if isinstance(label, dict):
            label, disabled = (label['label'],
                               label['label'] in self.disabled_values)
        option_dict = super(widgets.Select, self).create_option(
            name, value,
            label, selected,
            index, subindex=subindex,
            attrs=attrs)
        if disabled:
            option_dict['attrs']['disabled'] = 'disabled'
        return option_dict


# A Select widget that may have disabled options
class SelectDisable(DisabledChoiceMixin, widgets.Select):
    pass


# A SelectMultiple widget that may have disabled options
class SelectMultipleDisable(DisabledChoiceMixin, widgets.SelectMultiple):
    pass


# A CheckboxSelectMultiple widget that may have disabled options
class CheckboxSelectMultipleDisable(DisabledChoiceMixin,
                                    widgets.CheckboxSelectMultiple):
    pass
