from django import forms
from booking.models import UnitType

class UnitTypeForm(forms.ModelForm):
    class Meta:
        model = UnitType
        fields = ('name',)