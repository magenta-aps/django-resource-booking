# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.utils.translation import ugettext_lazy as _

import booking.models
from booking.fields import MultipleChoiceDisableModelField
from booking.models import EmailTemplateType
from booking.models import Visit, VisitAutosend, MultiProductVisit
from booking.widgets import CheckboxSelectMultipleDisable


class ChangeVisitStatusForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['workflow_status']
        widgets = {
            'workflow_status': forms.Select(
                attrs={'class': 'form-control'}
            )
        }

    def __init__(self, *args, **kwargs):
        super(ChangeVisitStatusForm, self).__init__(*args, **kwargs)

        if "instance" in kwargs:
            choices = kwargs['instance'].possible_status_choices()

            if kwargs['instance'].planned_status_is_blocked():
                remove_val = Visit.WORKFLOW_STATUS_PLANNED
                choices = (x for x in choices if x[0] != remove_val)

            self.fields['workflow_status'].widget.choices = choices
            self.fields['workflow_status'].label = _(u'Ny status')


class ChangeVisitResponsibleForm(forms.ModelForm):
    class Meta:
        model = MultiProductVisit
        fields = ['responsible']
        widgets = {
            'responsible': forms.Select(
                attrs={'class': 'form-control'}
            )
        }

    def __init__(self, *args, **kwargs):
        super(ChangeVisitResponsibleForm, self).__init__(*args, **kwargs)
        self.fields['responsible'].queryset = \
            kwargs['instance'].potential_responsible()


class ChangeVisitTeachersForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['teachers', 'override_needed_teachers']
        widgets = {
            'teachers': CheckboxSelectMultipleDisable(),
            'override_needed_teachers': forms.Select(
                attrs={'class': 'form-control'}
            )
        }

    # Will be called by the superclass to create form fields
    def formfield_callback(modelfield, **kwargs):
        if modelfield.name == 'teachers':
            return modelfield.formfield(
                form_class=MultipleChoiceDisableModelField, **kwargs
            )
        return modelfield.formfield(**kwargs)

    send_emails = forms.BooleanField(
        label=_(u"Udsend e-mails til nye undervisere der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitTeachersForm, self).__init__(*args, **kwargs)
        visit = kwargs['instance']
        teachers = visit.product.potentielle_undervisere.all()
        teacherfield = self.fields['teachers']
        teacherfield.label_from_instance = User.get_full_name
        teacherfield.queryset = teachers
        disabled_values = [
            teacher.pk
            for teacher in teachers
            if not teacher.userprofile
                   .get_resource().available_for_visit(visit)
        ]
        teacherfield.disabled_values = disabled_values


class ChangeVisitHostsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['hosts', 'override_needed_hosts']
        widgets = {
            'hosts': CheckboxSelectMultipleDisable(),
            'override_needed_hosts': forms.Select(
                attrs={'class': 'form-control'}
            )
        }

    # Will be called by the superclass to create form fields
    def formfield_callback(modelfield, **kwargs):
        if modelfield.name == 'hosts':
            return modelfield.formfield(
                form_class=MultipleChoiceDisableModelField, **kwargs
            )
        return modelfield.formfield(**kwargs)

    send_emails = forms.BooleanField(
        label=_(u"Udsend e-mails til nye værter der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitHostsForm, self).__init__(*args, **kwargs)
        visit = kwargs['instance']
        hosts = visit.product.potentielle_vaerter.all()
        hostfield = self.fields['hosts']
        hostfield.label_from_instance = User.get_full_name
        hostfield.queryset = hosts
        disabled_values = [
            host.pk
            for host in hosts
            if not host.userprofile.get_resource().available_for_visit(visit)
        ]
        hostfield.disabled_values = disabled_values


class ChangeVisitRoomsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['room_status']
        widgets = {
            'room_status': forms.Select(
                attrs={'class': 'form-control'}
            )
        }


class ChangeVisitCommentsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['comments']


class VisitAddLogEntryForm(forms.Form):
    new_comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Ny log-post')
    )


class ResetVisitChangesForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = []


class VisitAddCommentForm(forms.Form):
    new_comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Ny kommentar')
    )


class BecomeSomethingForm(forms.Form):

    resourcerequirements = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        label=_(u'Opfyld behov for'),
        required=False,
    )

    comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Kommentar'),
        required=False
    )


