# -*- coding: utf-8 -*-

from booking.models import StudyMaterial, VisitAutosend, Booking
from booking.models import UnitType
from booking.models import Unit
from booking.models import Resource, OtherResource, Visit
from booking.models import Booker, Region, PostCode, School
from booking.models import ClassBooking, TeacherBooking, BookingSubjectLevel
from booking.models import EmailTemplate
from booking.models import VisitOccurrence
from django import forms
from django.contrib.auth.models import User
from django.forms import CheckboxSelectMultiple, RadioSelect, EmailInput
from django.forms import formset_factory, inlineformset_factory
from django.forms import TextInput, NumberInput, Textarea, Select
from django.forms import HiddenInput
from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from profile.models import HOST, TEACHER
from tinymce.widgets import TinyMCE
from .fields import ExtensibleMultipleChoiceField


class AdminVisitSearchForm(forms.Form):

    q = forms.CharField(
        label=_(u'Fritekst'),
        max_length=60,
        required=False
    )

    s = forms.ChoiceField(
        label=_(u'Status'),
        choices=(('', _(u'[Vælg status]')),) + Resource.state_choices,
        required=False
    )

    e = forms.ChoiceField(
        label=_(u'Tilbud er aktivt'),
        choices=(
            (None, _(u'[Vælg]')),
            (1, _(u'Ja')),
            (0, _(u'Nej')),
        ),
        required=False
    )

    IS_VISIT = 1
    IS_NOT_VISIT = 2

    v = forms.ChoiceField(
        label=_(u'Besøg / ikke besøg'),
        choices=(
            (None, _(u'[Vælg]')),
            (IS_VISIT, _(u'Tilbud med besøg')),
            (IS_NOT_VISIT, _(u'Tilbud uden besøg')),
        ),
        required=False
    )

    HAS_BOOKINGS = 1
    HAS_NO_BOOKINGS = 2

    b = forms.ChoiceField(
        label=_(u'Bookinger'),
        choices=(
            (None, _(u'[Vælg]')),
            (HAS_BOOKINGS, _(u'Tilbud der har bookinger')),
            (HAS_NO_BOOKINGS, _(u'Tilbud der ikke har bookinger')),
        ),
        required=False
    )

    MY_UNIT = -1
    MY_FACULTY = -2
    MY_UNITS = -3

    u = forms.ChoiceField(
        label=_(u'Enhed'),
        required=False
    )

    to_date = forms.DateField(
        label=_(u'Dato til'),
        required=False
    )

    from_date = forms.DateField(
        label=_(u'Dato fra'),
        required=False
    )

    def __init__(self, qdict, *args, **kwargs):
        self.user = kwargs.pop("user")

        super(AdminVisitSearchForm, self).__init__(qdict, *args, **kwargs)

        self.fields['u'].choices = self.get_unit_choices()

        extra_classes = {
            'from_date': 'datepicker datepicker-admin',
            'to_date': 'datepicker datepicker-admin'
        }

        # Add classnames to all fields
        for fname, f in self.fields.iteritems():
            f.widget.attrs['class'] = " ".join([
                x for x in (
                    f.widget.attrs.get('class'),
                    'form-control input-sm',
                    extra_classes.get(fname)
                ) if x
            ])

        self.hiddenfields = []
        for x in ("a", "t", "f", "g"):
            for y in qdict.getlist(x, []):
                self.hiddenfields.append((x, y,))

    def get_unit_choices(self):
        choices = [
            (None, _(u'[Vælg]')),
            (self.MY_UNIT, _(u'Tilbud under min enhed')),
            (self.MY_FACULTY, _(u'Tilbud under mit fakultet')),
            (
                self.MY_UNITS,
                _(u'Tilbud under alle enheder jeg kan administrere')
            ),
            (None, '======'),
        ]

        for x in self.user.userprofile.get_unit_queryset():
            choices.append((x.pk, unicode(x)))

        return choices

    def add_prefix(self, field_name):
        # Remove _date postfix from date fields
        if field_name in ('from_date', 'to_date'):
            field_name = field_name[:-5]

        return super(AdminVisitSearchForm, self).add_prefix(field_name)


