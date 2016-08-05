# -*- coding: utf-8 -*-
from booking.models import VisitOccurrence, VisitOccurrenceAutosend
from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import ugettext_lazy as _


class ChangeVisitOccurrenceStatusForm(forms.ModelForm):

    class Meta:
        model = VisitOccurrence
        fields = ['workflow_status']

    def __init__(self, *args, **kwargs):
        super(ChangeVisitOccurrenceStatusForm, self).__init__(*args, **kwargs)

        if "instance" in kwargs:
            choices = kwargs['instance'].possible_status_choices()

            if kwargs['instance'].planned_status_is_blocked():
                remove_val = VisitOccurrence.WORKFLOW_STATUS_PLANNED
                choices = (x for x in choices if x[0] != remove_val)

            self.fields['workflow_status'].widget.choices = choices
            self.fields['workflow_status'].label = _(u'Ny status')


class ChangeVisitOccurrenceStartTimeForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['start_datetime']


class ChangeVisitOccurrenceTeachersForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['teachers', 'override_needed_teachers']
        widgets = {'teachers': forms.CheckboxSelectMultiple()}

    send_emails = forms.BooleanField(
        label=_(u"Udsend emails til nye undervisere der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitOccurrenceTeachersForm, self)\
            .__init__(*args, **kwargs)

        self.fields['teachers'].queryset = \
            kwargs['instance'].visit.potentielle_undervisere.all()


class ChangeVisitOccurrenceHostsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['hosts', 'override_needed_hosts']
        widgets = {'hosts': forms.CheckboxSelectMultiple()}

    send_emails = forms.BooleanField(
        label=_(u"Udsend emails til nye værter der tilknyttes"),
        initial=True,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ChangeVisitOccurrenceHostsForm, self).__init__(
            *args,
            **kwargs
        )

        self.fields['hosts'].queryset = \
            kwargs['instance'].visit.potentielle_vaerter.all()


class ChangeVisitOccurrenceRoomsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['room_status']


class ChangeVisitOccurrenceCommentsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['comments']


class ChangeVisitOccurrenceEvalForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['evaluation_link']


class VisitOccurrenceAddLogEntryForm(forms.Form):
    new_comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Ny log-post')
    )


class ResetVisitOccurrenceChangesForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = []


class VisitOccurrenceAddCommentForm(forms.Form):
    new_comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Ny kommentar')
    )


class BecomeSomethingForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Kommentar'),
        required=False
    )


VisitOccurrenceAutosendFormSet = inlineformset_factory(
    VisitOccurrence,
    VisitOccurrenceAutosend,
    fields=('template_key', 'enabled', 'inherit', 'days'),
    can_delete=True,
    extra=0,
    min_num=1
)
