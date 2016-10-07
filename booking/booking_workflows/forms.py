# -*- coding: utf-8 -*-
from booking.models import Visit, VisitAutosend, MultiProductVisit
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
        super(ChangeVisitTeachersForm, self)\
            .__init__(*args, **kwargs)

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
        super(ChangeVisitHostsForm, self).__init__(
            *args,
            **kwargs
        )

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


VisitAutosendFormSet = inlineformset_factory(
    Visit,
    VisitAutosend,
    fields=('template_key', 'enabled', 'inherit', 'days'),
    can_delete=True,
    extra=0,
    min_num=1
)
