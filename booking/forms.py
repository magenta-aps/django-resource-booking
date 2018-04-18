# -*- coding: utf-8 -*-
import sys

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.core import validators
from django.db.models import Q
from django.db.models.expressions import OrderBy
from django.forms import CheckboxSelectMultiple, CheckboxInput
from django.forms import EmailInput
from django.forms import HiddenInput
from django.forms import ModelMultipleChoiceField
from django.forms import TextInput, NumberInput, DateInput, Textarea, Select
from django.forms import formset_factory, inlineformset_factory
from django.template import TemplateSyntaxError
from django.utils.translation import ugettext_lazy as _

from booking.models import BLANK_LABEL, BLANK_OPTION
from booking.models import ClassBooking, TeacherBooking, \
    BookingGymnasieSubjectLevel
from booking.models import EmailTemplate, EmailTemplateType
from booking.models import Evaluation
from booking.models import EvaluationGuest
from booking.models import Guest, Region, PostCode, School
from booking.models import Locality, OrganizationalUnitType, OrganizationalUnit
from booking.models import MultiProductVisitTemp, MultiProductVisitTempProduct
from booking.models import Product
from booking.models import StudyMaterial, ProductAutosend, Booking
from booking.models import Subject, BookingGrundskoleSubjectLevel
from booking.models import Visit
from booking.utils import binary_or, binary_and, TemplateSplit
from booking.widgets import OrderedMultipleHiddenChooser
from .fields import ExtensibleMultipleChoiceField, VisitEventTimeField
from .fields import OrderedModelMultipleChoiceField


