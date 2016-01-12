from booking.models import StudyMaterial
from booking.models import UnitType
from booking.models import Unit
from booking.models import Visit
from django import forms
from django.forms import CheckboxSelectMultiple
from django.forms import inlineformset_factory
from django.forms import TextInput, NumberInput, Textarea
from django.utils.translation import ugettext_lazy as _
from profile.models import COORDINATOR
from tinymce.widgets import TinyMCE


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
                  'type', 'tags', 'preparation_time', 'comment',
                  'institution_level', 'topics', 'level', 'class_level_min',
                  'class_level_max',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'recurrences', 'duration', 'locality', 'rooms_assignment',
                  'rooms_needed',
                  'enabled', 'contact_persons', 'unit',)
        widgets = {
            'title': TextInput(attrs={'class': 'titlefield'}),
            'teaser': Textarea(attrs={'rows': 3, 'maxlength': 1000}),
            'description': TinyMCE(attrs={'rows': 10}),
            'minimum_number_of_visitors': NumberInput(attrs={'min': 1}),
            'maximum_number_of_visitors': NumberInput(attrs={'min': 1}),
            'tags': CheckboxSelectMultiple(),
            'topics': CheckboxSelectMultiple(),
            'contact_persons': CheckboxSelectMultiple(),
        }

    def clean_locality(self):
        data = self.cleaned_data
        locality = data.get("locality")
        if locality is None:
            raise forms.ValidationError("This field is required")
        return locality

    def clean(self):
        cleaned_data = super(VisitForm, self).clean()
        min_visitors = cleaned_data.get('minimum_number_of_visitors')
        max_visitors = cleaned_data.get('maximum_number_of_visitors')
        if min_visitors > max_visitors:
            min_error_msg = _(u"The minimum numbers of visitors " +
                              u"must not be larger than " +
                              u"the maximum number of visitors")
            max_error_msg = _(u"The maximum numbers of visitors " +
                              u"must not be smaller than " +
                              u"the minimum number of visitors")
            self.add_error('minimum_number_of_visitors', min_error_msg)
            self.add_error('maximum_number_of_visitors', max_error_msg)
            raise forms.ValidationError(min_error_msg)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(VisitForm, self).__init__(*args, **kwargs)
        self.fields['unit'].queryset = self.get_unit_query_set()

    def get_unit_query_set(self):
        """"Get units for which user can create events."""
        user = self.user
        if user.userprofile.get_role() == COORDINATOR:
            uu = user.userprofile.unit
            if uu is not None:
                qs = uu.get_descendants()
            else:
                qs = Unit.objects.none()
        else:
            # User must be an administrator and may attach any unit.
            qs = Unit.objects.all()
        return qs


VisitStudyMaterialFormBase = inlineformset_factory(Visit,
                                                   StudyMaterial,
                                                   fields=('file',),
                                                   can_delete=True, extra=1)


class VisitStudyMaterialForm(VisitStudyMaterialFormBase):

    def __init__(self, data, instance=None):
        super(VisitStudyMaterialForm, self).__init__(data)
        self.studymaterials = StudyMaterial.objects.filter(visit=instance)
