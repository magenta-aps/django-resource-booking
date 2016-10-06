from django.forms.utils import flatatt
from django.forms import widgets
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils.html import format_html

from itertools import chain
from datetime import timedelta

from django.utils.datastructures import MergeDict, MultiValueDict


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

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        id_ = final_attrs.get('id', None)
        selected_elements = [None]*len(value)
        unselected_elements = []
        for i, choice in enumerate(chain(self.choices, choices)):
            v, label = choice
            input_attrs = dict(value=force_text(v), **final_attrs)
            selected = v in value

            if not selected:
                input_attrs['disabled'] = 'disabled'
            if id_:
                input_attrs['id'] = '%s_%s' % (id_, i)

            element = format_html('<input{} />', flatatt(input_attrs))
            if selected:
                try:
                    index = value.index(v)
                    selected_elements[index] = element
                except ValueError:
                    pass
            else:
                unselected_elements.append(element)

        prototype_attrs = dict(disabled='disabled', **final_attrs)
        del prototype_attrs['id']
        prototype_attrs['data-prototype'] = 1
        unselected_elements.append(
            format_html('<input{} />', flatatt(prototype_attrs))
        )

        return mark_safe(
            '\n'.join(
                [e for e in selected_elements if e is not None] +
                unselected_elements
            )
        )


class DisabledChoiceMixin(object):
    disabled_values = []

    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        if option_value in self.disabled_values:
            disabled_html = mark_safe(' disabled="disabled"')
        else:
            disabled_html = ''
        return format_html('<option value="{}"{}{}>{}</option>',
                           option_value,
                           selected_html,
                           disabled_html,
                           force_text(option_label))


# A Select widget that may have disabled options
class SelectDisable(DisabledChoiceMixin, widgets.Select):
    pass


# A SelectMultiple widget that may have disabled options
class SelectMultipleDisable(DisabledChoiceMixin, widgets.SelectMultiple):
    pass


# Renderer class for choicefields that may have disabled options
class DisabledChoiceFieldRenderer(widgets.ChoiceFieldRenderer):
    disabled_values = []
    real_choice_input_class = None

    def __init__(self, *args, **kwargs):
        if 'disabled_values' in kwargs:
            values = kwargs.pop('disabled_values')
            if type(values) == set:
                values = list(values)
            elif type(values) != list:
                values = [values]
            self.disabled_values = [unicode(x) for x in values]
        super(DisabledChoiceFieldRenderer, self).__init__(*args, **kwargs)

    # Overriding an attribute on the superclass that is a class reference
    # replacing it with a regular function that returns an instance
    def choice_input_class(self, name, value, attrs, choice, index):
        (choice_value, choice_label) = choice
        if unicode(choice_value) in self.disabled_values:
            attrs['disabled'] = "disabled"
        return self.real_choice_input_class(name, value, attrs, choice, index)


class DisabledRadioFieldRenderer(DisabledChoiceFieldRenderer):
    real_choice_input_class = widgets.RadioChoiceInput


class DisabledCheckboxFieldRenderer(DisabledChoiceFieldRenderer):
    real_choice_input_class = widgets.CheckboxChoiceInput


# A CheckboxSelectMultiple widget that may have disabled options
class CheckboxSelectMultipleDisable(DisabledChoiceMixin,
                                    widgets.CheckboxSelectMultiple):
    renderer = DisabledCheckboxFieldRenderer
    disabled_values = []

    def get_renderer(self, name, value, attrs=None, choices=()):
        if value is None:
            value = self._empty_value
        final_attrs = self.build_attrs(attrs)
        choices = list(chain(self.choices, choices))
        return self.renderer(
            name, value, final_attrs, choices,
            disabled_values=self.disabled_values
        )
