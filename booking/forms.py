from booking.models import StudyMaterial
from booking.models import UnitType
from booking.models import Unit
from booking.models import Visit, VisitOccurrence
from booking.models import Booker, Region, PostCode, School
from booking.models import ClassBooking, TeacherBooking
from django import forms
from django.forms import CheckboxSelectMultiple, RadioSelect, EmailInput
from django.forms import inlineformset_factory
from django.forms import TextInput, NumberInput, Textarea, Select
from django.utils.translation import ugettext_lazy as _
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
    required_css_class = 'required'

    class Meta:
        model = Visit
        fields = ('title', 'teaser', 'description', 'price',
                  'type', 'tags', 'preparation_time', 'comment',
                  'institution_level', 'topics', 'level', 'class_level_min',
                  'class_level_max', 'subjects', 'audience',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'recurrences', 'duration', 'locality', 'rooms_assignment',
                  'rooms_needed',
                  'enabled', 'contact_persons', 'unit',)
        widgets = {
            'title': TextInput(attrs={
                'class': 'titlefield',
                'rows': 1, 'size': 62
            }),
            'teaser': Textarea(attrs={
                'rows': 3,
                'cols': 70,
                'maxlength': 210
            }),
            'description': TinyMCE(attrs={'rows': 10}),
            'minimum_number_of_visitors': NumberInput(attrs={'min': 1}),
            'maximum_number_of_visitors': NumberInput(attrs={'min': 1}),
            'tags': CheckboxSelectMultiple(),
            'topics': CheckboxSelectMultiple(),
            'contact_persons': CheckboxSelectMultiple(),
            'subjects': CheckboxSelectMultiple(),
            'audience': RadioSelect()
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
        return user.userprofile.get_unit_queryset()


VisitStudyMaterialFormBase = inlineformset_factory(Visit,
                                                   StudyMaterial,
                                                   fields=('file',),
                                                   can_delete=True, extra=1)


class VisitStudyMaterialForm(VisitStudyMaterialFormBase):

    def __init__(self, data, instance=None):
        super(VisitStudyMaterialForm, self).__init__(data)
        self.studymaterials = StudyMaterial.objects.filter(visit=instance)


class BookingForm(forms.ModelForm):

    def __init__(self, data=None, visit=None, *args, **kwargs):
        super(BookingForm, self).__init__(data, *args, **kwargs)


class BookerForm(BookingForm):

    class Meta:
        model = Booker
        fields = ('firstname', 'lastname', 'email', 'phone', 'line',
                  'level', 'attendee_count', 'notes')
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
                       'pattern': '(\(\+\d+\)|\+\d+)?\s*\d+[ \d]*'},
            ),
            'line': Select(
                attrs={'class': 'selectpicker form-control'}
            ),
            'level': Select(
                attrs={'class': 'selectpicker form-control'}
            ),
            'attendee_count': NumberInput(
                attrs={'class': 'form-control input-sm', 'min': 0}
            ),
            'notes': Textarea(
                attrs={'class': 'form-control input-sm'}
            ),

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
        ),
        required=False
    )
    city = forms.CharField(
        widget=TextInput(
            attrs={'class': 'form-control input-sm',
                   'placeholder': 'By'}
        ),
        required=False
    )
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=Select(
            attrs={'class': 'selectpicker form-control'}
        ),
        required=False
    )

    def __init__(self, data=None, visit=None, *args, **kwargs):
        super(BookerForm, self).__init__(data, *args, **kwargs)
        attendeecount_widget = self.fields['attendee_count'].widget
        attendeecount_widget.attrs['min'] = 1
        if visit is not None:
            if visit.minimum_number_of_visitors is not None:
                attendeecount_widget.attrs['min'] = \
                    visit.minimum_number_of_visitors
            if visit.maximum_number_of_visitors is not None:
                attendeecount_widget.attrs['max'] = \
                    visit.maximum_number_of_visitors

    def clean_postcode(self):
        postcode = self.cleaned_data.get('postcode')
        if postcode is not None:
            try:
                PostCode.objects.get(number=postcode)
            except:
                raise forms.ValidationError(u"Ukendt postnummer")

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


class ClassBookingForm(BookingForm):

    class Meta:
        model = ClassBooking
        fields = ('tour_desired',)

    time = forms.ChoiceField(
        widget=Select(
            attrs={'class': 'selectpicker form-control'}
        ),
        required=False
    )
    desired_time = forms.CharField(
        widget=Textarea(attrs={'class': 'form-control input-sm'}),
        required=False
    )

    scheduled = False

    def __init__(self, data=None, visit=None, *args, **kwargs):
        super(ClassBookingForm, self).__init__(data, *args, **kwargs)

        # self.scheduled = visit is not None and \
        #    visit.type == Resource.FIXED_SCHEDULE_GROUP_VISIT
        self.scheduled = visit is not None

        if self.scheduled:
            time_choices = [
                (x.id, x.start_datetime.strftime("%d-%m-%Y %H:%M"))
                for x in visit.visitoccurrence_set.all()
                ]
            self.fields['time'].choices = time_choices
            self.fields['time'].required = True
        else:
            self.fields['desired_time'].required = True

    def save(self, commit=True, *args, **kwargs):
        booking = super(ClassBookingForm, self).save(commit=False)
        data = self.cleaned_data
        if self.scheduled:
            occurrence_id = data.get("time")
            try:
                occurrence = VisitOccurrence.objects.get(id=occurrence_id)
                booking.time = occurrence.start_datetime
            except:
                pass
        if commit:
            booking.save(*args, **kwargs)
        return booking


class TeacherBookingForm(BookingForm):
    class Meta:
        model = TeacherBooking
        fields = ('subjects', )
