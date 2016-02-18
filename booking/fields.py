from django.db import models
from django.utils import six
from collections import defaultdict
from django.forms.fields import MultipleChoiceField

from .widgets import DurationWidget


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
