from django import forms
from booking.models import UnitType
from booking.models import Unit
from booking.models import Visit


class UnitTypeForm(forms.ModelForm):
    class Meta:
        model = UnitType
        fields = ('name',)


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ('name', 'type', 'parent')


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ('title', 'teaser', 'description', 'price',
                  'type', 'tags',
                  'institution_level', 'topics', 'level', 'class_level_min', 'class_level_max',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'time', 'duration', 'locality', 'room',
                  'enabled', 'contact_persons')
