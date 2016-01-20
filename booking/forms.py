from booking.models import StudyMaterial, PostCode
from booking.models import UnitType
from booking.models import Unit
from booking.models import Visit
from booking.models import Booker, Region, ClassBooking, School
from django import forms
from django.forms import CheckboxSelectMultiple, EmailInput
from django.forms import inlineformset_factory
from django.forms import TextInput, NumberInput, Textarea, DateTimeInput
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
                  'time', 'duration', 'locality', 'rooms_assignment',
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


class BookerForm(forms.ModelForm):
    class Meta:
        model = Booker
        fields = ('firstname', 'lastname', 'email', 'phone', 'line',
                  #'school',
                  'level', 'notes')
        widgets = {
            'firstname': TextInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Fornavn'}
            ),
            'lastname': TextInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Efternavn'}
            ),
            'email': EmailInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Email'}
            ),
            'phone': TextInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Telefonnummer',
                           'pattern': '(\(\+\d+\)|\+\d+)?\s*\d+[ \d]*'}
            ),
            'notes': Textarea(
                    attrs={'class': 'form-control input-sm'}
            )
        }

    repeatemail = forms.CharField(
            widget=TextInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Gentag email'}
            )
    )
    school = forms.CharField(
            widget=TextInput(
                    attrs={'class': 'form-control input-sm',
                           'autocomplete': 'off'}
            )
    )
    postcode = forms.IntegerField(
            widget=NumberInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'Postnummer',
                           'min': '1000', 'max': '9999'}
            )
    )
    city = forms.CharField(
            widget=TextInput(
                    attrs={'class': 'form-control input-sm',
                           'placeholder': 'By'}
            )
    )
    region = forms.ModelChoiceField(
            queryset=Region.objects.all()
    )

    def clean(self):
        cleaned_data = super(BookerForm, self).clean()
        email = cleaned_data.get("email")
        repeatemail = cleaned_data.get("repeatemail")

        if email is not None and repeatemail is not None \
                and email != repeatemail:
            error = forms.ValidationError(u"Indtast den samme email-adresse " +
                                          u"i begge felter")
            self.add_error('repeatemail', error)

    def save(self):
        booker = super(BookerForm, self).save(commit=False)
        data = self.cleaned_data
        schoolname = data.get('school')
        try:
            school = School.objects.get(name__iexact=schoolname)
        except:
            school = School()
            school.name = schoolname
            school.postcode = PostCode.objects.get(number=data.get('postcode'))
            school.save()
        booker.school = school
        booker.save()
        return booker


class ClassBookingForm(forms.ModelForm):

    class Meta:
        model = ClassBooking
        fields = ('student_count', 'teacher_count', 'time', 'tour_desired',
                  'notes',)
        widgets = {
            'student_count': NumberInput(attrs={'class': 'form-control input-sm'}),
            'teacher_count': NumberInput(attrs={'class': 'form-control input-sm'}),
            'time': DateTimeInput(attrs={'class': 'form-control input-sm'}),
            'notes': Textarea(attrs={'class': 'form-control input-sm'})
        }