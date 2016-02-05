# -*- coding: utf-8 -*-

from booking.models import Booking
from django import forms
from django.utils.translation import ugettext_lazy as _


class ChangeBookingStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ChangeBookingStatusForm, self).__init__(*args, **kwargs)

        if "instance" in kwargs:
            choices = kwargs['instance'].possible_status_choices()

            if kwargs['instance'].planned_status_is_blocked():
                remove_val = Booking.WORKFLOW_STATUS_PLANNED
                choices = (x for x in choices if x[0] != remove_val)

            self.fields['workflow_status'].widget.choices = choices
            self.fields['workflow_status'].label = _(u'Ny status')

    class Meta:
        model = Booking
        fields = ['workflow_status']


class ChangeBookingTeachersForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['teacher_status', 'teachers']
        widgets = {'teachers': forms.CheckboxSelectMultiple()}


class ChangeBookingHostsForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['host_status', 'hosts']
        widgets = {'hosts': forms.CheckboxSelectMultiple()}


class ChangeBookingRoomsForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room_status']
