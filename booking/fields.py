from inspect import isclass

from django.core.exceptions import ValidationError
from django.forms.fields import ChoiceField, MultipleChoiceField
from django.forms.models import ModelChoiceField
from django.forms.models import ModelMultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple, Select, SelectMultiple

from django.utils.translation import ugettext_lazy as _

from booking.models import EventTime

from .widgets import CheckboxSelectMultipleDisable
from .widgets import OrderedMultipleHiddenChooser
from .widgets import SelectDisable, SelectMultipleDisable


class ExtensibleMultipleChoiceField(MultipleChoiceField):
    """
    Like a MultipleChoiceField, but does not raise a validation error on
    values that were not part of the original choice list.
    Handy for dynamically adding choices with JavaScript
    """
    def valid_value(self, value):
        return True


class OrderedMultipleChoiceField(ExtensibleMultipleChoiceField):
    widget = OrderedMultipleHiddenChooser

    def has_changed(self, initial, data):
        if super(OrderedMultipleChoiceField, self).has_changed(initial, data):
            return True
        if initial is None:
            initial = []
        if data is None:
            data = []
        for i, value in enumerate(initial):
            if data[i] != initial[i]:
                return True
        return False


class DisableFieldMixin(object):
    widget = SelectDisable
    _disabled_values = []

    def __init__(self, disabled_values=[], *args, **kwargs):

        if 'widget' in kwargs:
            widget = kwargs['widget']
            if isinstance(widget, Select) or \
                    (isclass(widget) and issubclass(widget, Select)):
                self.widget = SelectDisable()
            if isinstance(widget, SelectMultiple) or \
                    (isclass(widget) and issubclass(widget, SelectMultiple)):
                self.widget = SelectMultipleDisable()
            if isinstance(widget, CheckboxSelectMultiple) or \
                    (
                            isclass(widget) and
                            issubclass(widget, CheckboxSelectMultiple)
                    ):
                self.widget = CheckboxSelectMultipleDisable()

        super(DisableFieldMixin, self).__init__(*args, **kwargs)
        self.disabled_values = disabled_values

    def valid_value(self, value):
        try:
            if int(value) in self.disabled_values:
                return False
        except ValueError:
            pass
        if value in self.disabled_values:
            return False
        return super(DisableFieldMixin, self).valid_value(value)

    def _get_disabled_values(self):
        return self._disabled_values

    def _set_disabled_values(self, values):
        if type(values) == list and hasattr(self.widget, 'disabled_values'):
            self._disabled_values = self.widget.disabled_values = values

    disabled_values = property(_get_disabled_values, _set_disabled_values)


class OptionLabelFieldMixin(object):

    def __init__(self, *args, **kwargs):
        self.choice_label_transform = \
            kwargs.pop('choice_label_transform', None)
        super(OptionLabelFieldMixin, self).__init__(*args, **kwargs)

    def label_from_instance(self, user):
        if self.choice_label_transform is not None:
            return self.choice_label_transform(user)
        return super(OptionLabelFieldMixin, self).label_from_instance(user)


class ChoiceDisableField(DisableFieldMixin, ChoiceField):
    widget = SelectDisable


class MultipleChoiceDisableField(DisableFieldMixin, MultipleChoiceField):
    widget = SelectMultipleDisable


class CustomModelChoiceField(
    OptionLabelFieldMixin, DisableFieldMixin, ModelChoiceField
):
    widget = SelectDisable


class MultipleChoiceDisableModelField(DisableFieldMixin, ModelMultipleChoiceField):
    widget = SelectMultipleDisable


class OrderedModelMultipleChoiceField(ModelMultipleChoiceField):
    def _check_values(self, value):
        items = super(OrderedModelMultipleChoiceField, self)._check_values(
            value
        )
        key = self.to_field_name or 'pk'
        map = {
            getattr(item, key): item
            for item in items
        }
        return [map[v] for v in value]


class VisitEventTimeField(ChoiceField):

    model = EventTime

    # Minor hack to validate that the selected eventtime is still available.
    # Otherwise there can be a race condition between two guests: Both open the
    # form, and guest 1 takes the only remaining seats. Guest 2 must then see
    # an error
    # This would also be caught in ChoiceField.clean(), but throwing a
    # nonsensical error
    def clean(self, value):
        try:
            eventtime = self.model.objects.get(pk=value)
            if eventtime.visit is not None:
                if not eventtime.visit.is_bookable and \
                        not eventtime.visit.can_join_waitinglist:
                    raise ValidationError(
                        _(u'Det valgte tidspunkt er blevet lukket for booking')
                    )
        except self.model.DoesNotExist:
            pass
        except ValueError:
            pass
        return super(ChoiceField, self).clean(value)
