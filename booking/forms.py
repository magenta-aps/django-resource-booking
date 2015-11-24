from django import forms
from booking.models import UnitType
from booking.models import Unit

class UnitTypeForm(forms.ModelForm):
    class Meta:
        model = UnitType
        fields = ('name',)


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ('name','type','parent')