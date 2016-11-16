# -*- coding: utf-8 -*-
from booking.models import Visit, VisitAutosend, MultiProductVisit
from booking.models import EmailTemplateType
from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import ugettext_lazy as _

import booking.models


class ChangeVisitStatusForm(forms.ModelForm):

    class Meta:
        model = Visit
        fields = ['workflow_status']

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

    def __init__(self, *args, **kwargs):
        super(ChangeVisitResponsibleForm, self).__init__(*args, **kwargs)
        self.fields['responsible'].queryset = \
            kwargs['instance'].potential_responsible()


class ChangeVisitTeachersForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['teachers', 'override_needed_teachers']
        widgets = {'teachers': forms.CheckboxSelectMultiple()}

    send_emails = forms.BooleanField(
        label=_(u"Udsend emails til nye undervisere der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitTeachersForm, self).__init__(*args, **kwargs)
        self.fields['teachers'].queryset = \
            kwargs['instance'].product.potentielle_undervisere.all()


class ChangeVisitHostsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['hosts', 'override_needed_hosts']
        widgets = {'hosts': forms.CheckboxSelectMultiple()}

    send_emails = forms.BooleanField(
        label=_(u"Udsend emails til nye værter der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitHostsForm, self).__init__(*args, **kwargs)
        self.fields['hosts'].queryset = \
            kwargs['instance'].product.potentielle_vaerter.all()


class ChangeVisitRoomsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['room_status']


class ChangeVisitCommentsForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['comments']


class ChangeVisitEvalForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['evaluation_link']


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
        booking.models.ResourceRequirement,
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
        fields = ['template_key', 'enabled', 'inherit', 'days']
        widgets = {
            'template_key': forms.HiddenInput()
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

        template_key = None
        if 'instance' in kwargs:
            template_key = kwargs['instance'].template_key
        elif 'initial' in kwargs:
            template_key = kwargs['initial']['template_key']
        if template_key is not None:
            template_type = EmailTemplateType.get(template_key)
            if not template_type.enable_days:
                self.fields['days'].widget = forms.HiddenInput()
            elif template_key == \
                    EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER:
                self.fields['days'].help_text = _(u'Notifikation vil blive '
                                                  u'afsendt dette antal dage '
                                                  u'før besøget')
            elif template_key == EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE:
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
    def template_key(self):
        return self.initial['template_key']

    def label(self):
        return EmailTemplateType.get_name(self.template_key)

    def inherit_from(self):
        return self.associated_visit.product.get_autosend(self.template_key)


VisitAutosendFormSetBase = inlineformset_factory(
    Visit,
    VisitAutosend,
    form=VisitAutosendForm,
    extra=0,
    max_num=len(EmailTemplateType.key_choices),
    can_delete=False,
    can_order=False
)


class VisitAutosendFormSet(VisitAutosendFormSetBase):
    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            autosends = kwargs['instance'].get_autosends(False, True, False)
            if len(autosends) < len(EmailTemplateType.key_choices):
                initial = []
                existing_keys = [
                    autosend.template_key for autosend in autosends
                ]
                for key, label in EmailTemplateType.key_choices:
                    if key not in existing_keys:
                        initial.append({
                            'template_key': key,
                            'enabled': False,
                            'inherit': False,
                            'days': '',
                            'visit': kwargs['instance'].pk
                        })
                initial.sort(key=lambda choice: choice['template_key'])
                kwargs['initial'] = initial
                self.extra = len(initial)
        super(VisitAutosendFormSet, self).__init__(*args, **kwargs)
