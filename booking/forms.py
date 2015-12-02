from django import forms
from booking.models import UnitType
from booking.models import Unit
from booking.models import Visit
from booking.models import StudyMaterial
from django.forms import inlineformset_factory, TextInput


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
                  'institution_level', 'topics', 'level', 'class_level_min',
                  'class_level_max',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'time', 'duration', 'locality', 'room',
                  'enabled', 'contact_persons')
        widgets = {
            'title': TextInput(attrs={'class':'titlefield'})
        }

    def clean_locality(self):
        data = self.cleaned_data
        locality = data.get("locality")
        if locality is None:
            raise forms.ValidationError("This field is required")
        return locality


VisitStudyMaterialForm = inlineformset_factory(Visit,
                                               StudyMaterial, fields=('file',),
                                               can_delete=True, extra=1)
