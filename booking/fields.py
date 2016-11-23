from django.db import models
from django.utils import six
from collections import defaultdict
from django.forms.fields import ChoiceField, MultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple, Select, SelectMultiple
from django.forms.models import ModelMultipleChoiceField

from .widgets import OrderedMultipleHiddenChooser
from .widgets import CheckboxSelectMultipleDisable, DurationWidget
from .widgets import SelectDisable, SelectMultipleDisable

COLUMN_TYPES = defaultdict(lambda: "char(20)")
COLUMN_TYPES["django.db.backends.postgresql_psycopg2"] = "interval"
COLUMN_TYPES["django.contrib.gis.db.backends.postgis"] = "interval"


class DurationField(six.with_metaclass(models.SubfieldBase, models.Field)):
    """
        Store a datetime.timedelta as an INTERVAL in postgres, or a
        CHAR(20) in other database backends.
        """
    _south_introspects = True

    def __init__(self, labels=None, *args, **kwargs):
        super(DurationField, self).__init__(*args, **kwargs)
        self.labels = labels

    def formfield(self, **kwargs):
        labels = self.labels
        kwargs['widget'] = DurationWidget(day_label=labels.get('day'),
                                          hour_label=labels.get('hour'),
                                          minute_label=labels.get('minute'))
        return super(DurationField, self).formfield(**kwargs)

    def get_prep_value(self, value):
        if self.null and value == "":
            return None
        if (value is None) or isinstance(value, six.string_types):
            return value
        return str(value).replace(',', '')

    # Database stuff

    def db_type(self, connection):
        return COLUMN_TYPES[connection.settings_dict['ENGINE']]

    def get_db_prep_value(self, value, connection=None, prepared=None):
        return self.get_prep_value(value)


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
            if isinstance(widget, Select) or issubclass(widget, Select):
                self.widget = SelectDisable()
            if isinstance(widget, SelectMultiple) or \
                    issubclass(widget, SelectMultiple):
                self.widget = SelectMultipleDisable()
            if isinstance(widget, CheckboxSelectMultiple) or \
                    issubclass(widget, CheckboxSelectMultiple):
                self.widget = CheckboxSelectMultipleDisable()

        super(DisableFieldMixin, self).__init__(*args, **kwargs)
        self.disabled_values = disabled_values

    def valid_value(self, value):
        if value in self.disabled_values:
            return False
        return super(DisableFieldMixin, self).valid_value(value)

    def _get_disabled_values(self):
        return self._disabled_values

    def _set_disabled_values(self, values):
        if type(values) == list and hasattr(self.widget, 'disabled_values'):
            self.widget.disabled_values = [unicode(value) for value in values]

    disabled_values = property(_get_disabled_values, _set_disabled_values)


class ChoiceDisableField(DisableFieldMixin, ChoiceField):
    widget = SelectDisable


class MultipleChoiceDisableField(DisableFieldMixin, MultipleChoiceField):
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