class AdminProductSearchForm(forms.Form):

    q = forms.CharField(
        label=_(u'Fritekst'),
        max_length=60,
        required=False
    )

    s = forms.ChoiceField(
        label=_(u'Status'),
        choices=(('', _(u'[Vælg status]')),) + Product.state_choices,
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

        super(AdminProductSearchForm, self).__init__(qdict, *args, **kwargs)

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
        for x in ("a", "t", "f", "g", "i"):
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

        return super(AdminProductSearchForm, self).add_prefix(field_name)


class VisitSearchForm(forms.Form):
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
        label=_(u'Status'),
        choices=(
            ('', _(u'Alle')),
            (WORKFLOW_STATUS_PENDING, _(u'Alle ikke-planlagte')),
            (WORKFLOW_STATUS_READY, _(u'Alle planlagte')),
            ('', u'====='),
        ) + Visit.workflow_status_choices,
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
                qdict["s"] = Product.ACTIVE

        super(VisitSearchForm, self).__init__(qdict, *args, **kwargs)

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


class OrganizationalUnitTypeForm(forms.ModelForm):
    class Meta:
        model = OrganizationalUnitType
        fields = ('name',)


class OrganizationalUnitForm(forms.ModelForm):
    class Meta:
        model = OrganizationalUnit
        fields = ('name', 'type', 'parent')


class ProductInitialForm(forms.Form):
    type = forms.ChoiceField(
        choices=Product.resource_type_choices,
        widget=Select(attrs={'class': 'form-control'})
    )


class ProductForm(forms.ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Product
        fields = ('title', 'teaser', 'description', 'price', 'state', 'type',
                  'tags', 'institution_level', 'topics',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'do_create_waiting_list', 'waiting_list_length',
                  'waiting_list_deadline_days', 'waiting_list_deadline_hours',
                  'time_mode', 'duration', 'locality',
                  'tour_available', 'catering_available',
                  'presentation_available', 'custom_available', 'custom_name',
                  'tilbudsansvarlig', 'organizationalunit',
                  'preparation_time', 'comment', 'only_one_guest_per_visit'
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
            'description': CKEditorUploadingWidget(),
            'custom_name': TextInput(attrs={
                'class': 'titlefield form-control input-sm',
                'rows': 1, 'size': 62
            }),

            'price': NumberInput(attrs={'class': 'form-control input-sm'}),
            'type': Select(attrs={'class': 'form-control input-sm'}),
            'preparation_time': TextInput(attrs={
                'class': 'titlefield form-control input-sm',
                'rows': 1, 'size': 62
            }),
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
            'do_create_waiting_list': CheckboxInput(
                attrs={
                    'class': 'form-control input-sm',
                    'data-toggle': 'hide',
                    'data-target': '!.waitinglist-dependent'
                }
            ),
            'waiting_list_length': NumberInput(
                attrs={
                    'class': 'form-control input-sm waitinglist-dependent',
                    'min': 1
                }
            ),
            'waiting_list_deadline_days': NumberInput(
                attrs={
                    'class': 'form-control input-sm waitinglist-dependent',
                    'min': 0
                }
            ),
            'waiting_list_deadline_hours': NumberInput(
                attrs={
                    'class': 'form-control input-sm waitinglist-dependent',
                    'min': 0,
                    'max': 23
                }
            ),
            'duration': Select(attrs={'class': 'form-control input-sm'}),
            'locality': Select(attrs={'class': 'form-control input-sm'}),
            'organizationalunit': Select(
                attrs={'class': 'form-control input-sm'}
            ),
            'tags': CheckboxSelectMultiple(),
            'roomresponsible': CheckboxSelectMultiple,
            'state': Select(attrs={'class': 'form-control input-sm'}),
            'time_mode': Select(attrs={'class': 'form-control input-sm'}),
            'tilbudsansvarlig': Select(
                attrs={'class': 'form-control input-sm'}
            )
        }
        labels = {
            'custom_name': _('Navn')
        }

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user')
        self.instance = kwargs.get('instance')

        unit = None
        if self.instance is not None:
            unit = self.instance.organizationalunit
        if unit is None and \
                self.user is not None and self.user.userprofile is not None:
            unit = self.user.userprofile.organizationalunit

        self.current_unit = unit

        time_mode_choices = self.instance.available_time_modes()

        if not self.instance.pk and 'initial' in kwargs:
            kwargs['initial']['tilbudsansvarlig'] = self.user.pk
            if unit is not None:
                kwargs['initial']['organizationalunit'] = unit.pk
            # When only one choice for time modes, default to that
            if len(time_mode_choices) == 1:
                kwargs['initial']['time_mode'] = time_mode_choices[0][0]

        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['organizationalunit'].queryset = self.get_unit_query_set()
        self.fields['type'].widget = HiddenInput()
        # Set time_mode choices to calculated value from instance
        self.fields['time_mode'].choices = time_mode_choices

        if unit is not None and 'locality' in self.fields:
            self.fields['locality'].choices = [BLANK_OPTION] + \
                [
                    (x.id, x.name_and_address)
                    for x in Locality.objects.order_by(
                        # Sort stuff where unit is null last
                        OrderBy(Q(organizationalunit__isnull=False),
                                descending=True),
                        # Sort localities belong to current unit first
                        OrderBy(Q(organizationalunit=unit), descending=True),
                        # Lastly, sort by name
                        "name"
                    )
                ]

        if 'duration' in self.fields:
            self.fields['duration'].choices = [
                ('00:00', _(u'Ingen')), ('00:15', _(u'15 minutter')),
                ('00:30', _(u'30 minutter')), ('00:45', _(u'45 minutter')),
                ('01:00', _(u'1 time')), ('01:15', _(u'1 time, 15 minutter')),
                ('01:30', _(u'1 time, 30 minutter')),
                ('01:45', _(u'1 time, 45 minutter')),
                ('02:00', _(u'2 timer')),
                ('02:30', _(u'2 timer, 30 minutter')),
                ('03:00', _(u'3 timer')),
                ('03:30', _(u'3 timer, 30 minutter')),
                ('04:00', _(u'4 timer')),
                ('04:30', _(u'4 timer, 30 minutter')),
                ('05:00', _(u'5 timer')),
                ('05:30', _(u'5 timer, 30 minutter')),
                ('06:00', _(u'6 timer')),
                ('06:30', _(u'6 timer, 30 minutter')),
                ('07:00', _(u'7 timer')),
                ('07:30', _(u'7 timer, 30 minutter')),
                ('08:00', _(u'8 timer')),
                ('08:30', _(u'8 timer, 30 minutter')),
                ('09:00', _(u'9 timer')),
                ('09:30', _(u'9 timer, 30 minutter')),
                ('10:00', _(u'10 timer')), ('11:00', _(u'11 timer')),
                ('12:00', _(u'12 timer')), ('13:00', _(u'13 timer')),
                ('14:00', _(u'14 timer')), ('15:00', _(u'15 timer')),
                ('20:00', _(u'20 timer')), ('24:00', _(u'24 timer')),
                ('36:00', _(u'36 timer')), ('48:00', _(u'48 timer'))
            ]

        if 'tilbudsansvarlig' in self.fields:
            qs = self.fields['tilbudsansvarlig']._get_queryset()
            self.fields['tilbudsansvarlig']._set_queryset(
                qs.filter(userprofile__organizationalunit=unit)
            )
            self.fields['tilbudsansvarlig'].label_from_instance = \
                lambda obj: "%s (%s) <%s>" % (
                    obj.get_full_name(),
                    obj.username,
                    obj.email
                )

        if 'roomresponsible' in self.fields:
            qs = self.fields['roomresponsible']._get_queryset()
            self.fields['roomresponsible']._set_queryset(
                qs.filter(organizationalunit=unit)
            )
            self.fields['roomresponsible'].label_from_instance = \
                lambda obj: "%s <%s>" % (
                    obj.get_full_name(),
                    obj.email
                )

    def clean_type(self):
        instance = getattr(self, 'instance', None)
        if instance:
            return instance.type
        else:
            return self.cleaned_data['type']

    def clean(self):
        cleaned_data = super(ProductForm, self).clean()
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


class StudentForADayForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics',
                  'time_mode', 'duration', 'locality',
                  'tilbudsansvarlig', 'organizationalunit',
                  'preparation_time', 'comment',
                  )
        widgets = ProductForm.Meta.widgets


class InternshipForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics',
                  'time_mode', 'locality',
                  'tilbudsansvarlig', 'organizationalunit',
                  'preparation_time', 'comment',
                  )
        widgets = ProductForm.Meta.widgets


class OpenHouseForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics',
                  'time_mode', 'locality',
                  'tilbudsansvarlig', 'organizationalunit',
                  'preparation_time', 'comment',
                  )
        widgets = ProductForm.Meta.widgets


class TeacherProductForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'do_create_waiting_list', 'waiting_list_length',
                  'waiting_list_deadline_days', 'waiting_list_deadline_hours',
                  'time_mode', 'duration', 'locality',
                  'tilbudsansvarlig', 'roomresponsible', 'organizationalunit',
                  'preparation_time', 'comment',
                  )
        widgets = ProductForm.Meta.widgets


class ClassProductForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'do_create_waiting_list', 'waiting_list_length',
                  'waiting_list_deadline_days', 'waiting_list_deadline_hours',
                  'time_mode', 'duration', 'locality',
                  'tour_available', 'catering_available',
                  'presentation_available', 'custom_available', 'custom_name',
                  'tilbudsansvarlig', 'roomresponsible', 'organizationalunit',
                  'preparation_time', 'comment', 'only_one_guest_per_visit'
                  )
        widgets = ProductForm.Meta.widgets
        labels = ProductForm.Meta.labels


class StudyProjectForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics',
                  'minimum_number_of_visitors', 'maximum_number_of_visitors',
                  'time_mode', 'locality',
                  'tilbudsansvarlig', 'organizationalunit',
                  'preparation_time', 'comment',
                  )
        widgets = ProductForm.Meta.widgets


class AssignmentHelpForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'state',
                  'institution_level', 'topics',
                  'time_mode',
                  'tilbudsansvarlig', 'organizationalunit',
                  'comment',
                  )
        widgets = ProductForm.Meta.widgets


class StudyMaterialForm(ProductForm):
    class Meta:
        model = Product
        fields = ('type', 'title', 'teaser', 'description', 'price', 'state',
                  'institution_level', 'topics',
                  'time_mode',
                  'tilbudsansvarlig', 'organizationalunit',
                  'comment'
                  )
        widgets = ProductForm.Meta.widgets


class OtherProductForm(ProductForm):
    class Meta:
        model = Product
        fields = ProductForm.Meta.fields
        widgets = ProductForm.Meta.widgets


ProductStudyMaterialFormBase = inlineformset_factory(Product,
                                                     StudyMaterial,
                                                     fields=('file',),
                                                     can_delete=True, extra=1)


class ProductStudyMaterialForm(ProductStudyMaterialFormBase):

    def __init__(self, data, instance=None):
        super(ProductStudyMaterialForm, self).__init__(data)
        self.studymaterials = StudyMaterial.objects.filter(product=instance)


class ProductAutosendForm(forms.ModelForm):
    class Meta:
        model = ProductAutosend
        fields = ['template_type', 'enabled', 'days']
        widgets = {
            'template_type': forms.HiddenInput(),
            'days': forms.NumberInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super(ProductAutosendForm, self).__init__(*args, **kwargs)

        template_type = self.template_type
        if template_type is not None:
            if not template_type.enable_days:
                self.fields['days'].widget = forms.HiddenInput()
            elif template_type.key == \
                    EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER:
                self.fields['days'].help_text = _(u'Notifikation vil blive '
                                                  u'afsendt dette antal dage '
                                                  u'før besøget')
            elif template_type.key == \
                    EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE:
                self.fields['days'].help_text = _(u'Notifikation vil blive '
                                                  u'afsendt dette antal dage '
                                                  u'efter første booking er '
                                                  u'foretaget')

    @property
    def template_type(self):
        template_type = None
        try:
            template_type = self.instance.template_type
        except:
            pass
        if template_type is None:
            try:
                template_type = self.initial['template_type']
            except:
                pass

        if isinstance(template_type, EmailTemplateType):
            return template_type
        if type(template_type) == int:
            return self.fields['template_type'].to_python(
                template_type
            )

    def label(self):
        return self.template_type.name

    def has_changed(self):
        return (
            (self.instance.pk is None) or
            super(ProductAutosendForm, self).has_changed()
        )


ProductAutosendFormSetBase = inlineformset_factory(
    Product,
    ProductAutosend,
    form=ProductAutosendForm,
    extra=0,
    max_num=EmailTemplateType.objects.filter(
        enable_autosend=True, form_show=True
    ).count(),
    can_delete=False,
    can_order=False
)


class ProductAutosendFormSet(ProductAutosendFormSetBase):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', [])
        instance = kwargs.get("instance", None)
        existing_types = []

        # Ensure that no-longer-used templatetypes are removed and that new
        # defaults are added to autosend choices. Only do this for products
        # that are saved in the database and have a primary key.
        if instance and instance.pk:
            # Get list of all currently enabled types
            all_types = EmailTemplateType.objects.filter(
                enable_autosend=True, form_show=True
            )
            # Get all relevant types from the product
            product_autosends = instance.get_autosends(True).filter(
                template_type__in=all_types
            ).order_by('template_type__ordering')
            # Tell the form that is the set we already have
            kwargs['queryset'] = product_autosends

            # Add any missing defaults
            initial = []
            existing_types = [
                autosend.template_type for autosend in product_autosends
            ]
            for type in all_types:
                if type not in existing_types:
                    initial.append({
                        'template_type': type,
                        'enabled': type.is_default,
                        'days': ''
                    })
            # Add the new defaults as extra forms, with their data specified
            # in initial
            self.extra = len(initial)
            kwargs['initial'] = initial
        else:
            self.extra = len(initial)
        super(ProductAutosendFormSet, self).__init__(*args, **kwargs)

    def save_new_objects(self, commit=True):
        self.new_objects = []
        for form in self.forms:
            if form.instance and form.instance.pk:
                continue
            if self.can_delete and self._should_delete_form(form):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
            if not commit:
                self.saved_forms.append(form)
        return self.new_objects


class BookingForm(forms.ModelForm):

    scheduled = False
    product = None

    eventtime = VisitEventTimeField(
        required=False,
        label=_(u"Tidspunkt"),
        choices=(),
        widget=Select(attrs={
            'class': 'form-control'
        })
    )

    desired_time = forms.CharField(
        widget=Textarea(attrs={'class': 'form-control input-sm'}),
        required=False
    )

    class Meta:
        model = Booking
        fields = ['eventtime', 'notes']
        labels = {
            'eventtime': _(u"Tidspunkt")
        },
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, product=None, *args, **kwargs):
        super(BookingForm, self).__init__(data, *args, **kwargs)

        if product is None:
            product = self.product
        else:
            self.product = product

        # self.scheduled = visit is not None and \
        #    visit.type == Product.FIXED_SCHEDULE_GROUP_VISIT
        self.scheduled = (
            product is not None and
            product.time_mode != Product.TIME_MODE_GUEST_SUGGESTED
        )
        if self.scheduled:
            choices = [(None, BLANK_LABEL)]
            qs = product.future_bookable_times.order_by('start', 'end')
            for eventtime in qs:
                date = eventtime.interval_display

                visit = eventtime.visit
                product = eventtime.product

                if visit:
                    available_seats = visit.available_seats
                    waitinglist_capacity = visit.waiting_list_capacity
                    bookings = visit.bookings.count
                else:
                    available_seats = product.maximum_number_of_visitors
                    waitinglist_capacity = 0
                    bookings = 0

                if available_seats is None or available_seats == sys.maxint:
                    choices.append((eventtime.pk, date))
                else:
                    if bookings == 0:
                        # There are no bookings at all - yet
                        capacity_text = "%d ledige pladser" % available_seats
                    elif available_seats > 0:
                        if waitinglist_capacity > 0:
                            # There's some room on both
                            # regular and waiting list
                            capacity_text = _("%d ledige pladser + "
                                              "venteliste") % available_seats
                        else:
                            # There's only regular seats
                            capacity_text = _("%d ledige pladser") % \
                                            available_seats
                    else:
                        if waitinglist_capacity > 0:
                            # There's only waitinglist seats
                            capacity_text = _("venteliste (%d pladser)") % \
                                            waitinglist_capacity
                        else:
                            # There's no room at all
                            continue

                    choices.append(
                        (eventtime.pk, "%s - %s" % (date, capacity_text))
                    )

            self.fields['eventtime'].choices = choices
            self.fields['eventtime'].required = True
        else:
            self.fields['desired_time'].required = True

        if product is not None and 'subjects' in self.fields and \
                product.institution_level != Subject.SUBJECT_TYPE_BOTH:
            qs = None
            if product.institution_level == Subject.SUBJECT_TYPE_GRUNDSKOLE:
                qs = Subject.grundskolefag_qs()
            elif product.institution_level == Subject.SUBJECT_TYPE_GYMNASIE:
                qs = Subject.gymnasiefag_qs()
            if qs:
                self.fields['subjects'].choices = [
                    (subject.id, subject.name) for subject in qs
                ]

    def save(self, commit=True, *args, **kwargs):
        booking = super(BookingForm, self).save(commit, *args, **kwargs)
        if booking.visit and 'desired_time' in self.cleaned_data:
            booking.visit.desired_time = self.cleaned_data['desired_time']
        return booking


