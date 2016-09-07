# encoding: utf-8
from booking.models import OrganizationalUnit
from booking.models import Resource
from booking.models import ResourceType
from booking.models import TeacherResource
from django import forms
from django.utils.translation import ugettext_lazy as _


class ResourceTypeForm(forms.Form):

    EXCEPT_TYPES = [
        ResourceType.RESOURCE_TYPE_TEACHER,
        ResourceType.RESOURCE_TYPE_ROOM
    ]

    type = forms.ChoiceField(
        label=_(u'Type'),
        choices=[
            (x.id, x.name)
            for x in ResourceType.objects.all()
            if x.id not in EXCEPT_TYPES
        ],
        required=True
    )
    unit = forms.ChoiceField(
        label=_(u'Enhed'),
        choices=[
            (x.id, x.name)
            for x in OrganizationalUnit.objects.all()
        ]
    )

class EditTeacherResourceForm(forms.ModelForm):
    class Meta:
        model = TeacherResource
        fields = ('user', 'resource_type', 'organizationalunit')
        widgets = {
            'type': forms.HiddenInput(),
            'unit': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        if not self.instance.pk:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            if 'unit' in kwargs:
                kwargs['initial']['unit'] = kwargs['unit']
        super(EditTeacherResourceForm, self).__init__(*args, **kwargs)