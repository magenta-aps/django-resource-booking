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
        fields = ['teacher_status', 'teachers']
        widgets = {'teachers': forms.CheckboxSelectMultiple()}


class ChangeVisitOccurrenceHostsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['host_status', 'hosts']
        widgets = {'hosts': forms.CheckboxSelectMultiple()}


class ChangeVisitOccurrenceRoomsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['room_status']


class ChangeVisitOccurrenceCommentsForm(forms.ModelForm):
    class Meta:
        model = VisitOccurrence
        fields = ['comments']


class VisitOccurrenceAddLogEntryForm(forms.Form):
    new_comment = forms.CharField(
        widget=forms.Textarea,
        label=_(u'Ny log-post')
    )

VisitOccurrenceAutosendFormSet = inlineformset_factory(
    VisitOccurrence,
    VisitOccurrenceAutosend,
    fields=('template_key', 'enabled', 'inherit', 'days'),
    can_delete=True,
    extra=1
)