class BookerForm(forms.ModelForm):

    class Meta:
        model = Guest
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
                       'placeholder': _(u'E-mail')}
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
                   'placeholder': _(u'Gentag e-mail')}
        )
    )
    school = forms.CharField(
        widget=TextInput(
            attrs={'class': 'form-control input-sm',
                   'autocomplete': 'off'}
        )
    )
    school_type = forms.IntegerField(
        widget=HiddenInput()
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

    def __init__(self, data=None, products=[], language='da', *args, **kwargs):
        super(BookerForm, self).__init__(data, *args, **kwargs)
        attendeecount_widget = self.fields['attendee_count'].widget

        attendeecount_widget.attrs['min'] = 1

        if len(products) > 1:
            attendeecount_widget.attrs['data-validation-number-min-message'] =\
                _(u"Der der kræves mindst %d "
                  u"deltagere på at af de besøg du har valgt.")
            attendeecount_widget.attrs['data-validation-number-max-message'] =\
                _(u"Der er max plads til %d "
                  u"deltagere på et af de besøg du har valgt.")
        else:
            attendeecount_widget.attrs['data-validation-number-min-message'] =\
                _(u"Der der kræves mindst %d "
                  u"deltagere på det besøg du har valgt.")
            attendeecount_widget.attrs['data-validation-number-max-message'] =\
                _(u"Der er max plads til %d "
                  u"deltagere på det besøg du har valgt.")

        if len(products) > 0:
            min_visitors = [
                product.minimum_number_of_visitors
                for product in products
                if product.minimum_number_of_visitors
            ]
            if len(min_visitors) > 0:
                attendeecount_widget.attrs['min'] = min(min_visitors)

            max_visitors = [
                product.maximum_number_of_visitors
                for product in products
                if product.maximum_number_of_visitors
            ]
            if len(max_visitors) > 0:
                attendeecount_widget.attrs['max'] = max(max_visitors)

            # union or intersection?
            level = binary_or(*[
                product.institution_level for product in products
            ])

            self.fields['school'].widget.attrs['data-institution-level'] = \
                level
            if level in [School.ELEMENTARY_SCHOOL, School.GYMNASIE]:
                self.initial['school_type'] = level
            available_level_choices = Guest.level_map[level]
            self.fields['level'].choices = [(u'', BLANK_LABEL)] + [
                (value, title)
                for (value, title) in Guest.level_choices
                if value in available_level_choices
            ]

            for product in products:
                # Visit types where attendee count is mandatory
                if product.type in [
                    Product.GROUP_VISIT, Product.TEACHER_EVENT,
                    Product.STUDY_PROJECT
                ]:
                    self.fields['attendee_count'].required = True
                # Class level is not mandatory for teacher events.
                if product.type == Product.TEACHER_EVENT:
                    self.fields['level'].required = False
                if product.type == Product.STUDENT_FOR_A_DAY:
                    self.fields['attendee_count'].initial = 1

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

    def clean_school(self):
        school = self.cleaned_data.get('school')
        if School.objects.filter(name=school).count() == 0:
            raise forms.ValidationError(
                _(u'Du skal vælge skole/gymnasium fra listen for at kunne '
                  u'tilmelde dig. Hvis din skole eller dit gymnasium ikke '
                  u'kommer frem på listen, kontakt da fokussupport@adm.ku.dk '
                  u'for at få hjælp til tilmelding.')
            )
        return school

    def clean(self):
        cleaned_data = super(BookerForm, self).clean()
        email = cleaned_data.get("email")
        repeatemail = cleaned_data.get("repeatemail")
        level = cleaned_data.get("level")

        if level == '':
            cleaned_data['level'] = Guest.other

        if email is not None and repeatemail is not None \
                and email != repeatemail:
            error = forms.ValidationError(
                _(u"Indtast den samme e-mail i begge felter")
            )
            self.add_error('repeatemail', error)
        return cleaned_data

    def _clean_fields(self):
        self.update_school_dependents()
        return super(BookerForm, self)._clean_fields()

    def update_school_dependents(self):
        field = self.fields['school']
        value = field.widget.value_from_datadict(
            self.data, self.files, self.add_prefix('school')
        )
        self.schooltype = None
        try:
            school = field.clean(value)
            self.schooltype = School.objects.get(name__iexact=school).type
        except:
            pass
        if self.schooltype is not None:
            if self.schooltype != School.ELEMENTARY_SCHOOL:
                self.fields['level'].required = False

    def save(self, commit=True):
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


class EditBookerForm(forms.ModelForm):

    class Meta:
        model = Guest
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
                       'placeholder': _(u'E-mail')}
            ),
            'phone': TextInput(
                attrs={'class': 'form-control input-sm',
                       'placeholder': _(u'Telefonnummer'),
                       'pattern': '(\(\+\d+\)|\+\d+)?\s*\d+[ \d]*'},
            ),
            'attendee_count': NumberInput(
                attrs={'class': 'form-control input-sm', 'min': 0}
            ),
            'line': Select(
                attrs={'class': 'selectpicker form-control'}
            ),
            'level': Select(
                attrs={'class': 'selectpicker form-control'}
            ),
        }

    school = forms.CharField(
        widget=TextInput(
            attrs={'class': 'form-control input-sm',
                   'autocomplete': 'off'}
        )
    )
    school_type = forms.IntegerField(
        widget=HiddenInput()
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

    def __init__(self, data=None, products=[], *args, **kwargs):
        super(EditBookerForm, self).__init__(data, *args, **kwargs)
        self.fields['school'].widget.attrs['data-institution-level'] = \
            self.instance.level
        if self.instance.school is not None:
            self.fields['school'].initial = self.instance.school.name
            postcode = self.instance.school.postcode
            if postcode is not None:
                self.fields['postcode'].initial = postcode.number
                self.fields['city'].initial = postcode.city
                self.fields['region'].initial = postcode.region
            level = binary_or(*[
                product.institution_level for product in products
            ])
            self.fields['school'].widget.attrs['data-institution-level'] = \
                level
            self.fields['school_type'].initial = level

    def clean_school(self):
        school = self.cleaned_data.get('school')
        if School.objects.filter(name=school).count() == 0:
            raise forms.ValidationError(
                _(u'Skole ikke fundet')
            )
        return school

    def clean_postcode(self):
        postcode = self.cleaned_data.get('postcode')
        if postcode is not None:
            try:
                PostCode.objects.get(number=postcode)
            except:
                raise forms.ValidationError(_(u'Ukendt postnummer'))
        return postcode

    def save(self, commit=True):
        booker = super(EditBookerForm, self).save(commit=False)
        data = self.cleaned_data
        school = School.objects.filter(name__iexact=data.get('school')).first()
        booker.school = school
        booker.save()
        return booker


class ClassBookingBaseForm(forms.ModelForm):

    class Meta:
        model = ClassBooking
        fields = ('tour_desired', 'catering_desired', 'presentation_desired',
                  'custom_desired', 'notes')
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, product=None, *args, **kwargs):
        self.product = product
        super(ClassBookingBaseForm, self).__init__(data, *args, **kwargs)
        if product is not None:
            for service in ['tour', 'catering', 'presentation', 'custom']:
                if not getattr(self.product, service + '_available'):
                    del self.fields[service + '_desired']


