# -*- coding: utf-8 -*-
from booking.models import Visit, VisitAutosend, MultiProductVisit
from booking.models import EmailTemplate
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
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

    def __init__(self, *args, **kwargs):
        super(VisitAutosendForm, self).__init__(*args, **kwargs)

        template_key = None
        if 'instance' in kwargs:
            template_key = kwargs['instance'].template_key
        elif 'initial' in kwargs:
            template_key = kwargs['initial']['template_key']
        if template_key is not None and \
                template_key not in EmailTemplate.enable_days:
            self.fields['days'].widget = forms.HiddenInput()
        elif template_key == EmailTemplate.NOTITY_ALL__BOOKING_REMINDER:
            self.fields['days'].help_text = _(u'Notifikation vil blive afsendt'
                                              u' dette antal dage før besøget')
        elif template_key == EmailTemplate.NOTIFY_HOST__HOSTROLE_IDLE:
            self.fields['days'].help_text = _(u'Notifikation vil blive afsendt'
                                              u' dette antal dage efter første'
                                              u' booking er foretaget')

    def label(self):
        return EmailTemplate.get_name(self.initial['template_key'])


VisitAutosendFormSetBase = inlineformset_factory(
    Visit,
    VisitAutosend,
    form=VisitAutosendForm,
    formset=BaseInlineFormSet,
    extra=0,
    max_num=len(EmailTemplate.key_choices),
    can_delete=False,
    can_order=False
)


class VisitAutosendFormSet(VisitAutosendFormSetBase):
    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            autosends = kwargs['instance'].get_autosends(False, True, False)
            if len(autosends) < len(EmailTemplate.key_choices):
                initial = []
                existing_keys = [
                    autosend.template_key for autosend in autosends
                ]
                for key, label in EmailTemplate.key_choices:
                    if key not in existing_keys:
                        initial.append({
                            'template_key': key,
                            'enabled': False,
                            'inherit': False,
                            'days': ''
                        })
                initial.sort(key=lambda choice: choice['template_key'])
                kwargs['initial'] = initial
                self.extra = len(initial)
        super(VisitAutosendFormSet, self).__init__(*args, **kwargs)