class VisitAutosendForm(forms.ModelForm):
    class Meta:
        model = VisitAutosend
        fields = ['template_type', 'enabled', 'inherit', 'days']
        widgets = {
            'template_type': forms.HiddenInput()
        }

    ACTIVITY_DISABLED = 0
    ACTIVITY_ENABLED = 1
    ACTIVITY_INHERIT = 2
    active = forms.ChoiceField(
        choices=[
            (ACTIVITY_ENABLED, _(u'Aktiv')),
            (ACTIVITY_INHERIT, _(u'Nedarv')),
            (ACTIVITY_DISABLED, _(u'Inaktiv'))
        ],
        widget=forms.widgets.RadioSelect()
    )

    def clean(self):
        activity = str(self.cleaned_data['active'])
        self.cleaned_data['enabled'] = \
            (activity == str(VisitAutosendForm.ACTIVITY_ENABLED))
        self.cleaned_data['inherit'] = \
            (activity == str(VisitAutosendForm.ACTIVITY_INHERIT))

    def get_active_value(self, kwargs):
        if 'instance' in kwargs:
            if kwargs['instance'].inherit:
                return VisitAutosendForm.ACTIVITY_INHERIT
            if kwargs['instance'].enabled:
                return VisitAutosendForm.ACTIVITY_ENABLED
            else:
                return VisitAutosendForm.ACTIVITY_DISABLED
        elif 'initial' in kwargs:
            if kwargs['initial']['inherit']:
                return VisitAutosendForm.ACTIVITY_INHERIT
            if kwargs['initial']['enabled']:
                return VisitAutosendForm.ACTIVITY_ENABLED
        return VisitAutosendForm.ACTIVITY_INHERIT

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        initial.update({'active': self.get_active_value(kwargs)})
        kwargs['initial'] = initial

        super(VisitAutosendForm, self).__init__(*args, **kwargs)

        template_type = None
        if 'instance' in kwargs:
            template_type = kwargs['instance'].template_type
        elif 'initial' in kwargs:
            template_type = kwargs['initial']['template_type']
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
                                                  u'efter første booking '
                                                  u'er foretaget')

    @property
    def associated_visit(self):
        if 'visit' in self.initial:
            visit = self.initial['visit']
            if type(visit) == int:
                visit = Visit.objects.get(id=visit)
            if isinstance(visit, Visit):
                return visit
        elif self.instance:
            return self.instance.visit

    @property
    def template_type(self):
        value = self.initial['template_type']
        if isinstance(value, EmailTemplateType):
            return value
        if type(value) == int:
            return self.fields['template_type'].to_python(
                value
            )

    def label(self):
        return self.template_type.name

    def inherit_from(self):
        visit = self.associated_visit
        for product in visit.products:
            autosend = product.get_autosend(self.template_type)
            if autosend is not None:
                return autosend
        # return self.associated_visit.product.get_autosend(self.template_type)


VisitAutosendFormSetBase = inlineformset_factory(
    Visit,
    VisitAutosend,
    form=VisitAutosendForm,
    extra=0,
    can_delete=False,
    can_order=False
)


class VisitAutosendFormSet(VisitAutosendFormSetBase):
    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            instance = kwargs['instance']
            all_types = EmailTemplateType.objects.filter(
                enable_autosend=True, form_show=True
            )
            visit_autosends = instance.visitautosend_set.filter(
                template_type__in=all_types
            ).order_by('template_type__ordering')
            kwargs['queryset'] = visit_autosends

            if visit_autosends.count() < all_types.count():
                initial = []
                existing_types = [
                    autosend.template_type for autosend in visit_autosends
                ]
                for type in all_types:
                    if type.key not in existing_types and \
                            instance.product.type not in \
                            type.disabled_product_types:
                        initial.append({
                            'template_type': type,
                            'enabled': False,
                            'inherit': True,
                            'days': '',
                            'visit': kwargs['instance'].pk
                        })
                initial.sort(
                    key=lambda choice: choice['template_type'].ordering
                )
                kwargs['initial'] = initial
                self.extra = len(initial)
        super(VisitAutosendFormSet, self).__init__(*args, **kwargs)