class ClassBookingForm(ClassBookingBaseForm, BookingForm):

    class Meta:
        model = ClassBooking
        fields = ('tour_desired', 'catering_desired', 'presentation_desired',
                  'custom_desired', 'eventtime', 'notes')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


class TeacherBookingBaseForm(forms.ModelForm):

    class Meta:
        model = TeacherBooking
        fields = ('subjects', 'notes')
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, product=None, *args, **kwargs):
        self.product = product
        super(TeacherBookingBaseForm, self).__init__(data, *args, **kwargs)


class TeacherBookingForm(TeacherBookingBaseForm, BookingForm):

    class Meta:
        model = TeacherBooking
        fields = ('subjects', 'notes', 'eventtime')
        widgets = BookingForm.Meta.widgets


class StudentForADayBookingBaseForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ('notes',)
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, product=None, *args, **kwargs):
        self.product = product
        super(StudentForADayBookingBaseForm, self).__init__(
            data, *args, **kwargs
        )


class StudentForADayBookingForm(StudentForADayBookingBaseForm, BookingForm):
    class Meta:
        model = Booking
        fields = ('notes', 'eventtime')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


class StudyProjectBookingBaseForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ('notes',)
        widgets = {
            'notes': Textarea(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, data=None, product=None, *args, **kwargs):
        super(StudyProjectBookingBaseForm, self).__init__(
            data, *args, **kwargs
        )
        self.product = product


class StudyProjectBookingForm(StudyProjectBookingBaseForm, BookingForm):

    class Meta:
        model = Booking
        fields = ('notes', 'eventtime')
        labels = BookingForm.Meta.labels
        widgets = BookingForm.Meta.widgets


class BookingSubjectLevelFormBase(forms.ModelForm):
    class Meta:
        fields = ['subject', 'level']
        widgets = {
            'subject': Select(
                attrs={'class': 'form-control'}
            ),
            'level': Select(
                attrs={'class': 'form-control'}
            )
        }

    def get_queryset(self):
        return Subject.objects.all()

    def __init__(self, *args, **kwargs):
        super(BookingSubjectLevelFormBase, self).__init__(*args, **kwargs)
        # 16338: Put in a different name for each choice
        self.fields['subject'].choices = [(None, BLANK_LABEL)] + [
            (item.id, item.name) for item in self.get_queryset()
        ]


class BookingGymnasieSubjectLevelFormBase(BookingSubjectLevelFormBase):

    class Meta:
        model = BookingGymnasieSubjectLevel
        fields = BookingSubjectLevelFormBase.Meta.fields
        widgets = BookingSubjectLevelFormBase.Meta.widgets

    def get_queryset(self):
        return Subject.gymnasiefag_qs()


class BookingGrundskoleSubjectLevelFormBase(BookingSubjectLevelFormBase):

    class Meta:
        model = BookingGrundskoleSubjectLevel
        fields = BookingSubjectLevelFormBase.Meta.fields
        widgets = BookingSubjectLevelFormBase.Meta.widgets

    def get_queryset(self):
        return Subject.grundskolefag_qs()


BookingGymnasieSubjectLevelForm = \
    inlineformset_factory(
        ClassBooking,
        BookingGymnasieSubjectLevel,
        form=BookingGymnasieSubjectLevelFormBase,
        can_delete=True,
        extra=0,
        min_num=1
    )


BookingGrundskoleSubjectLevelForm = \
    inlineformset_factory(
        ClassBooking,
        BookingGrundskoleSubjectLevel,
        form=BookingGrundskoleSubjectLevelFormBase,
        can_delete=True,
        extra=0,
        min_num=1
    )


class EmailTemplateForm(forms.ModelForm):

    field_attrs = {'attrs': {'class': 'form-control enable-field-insert'}}
    area_attrs = {
        'attrs': {'class': 'form-control enable-field-insert', 'rows': 20}
    }

    class Meta:
        model = EmailTemplate
        fields = ('type', 'subject', 'body', 'organizationalunit')
        widgets = {
            'type': Select(attrs={'class': 'form-control'}),
            'organizationalunit': Select(attrs={'class': 'form-control'}),
            'subject': TextInput(
                attrs={'class': 'form-control enable-field-insert'}
            ),
            'body': Textarea(
                attrs={'class': 'form-control enable-field-insert', 'rows': 20}
            ),
        }

    subject_guest = forms.CharField(
        widget=TextInput(**field_attrs),
        label=_(u'Emne til gæster'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Emne til andre" blive sendt i stedet'),
        required=False
    )
    body_guest = forms.CharField(
        widget=Textarea(**area_attrs),
        label=_(u'Tekst til gæster'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Tekst til andre" blive sendt i stedet'),
        required=False
    )
    subject_teacher = forms.CharField(
        widget=TextInput(**field_attrs),
        label=_(u'Emne til undervisere'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Emne til andre" blive sendt i stedet'),
        required=False
    )
    body_teacher = forms.CharField(
        widget=Textarea(**area_attrs),
        label=_(u'Tekst til undervisere'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Tekst til andre" blive sendt i stedet'),
        required=False
    )
    subject_host = forms.CharField(
        widget=TextInput(**field_attrs),
        label=_(u'Emne til værter'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Emne til andre" blive sendt i stedet'),
        required=False
    )
    body_host = forms.CharField(
        widget=Textarea(**area_attrs),
        label=_(u'Tekst til værter'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Tekst til andre" blive sendt i stedet'),
        required=False
    )
    subject_other = forms.CharField(
        widget=TextInput(**field_attrs),
        label=_(u'Emne til andre'),
        help_text=_(u'Hvis feltet er tomt, vil indholdet af '
                    u'"Emne til andre" blive sendt i stedet'),
        required=False
    )
    body_other = forms.CharField(
        widget=Textarea(**area_attrs),
        label=_(u'Tekst til andre'),
        required=False
    )

    def __init__(self, user, *args, **kwargs):
        super(EmailTemplateForm, self).__init__(*args, **kwargs)
        self.fields['organizationalunit'].choices = [BLANK_OPTION] + [
            (x.pk, unicode(x))
            for x in user.userprofile.get_unit_queryset()]

        self.split = {}
        for field in ['subject', 'body']:
            block = None
            full_text = getattr(self.instance, field)
            split = TemplateSplit(full_text)

            guest_block = split.get_subblock_containing("recipient.guest")
            teacher_block = split.get_subblock_containing(
                "recipient.user.userprofile.is_teacher"
            )
            host_block = split.get_subblock_containing(
                "recipient.user.userprofile.is_host"
            )
            try:
                block = next(
                    subblock.block
                    for subblock in [guest_block, teacher_block, host_block]
                    if subblock is not None
                )
            except StopIteration:
                pass

            if block is None:
                # There is no branching;
                # all body text goes in the 'body' field
                self.fields[field + '_guest'].widget = HiddenInput()
                self.fields[field + '_teacher'].widget = HiddenInput()
                self.fields[field + '_host'].widget = HiddenInput()
                self.fields[field + '_other'].widget = HiddenInput()
                self.split[field] = False

            else:
                # There is branching - body text is split up in separate fields
                else_block = block.get_else_subblock()

                if guest_block is not None:
                    self.fields[field + '_guest'].initial = \
                        (guest_block.block.text_before + guest_block.text +
                         guest_block.block.text_after).strip()
                if teacher_block is not None:
                    self.fields[field + '_teacher'].initial = \
                        (teacher_block.block.text_before + teacher_block.text +
                         teacher_block.block.text_after).strip()
                if host_block is not None:
                    self.fields[field + '_host'].initial = \
                        (host_block.block.text_before + host_block.text +
                         host_block.block.text_after).strip()
                if else_block is not None:
                    self.fields[field + '_other'].initial = \
                        (else_block.block.text_before + else_block.text +
                         else_block.block.text_after).strip()

                self.fields[field].widget = HiddenInput()

                self.split[field] = True

    def clean_text_field(self, fieldname):
        body = self.cleaned_data[fieldname]
        try:
            EmailTemplate._expand(body, {}, True)
        except TemplateSyntaxError as e:
            raise forms.ValidationError(
                _(u'Syntaksfejl i skabelon: ') + "\n%s" % e.message
            )
        return body

    def clean_subject_guest(self):
        return self.clean_text_field('subject_guest')

    def clean_body_guest(self):
        return self.clean_text_field('body_guest')

    def clean_subject_teacher(self):
        return self.clean_text_field('subject_teacher')

    def clean_body_teacher(self):
        return self.clean_text_field('body_teacher')

    def clean_subject_host(self):
        return self.clean_text_field('subject_host')

    def clean_body_host(self):
        return self.clean_text_field('body_host')

    def clean_body_other(self):
        return self.clean_text_field('body_other')

    def clean_subject_other(self):
        return self.clean_text_field('subject_other')

    def clean_subject(self):
        return self.clean_text_field('subject')

    def clean_body(self):
        return self.clean_text_field('body')

    def clean(self):
        cleaned_data = super(EmailTemplateForm, self).clean()
        for field in ['subject', 'body']:
            sep = '\r\n' if field == 'body' else ''
            if self.split[field]:
                text = []
                first = True
                for condition, fieldname in [
                    ("recipient.guest", field + "_guest"),
                    ("recipient.user.userprofile.is_teacher",
                     field + "_teacher"),
                    ("recipient.user.userprofile.is_host", field + "_host")
                ]:
                    sub_text = cleaned_data.get(fieldname, "").strip()
                    if len(sub_text) > 0:
                        text.append(
                            "%s{%% %s %s %%}%s%s" %
                            (sep, "if" if first else "elif",
                             condition, sep, sub_text)
                        )
                        first = False

                sub_text = (cleaned_data[field + "_other"] or "").strip()
                text.append("%s{%% else %%}%s%s" % (sep, sep, sub_text))
                text.append("%s{%% endif %%}" % (sep,))
                cleaned_data[field] = ''.join(text)
        return cleaned_data


class EmailTemplatePreviewContextEntryForm(forms.Form):

    classes = {
        'OrganizationalUnit': OrganizationalUnit,
        'Product': Product,
        'Visit': Visit,
        'Booking': Booking,
        'Guest': Guest,
    }

    key = forms.CharField(
        max_length=256,
        widget=HiddenInput(attrs={
            'class': 'form-control emailtemplate-key',
        })
    )
    type = forms.CharField(
        widget=HiddenInput(attrs={'class': 'emailtemplate-type'})
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

    def __init__(self, *args, **kwargs):
        super(EmailTemplatePreviewContextEntryForm, self).__init__(
            *args, **kwargs
        )
        if 'initial' in kwargs:
            initial = kwargs['initial']
            type = initial['type']
            if type in self.classes:
                clazz = self.classes[type]
                valuefield = self.fields['value']
                valuefield.widget = Select(
                    attrs={
                        "class": "form-control emailtemplate-value "
                                 "emailtemplate-type-%s" % type
                    },
                    choices=[
                        (object.id, unicode(object))
                        for object in clazz.objects.order_by('id')
                    ]
                )
            if type == "Recipient":
                valuefield = self.fields['value']
                valuefield.widget = Select(
                    attrs={
                        "class": "form-control emailtemplate-value "
                                 "emailtemplate-type-%s" % type
                    }
                )


EmailTemplatePreviewContextForm = formset_factory(
    EmailTemplatePreviewContextEntryForm,
    extra=0
)


class BaseEmailComposeForm(forms.Form):

    required_css_class = 'required'

    body = forms.CharField(
        max_length=65584,
        widget=Textarea(attrs={'class': 'form-control'}),
        label=_(u'Tekst')
    )


class EmailComposeForm(BaseEmailComposeForm):

    def __init__(self, *args, **kwargs):
        self.view = kwargs.pop('view', None)
        super(EmailComposeForm, self).__init__(*args, **kwargs)

    recipients = ExtensibleMultipleChoiceField(
        label=_(u'Modtagere'),
        widget=CheckboxSelectMultiple
    )

    subject = forms.CharField(
        label=_(u'Emne'),
        widget=TextInput(attrs={
            'class': 'form-control'
        })
    )

    subject_max_length = 77

    def clean_subject(self):
        subject = self.cleaned_data['subject']
        if self.view is not None and hasattr(self.view, 'template_context'):
            context = self.view.template_context
            template = EmailTemplate(subject=subject, body='')
            expanded = template.expand_subject(context)
            validator = validators.MaxLengthValidator(self.subject_max_length)
            validator(expanded)
        return subject


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
        label=_(u'E-mail'),
        widget=EmailInput(
            attrs={
                'class': 'form-control input-sm',
                'placeholder': _(u'Din e-mail')
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


class BookingListForm(forms.Form):
    bookings = forms.MultipleChoiceField(
        widget=CheckboxSelectMultiple()
    )


class AcceptBookingForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Kommentar'),
        required=False
    )


class EvaluationOverviewForm(forms.Form):
    user = None

    organizationalunit = forms.MultipleChoiceField(
        label=_(u'Afgræns ud fra enhed(er)'),
        required=False,
    )

    limit_to_personal = forms.BooleanField(
        label=_(u'Begræns til besøg jeg personligt er involveret i'),
        required=False
    )

    def __init__(self, qdict, *args, **kwargs):
        self.user = kwargs.pop("user")
        userprofile = self.user.userprofile

        super(EvaluationOverviewForm, self).__init__(qdict, *args, **kwargs)

        self.fields['organizationalunit'].choices = [
            (x.pk, unicode(x)) for x in userprofile.get_unit_queryset()
        ]


class MultiProductVisitTempDateForm(forms.ModelForm):
    class Meta:
        model = MultiProductVisitTemp
        fields = ['date', 'baseproduct']
        widgets = {
            'date': DateInput(
                attrs={'class': 'datepicker form-control'}
            ),
            'baseproduct': HiddenInput()
        }
        labels = {
            'date': _(u'Vælg dato')
        }

    def __init__(self, *args, **kwargs):
        super(MultiProductVisitTempDateForm, self).__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%d-%m-%Y', '%d.%m.%Y']

    def clean(self):
        if 'date' in self.cleaned_data:
            date = self.cleaned_data['date']
            product = self.cleaned_data['baseproduct']
            if not product.is_bookable(date):
                raise forms.ValidationError(
                    {'date': _(u'Det er desværre ikke muligt at bestille '
                               u'besøget på den valgte dato. Der kan være '
                               u'begrænsninger for hvilke dage, besøget kan '
                               u'lade sig gøre - se beskrivelse af besøget.')
                     }
                )
        return super(MultiProductVisitTempDateForm, self).clean()


class MultiProductVisitTempProductsForm(forms.ModelForm):

    products_key = 'products'

    products = OrderedModelMultipleChoiceField(
        queryset=Product.objects.all(),
        widget=OrderedMultipleHiddenChooser(),
        error_messages={'required': _(u"Der er ikke valgt nogen besøg")}
    )

    class Meta:
        model = MultiProductVisitTemp
        fields = ['required_visits', 'notes']
        widgets = {
            'required_visits': TextInput(
                attrs={'class': 'form-control input-sm'}
            ),
            'notes': Textarea(
                attrs={'class': 'form-control input-sm'}
            )
        }

    def clean_products(self):
        products = self.cleaned_data[self.products_key]
        if len(products) == 0:
            raise forms.ValidationError(_(u"Der er ikke valgt nogen besøg"))
        common_institution = binary_and([
            product.institution_level for product in products
        ])
        if common_institution == 0:
            raise forms.ValidationError(
                _(u"Nogle af de valgte besøg henvender sig kun til "
                  u"grundskoleklasser og andre kun til gymnasieklasser"),
                code='conflict'
            )
        return products

    def clean(self):
        super(MultiProductVisitTempProductsForm, self).clean()
        products_selected = 0 if self.products_key not in self.cleaned_data \
            else len(self.cleaned_data[self.products_key])
        if self.cleaned_data['required_visits'] > products_selected:
            self.cleaned_data['required_visits'] = products_selected

    def save(self, commit=True):
        mvpt = super(MultiProductVisitTempProductsForm, self).save(commit)
        MultiProductVisitTempProduct.objects.filter(
            multiproductvisittemp=mvpt
        ).delete()
        for index, product in enumerate(self.cleaned_data[self.products_key]):
            relation = MultiProductVisitTempProduct(
                product=product, multiproductvisittemp=mvpt, index=index
            )
            relation.save()
        return mvpt


class EvaluationForm(forms.ModelForm):

    class Meta:
        model = Evaluation
        fields = ['url']
        widgets = {'url': TextInput(attrs={
            'class': 'form-control input-sm',
            'readonly': 'readonly'
        })}

    nonparticipating_guests = ModelMultipleChoiceField(
        queryset=Guest.objects.all(),
        required=False,
        label=_(u'Deltagere uden spørgeskema')
    )

    def __init__(self, visit, *args, **kwargs):
        self.instance = kwargs.get('instance')
        self.visit = visit
        if self.instance:
            kwargs['initial']['nonparticipating_guests'] = [
                evaluationguest.guest
                for evaluationguest
                in self.instance.evaluationguest_set.filter(
                    status=EvaluationGuest.STATUS_NO_PARTICIPATION
                )
            ]
        super(EvaluationForm, self).__init__(*args, **kwargs)
        self.fields['nonparticipating_guests'].queryset = Guest.objects.filter(
            booking__in=self.visit.booking_list
        )

    def get_queryset(self):
        return Evaluation.objects.filter(visit=self.visit)

    def save(self, commit=True):
        self.instance.visit = self.visit
        super(EvaluationForm, self).save(commit)
        existing_guests = {
            evalguest.guest: evalguest
            for evalguest in self.instance.evaluationguest_set.all()
        }
        for booking in self.visit.booking_list:
            guest = booking.booker
            status = EvaluationGuest.STATUS_NO_PARTICIPATION
            if guest not in self.cleaned_data['nonparticipating_guests']:
                status = EvaluationGuest.STATUS_NOT_SENT
            if guest in existing_guests:
                evalguest = existing_guests[guest]
                evalguest.status = status
            else:
                evalguest = EvaluationGuest(
                    evaluation=self.instance,
                    guest=guest,
                    status=status
                )
            evalguest.save()
        return self.instance


class EvaluationStatisticsForm(forms.Form):

    from_date = forms.DateField(
        label=_(u'Dato fra'),
        input_formats=['%d-%m-%Y'],
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control input-sm datepicker datepicker-admin'
            }
        )
    )

    to_date = forms.DateField(
        label=_(u'Dato til'),
        input_formats=['%d-%m-%Y'],
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control input-sm datepicker datepicker-admin'
            }
        )
    )

    unit = forms.ModelChoiceField(
        label=_(u'Enhed'),
        queryset=OrganizationalUnit.objects.all()
    )