class VisitOccurrenceSearchForm(forms.Form):
    q = forms.CharField(
        label=_(u'Fritekst'),
        max_length=60,
        required=False
    )

    t = forms.CharField(
        label=_(u'Tilbuds-ID'),
        max_length=10,
        required=False,
        widget=forms.widgets.NumberInput
    )

    MY_UNIT = -1
    MY_FACULTY = -2
    MY_UNITS = -3

    u = forms.ChoiceField(
        label=_(u'Enhed'),
        required=False
    )

    WORKFLOW_STATUS_PENDING = -1
    WORKFLOW_STATUS_READY = -2

    w = forms.ChoiceField(
        label=_(u'Workflow status'),
        choices=(
            ('', _(u'Alle')),
            (WORKFLOW_STATUS_PENDING, _(u'Alle der kræver handling')),
            (WORKFLOW_STATUS_READY, _(u'Alle planlagte')),
            ('', u'====='),
        ) + VisitOccurrence.workflow_status_choices,
        required=False
    )

    participant_choices = (
        ('', _(u'[Vælg]')),
        (1, 1),
        (5, 5),
    ) + tuple((x, x) for x in range(10, 60, 10))

    p_min = forms.ChoiceField(
        label=_(u'Minimum antal deltagere'),
        choices=participant_choices,
        required=False
    )

    p_max = forms.ChoiceField(
        label=_(u'Maksimum antal deltagere'),
        choices=participant_choices,
        required=False
    )

    from_date = forms.DateField(
        label=_(u'Dato fra'),
        input_formats=['%d-%m-%Y'],
        required=False
    )

    to_date = forms.DateField(
        label=_(u'Dato til'),
        input_formats=['%d-%m-%Y'],
        required=False
    )

    def __init__(self, qdict, *args, **kwargs):
        self.user = kwargs.pop("user")

        qdict = qdict.copy()

        # Set some defaults if form was not submitted
        if not qdict.get("go", False):
            if qdict.get("u", "") == "":
                qdict["u"] = self.MY_UNITS

            if qdict.get("s", "") == "":
                qdict["s"] = Resource.ACTIVE

        super(VisitOccurrenceSearchForm, self).__init__(qdict, *args, **kwargs)

        self.fields['u'].choices = self.get_unit_choices()

        extra_classes = {
            'from_date': 'datepicker datepicker-admin',
            'to_date': 'datepicker datepicker-admin'
        }

        # Add classnames to all fields
        for fname, f in self.fields.iteritems():
            f.widget.attrs['class'] = " ".join([
                x for x in (
                    f.widget.attrs.get('class'),
                    'form-control input-sm',
                    extra_classes.get(fname)
                ) if x
            ])

    def get_unit_choices(self):
        choices = [
            (None, _(u'[Vælg]')),
            (self.MY_UNIT, _(u'Tilbud under min enhed')),
            (self.MY_FACULTY, _(u'Tilbud under mit fakultet')),
            (
                self.MY_UNITS,
                _(u'Tilbud under alle enheder jeg kan administrere')
            ),
            (None, '======'),
        ]

        for x in self.user.userprofile.get_unit_queryset():
            choices.append((x.pk, unicode(x)))

        return choices


class UnitTypeForm(forms.ModelForm):
    class Meta:
        model = UnitType
        fields = ('name',)


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ('name', 'type', 'parent')


class ResourceInitialForm(forms.Form):
    type = forms.ChoiceField(
        choices=Resource.resource_type_choices
    )


