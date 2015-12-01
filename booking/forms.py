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
        fields = ('title', 'description', 'price',
                  'type', 'tags',
                  'audience', 'topics', 'level', 'maximum_number_of_visitors',
                  'locality', 'room',
                  'contact_persons')