class OtherResourceForm(forms.ModelForm):
    required_css_class = 'required'

    class Meta:
        model = OtherResource
        fields = ('title', 'teaser', 'description', 'price', 'state',
                  'type', 'tags',
                  'institution_level', 'topics', 'audience',
                  'locality',
                  'contact_persons', 'unit',
                  'preparation_time', 'comment'
                  )
        widgets = {
            'title': TextInput(attrs={
                'class': 'titlefield form-control input-sm'
            }),
            'teaser': Textarea(attrs={
                'rows': 3,
                'cols': 70,
                'maxlength': 1000,
                'class': 'form-control input-sm'
            }),
            'description': TinyMCE(attrs={
                'rows': 10,
                'cols': 90
            }),
            'tags': CheckboxSelectMultiple(),
            'topics': CheckboxSelectMultiple(),
            'audience': RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(OtherResourceForm, self).__init__(*args, **kwargs)
        self.fields['unit'].queryset = self.get_unit_query_set()
        self.fields['type'].widget = HiddenInput()

    def get_unit_query_set(self):
        """"Get units for which user can create events."""
        user = self.user
        return user.userprofile.get_unit_queryset()


class VisitForm(forms.ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Visit
        fields = ('title', 'teaser', 'description', 'price', 'state',
                  'type', 'tags',
                  'institution_level', 'topics', 'audience',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'duration', 'locality', 'rooms_assignment',
                  'rooms_needed', 'tour_available',
                  'contact_persons', 'unit',
                  'needed_hosts', 'needed_teachers',
                  'preparation_time', 'comment',
                  )

        widgets = {
            'title': TextInput(attrs={
                'class': 'titlefield form-control input-sm',
                'rows': 1, 'size': 62
            }),
            'teaser': Textarea(
                attrs={
                    'class': 'form-control input-sm',
                    'rows': 3,
                    'cols': 70,
                    'maxlength': 210
                }
            ),
            'description': TinyMCE(attrs={'rows': 10, 'cols': 90}),

            'price': NumberInput(attrs={'class': 'form-control input-sm'}),
            'type': Select(attrs={'class': 'form-control input-sm'}),
            'preparation_time': NumberInput(
                attrs={'class': 'form-control input-sm'}
            ),
            'comment': Textarea(attrs={'class': 'form-control input-sm'}),
            'institution_level': Select(
                attrs={'class': 'form-control input-sm'}
            ),
            'minimum_number_of_visitors': NumberInput(
                attrs={'class': 'form-control input-sm', 'min': 1}
            ),
            'maximum_number_of_visitors': NumberInput(
                attrs={'class': 'form-control input-sm', 'min': 1}
            ),
            'duration': Select(attrs={'class': 'form-control input-sm'}),
            'locality': Select(attrs={'class': 'form-control input-sm'}),
            'rooms_assignment': Select(
                attrs={'class': 'form-control input-sm'}
            ),
            'unit': Select(attrs={'class': 'form-control input-sm'}),
            'audience': RadioSelect(),
            'tags': CheckboxSelectMultiple(),
            'contact_persons': CheckboxSelectMultiple(),
            'room_responsible': CheckboxSelectMultiple(),
            'default_hosts': CheckboxSelectMultiple(),
            'default_teachers': CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        # Provide defaults for needed_-fields if not present in submit data.
        if 'data' in kwargs:
            kwargs['data']['needed_hosts'] = kwargs['data'].get(
                'needed_hosts', 0
            )
            kwargs['data']['needed_teachers'] = kwargs['data'].get(
                'needed_teachers', 0
            )

        self.user = kwargs.pop('user')
        super(VisitForm, self).__init__(*args, **kwargs)
        self.fields['unit'].queryset = self.get_unit_query_set()
        self.fields['type'].widget = HiddenInput()

        # Not all resources have hosts and teachers!
        if 'default_hosts' in self.fields \
                and 'default_teachers' in self.fields:
            # The operation is 'update'
            if kwargs['instance'] and kwargs['instance'].unit_id:
                self.fields['default_hosts'].queryset = User.objects.filter(
                    userprofile__user_role__role=HOST,
                    userprofile__unit_id=kwargs['instance'].unit_id
                )
                self.fields['default_teachers'].queryset = \
                    User.objects.filter(
                        userprofile__user_role__role=TEACHER,
                        userprofile__unit_id=kwargs['instance'].unit_id
                    )
            else:  # The operation is 'create'
                self.fields['default_hosts'].queryset = User.objects.filter(
                    userprofile__user_role__role=HOST,
                    userprofile__unit__in=self.get_unit_query_set()
                )
                self.fields['default_teachers'].queryset = \
                    User.objects.filter(
                        userprofile__user_role__role=TEACHER,
                        userprofile__unit__in=self.get_unit_query_set()
                    )
        # Add classes to certain widgets
        for x in ('needed_hosts', 'needed_teachers'):
            f = self.fields.get(x)
            if f is not None:
                f.widget.attrs['class'] = " ".join([
                    x for x in (
                        f.widget.attrs.get('class'),
                        'form-control input-sm'
                    ) if x
                ])

    def clean_type(self):
        instance = getattr(self, 'instance', None)
        if instance:
            return instance.type
        else:
            return self.cleaned_data['type']

    def clean(self):
        cleaned_data = super(VisitForm, self).clean()
        min_visitors = cleaned_data.get('minimum_number_of_visitors')
        max_visitors = cleaned_data.get('maximum_number_of_visitors')
        if min_visitors is not None and max_visitors is not None and \
           min_visitors > max_visitors:
            min_error_msg = _(u"The minimum numbers of visitors " +
                              u"must not be larger than " +
                              u"the maximum number of visitors")
            max_error_msg = _(u"The maximum numbers of visitors " +
                              u"must not be smaller than " +
                              u"the minimum number of visitors")
            self.add_error('minimum_number_of_visitors', min_error_msg)
            self.add_error('maximum_number_of_visitors', max_error_msg)
            raise forms.ValidationError(min_error_msg)

    def get_unit_query_set(self):
        """"Get units for which user can create events."""
        user = self.user
        return user.userprofile.get_unit_queryset()


class StudentForADayForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics', 'audience',
                  'duration', 'locality',
                  'contact_persons', 'unit',
                  'needed_hosts', 'needed_teachers',
                  'preparation_time', 'comment',
                  'default_hosts', 'default_teachers',
                  )
        widgets = VisitForm.Meta.widgets


class InternshipForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics', 'audience',
                  'locality',
                  'contact_persons', 'unit',
                  'preparation_time', 'comment',
                  )
        widgets = VisitForm.Meta.widgets


class OpenHouseForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics', 'audience',
                  'locality', 'rooms_assignment', 'rooms_needed',
                  'contact_persons', 'unit',
                  'preparation_time', 'comment',
                  )
        widgets = VisitForm.Meta.widgets


class TeacherVisitForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics', 'audience',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'duration', 'locality', 'rooms_assignment',
                  'rooms_needed',
                  'contact_persons', 'room_responsible', 'unit',
                  'needed_hosts', 'needed_teachers',
                  'preparation_time', 'comment',
                  'default_hosts', 'default_teachers',
                  )
        widgets = VisitForm.Meta.widgets


class ClassVisitForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics', 'audience',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'duration', 'locality', 'rooms_assignment',
                  'rooms_needed', 'tour_available',
                  'contact_persons', 'room_responsible', 'unit',
                  'needed_hosts', 'needed_teachers',
                  'preparation_time', 'comment',
                  'default_hosts', 'default_teachers',
                  )
        widgets = VisitForm.Meta.widgets


class StudyProjectForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics', 'audience',
                  'locality',
                  'rooms_assignment', 'rooms_needed',
                  'contact_persons', 'unit',
                  'preparation_time', 'comment',
                  )
        widgets = VisitForm.Meta.widgets


class AssignmentHelpForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics', 'audience',
                  'contact_persons', 'unit',
                  'comment',
                  )
        widgets = VisitForm.Meta.widgets


class StudyMaterialForm(VisitForm):
    class Meta:
        model = Visit
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics', 'audience',
                  'contact_persons', 'unit',
                  'comment'
                  )
        widgets = VisitForm.Meta.widgets


class OtherVisitForm(VisitForm):
    class Meta:
        model = Visit
        fields = VisitForm.Meta.fields
        widgets = VisitForm.Meta.widgets


ResourceStudyMaterialFormBase = inlineformset_factory(Resource,
                                                      StudyMaterial,
                                                      fields=('file',),
                                                      can_delete=True, extra=1)


class ResourceStudyMaterialForm(ResourceStudyMaterialFormBase):

    def __init__(self, data, instance=None):
        super(ResourceStudyMaterialForm, self).__init__(data)
        self.studymaterials = StudyMaterial.objects.filter(resource=instance)


VisitAutosendFormSetBase = inlineformset_factory(
    Visit,
    VisitAutosend,
    fields=('template_key', 'enabled', 'days'),
    can_delete=True,
    min_num=1,
    extra=len(EmailTemplate.default)
)


class VisitAutosendFormSet(VisitAutosendFormSetBase):

    def is_valid(self):
        return True

    def clean(self):
        cleaned_forms = []
        for form in self.forms:
            if form.is_valid():
                cleaned_forms.append(form)
        self.forms = cleaned_forms


class BookingForm(forms.ModelForm):

    scheduled = False

    class Meta:
        model = Booking
        fields = ()
        labels = {
            'visitoccurrence': _(u"Tidspunkt")
        },
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, visit=None, *args, **kwargs):
        super(BookingForm, self).__init__(data, *args, **kwargs)

        self.visit = visit
        # self.scheduled = visit is not None and \
        #    visit.type == Resource.FIXED_SCHEDULE_GROUP_VISIT
        self.scheduled = (
            visit is not None and
            len(visit.future_events) > 0
        )
        if self.scheduled:
            self.fields['visitoccurrence'].choices = (
                (
                    x.pk,
                    formats.date_format(x.start_datetime, "DATETIME_FORMAT")
                )
                for x in visit.future_events.order_by('start_datetime')
            )
            self.fields['visitoccurrence'].required = True


class BookerForm(forms.ModelForm):

    class Meta:
        model = Booker
        fields = ('firstname', 'lastname', 'email', 'phone', 'line',
                  'level', 'attendee_count')
        widgets = {
            'firstname': TextInput(
                attrs={'class': 'form-control input-sm',
                       'placeholder': _(u'Fornavn')}
            ),
            'lastname': TextInput(
                attrs={'class': 'form-control input-sm',
                       'placeholder': _(u'Efternavn')}
            ),
            'email': EmailInput(
                attrs={'class': 'form-control input-sm',
                       'placeholder': _(u'Email')}
            ),
            'phone': TextInput(
                attrs={'class': 'form-control input-sm',
                       'placeholder': _(u'Telefonnummer'),
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
        }

    repeatemail = forms.CharField(
        widget=TextInput(
            attrs={'class': 'form-control input-sm',
                   'placeholder': _(u'Gentag email')}
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
                   'placeholder': _(u'Postnummer'),
                   'min': '1000', 'max': '9999'}
        ),
        required=False
    )
    city = forms.CharField(
        widget=TextInput(
            attrs={'class': 'form-control input-sm',
                   'placeholder': _(u'By')}
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

    def __init__(self, data=None, visit=None, language='da', *args, **kwargs):
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

            self.fields['school'].widget.attrs['data-institution-level'] = \
                visit.institution_level

            available_level_choices = Booker.level_map[visit.institution_level]
            self.fields['level'].choices = [(u'', u'---------')] + [
                (value, title)
                for (value, title) in Booker.level_choices
                if value in available_level_choices
            ]

        # Eventually we may want a prettier solution,
        # but for now this will have to do
        if language == 'en':
            self.fields['region'].choices = [
                (
                    region.id,
                    region.name_en
                    if region.name_en is not None else region.name
                )
                for region in Region.objects.all()
            ]

    def clean_postcode(self):
        postcode = self.cleaned_data.get('postcode')
        if postcode is not None:
            try:
                PostCode.objects.get(number=postcode)
            except:
                raise forms.ValidationError(_(u'Ukendt postnummer'))
        return postcode

    def clean(self):
        cleaned_data = super(BookerForm, self).clean()
        email = cleaned_data.get("email")
        repeatemail = cleaned_data.get("repeatemail")

        if email is not None and repeatemail is not None \
                and email != repeatemail:
            error = forms.ValidationError(
                _(u"Indtast den samme email-adresse i begge felter")
            )
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
        fields = ('tour_desired', 'visitoccurrence', 'notes')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets

    desired_time = forms.CharField(
        widget=Textarea(attrs={'class': 'form-control input-sm'}),
        required=False
    )

    def __init__(self, data=None, visit=None, *args, **kwargs):
        super(ClassBookingForm, self).__init__(data, visit, *args, **kwargs)

        if not self.scheduled:
            self.fields['desired_time'].required = True

        if self.visit is not None and not self.visit.tour_available:
            del self.fields['tour_desired']

    def save(self, commit=True, *args, **kwargs):
        booking = super(ClassBookingForm, self).save(commit=False)
        data = self.cleaned_data

        if 'tour_desired' not in data:
            data['tour_desired'] = False
            booking.tour_desired = False
        if commit:
            booking.save(*args, **kwargs)
        return booking


class TeacherBookingForm(BookingForm):
    class Meta:
        model = TeacherBooking
        fields = ('subjects', 'notes', 'visitoccurrence')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


class StudentForADayBookingForm(BookingForm):
    class Meta:
        model = Booking
        fields = ('notes', 'visitoccurrence')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


class StudyProjectBookingForm(BookingForm):
    class Meta:
        model = Booking
        fields = ('notes', 'visitoccurrence')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


BookingSubjectLevelForm = \
    inlineformset_factory(ClassBooking,
                          BookingSubjectLevel,
                          fields=('subject', 'level'),
                          can_delete=True,
                          extra=1,
                          widgets={
                              'subject': Select(
                                  attrs={'class': 'form-control'}
                              ),
                              'level': Select(
                                  attrs={'class': 'form-control'}
                              )
                          }
                          )


class EmailTemplateForm(forms.ModelForm):

    class Meta:
        model = EmailTemplate
        fields = ('key', 'subject', 'body', 'unit')
        widgets = {
            'subject': TextInput(attrs={'class': 'form-control'}),
            'body': Textarea(attrs={'rows': 10, 'cols': 90}),
            # 'body': TinyMCE(attrs={'rows': 10, 'cols': 90}),
        }

    def __init__(self, user, *args, **kwargs):
        super(EmailTemplateForm, self).__init__(*args, **kwargs)
        self.fields['unit'].choices = [(None, u'---------')] + [
            (x.pk, unicode(x))
            for x in user.userprofile.get_unit_queryset()]


class EmailTemplatePreviewContextEntryForm(forms.Form):
    key = forms.CharField(
        max_length=256,
        widget=TextInput(attrs={'class': 'form-control emailtemplate-key'})
    )
    type = forms.ChoiceField(
        choices=(
            ('string', 'String'),
            ('Unit', 'Unit'),
            # ('OtherResource': OtherResource),
            ('Visit', 'Visit'),
            ('VisitOccurrence', 'VisitOccurrence'),
            # ('StudyMaterial', StudyMaterial),
            # ('Resource',Resource),
            # ('Subject', Subject),
            # ('GymnasieLevel', GymnasieLevel),
            # ('Room', Room),
            # ('PostCode', PostCode),
            # ('School', School),
            ('Booking', 'Booking'),
        ),
        widget=Select(attrs={'class': 'form-control emailtemplate-type'})
    )
    value = forms.CharField(
        max_length=1024,
        widget=TextInput(
            attrs={
                'class': 'form-control emailtemplate-value '
                         'emailtemplate-type-string'
            }
        )
    )

EmailTemplatePreviewContextForm = formset_factory(
    EmailTemplatePreviewContextEntryForm
)


class BaseEmailComposeForm(forms.Form):
    required_css_class = 'required'

    body = forms.CharField(
        max_length=65584,
        # widget=TinyMCE(attrs={'rows': 10, 'cols': 90}),
        widget=Textarea(attrs={'rows': 10, 'cols': 90}),
        label=_(u'Tekst')
    )


class EmailComposeForm(BaseEmailComposeForm):

    recipients = ExtensibleMultipleChoiceField(
        label=_(u'Modtagere'),
        widget=CheckboxSelectMultiple
    )

    subject = forms.CharField(
        max_length=77,
        label=_(u'Emne'),
        widget=TextInput(attrs={
            'class': 'form-control'
        })
    )


class GuestEmailComposeForm(BaseEmailComposeForm):

    name = forms.CharField(
        max_length=100,
        label=_(u'Navn'),
        widget=TextInput(
            attrs={
                'class': 'form-control input-sm',
                'placeholder': _(u'Dit navn')
            }
        )
    )

    email = forms.EmailField(
        label=_(u'Email'),
        widget=EmailInput(
            attrs={
                'class': 'form-control input-sm',
                'placeholder': _(u'Din email-adresse')
            }
        )
    )

    phone = forms.CharField(
        label=_(u'Telefon'),
        widget=TextInput(
            attrs={
                'class': 'form-control input-sm',
                'placeholder': _(u'Dit telefonnummer'),
                'pattern': '(\(\+\d+\)|\+\d+)?\s*\d+[ \d]*'
            },
        ),
        required=False
    )


class EmailReplyForm(forms.Form):
    reply = forms.CharField(
        label=_(u'Mit svar'),
        widget=Textarea(attrs={'class': 'form-control input-sm'}),
        required=True
    )
