# encoding: utf-8
from booking.models import OrganizationalUnit
from booking.models import Resource
from booking.models import ResourceType
from booking.models import ItemResource, VehicleResource
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


class EditResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = []

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control input-sm',
                'rows': 1, 'size': 62
            })
        }


class EditItemResourceForm(EditResourceForm):
    class Meta:
        model = ItemResource
        fields = EditResourceForm.Meta.fields + ['name', 'locality']
        widgets = EditResourceForm.Meta.widgets


class EditVehicleResourceForm(EditResourceForm):
    class Meta:
        model = VehicleResource
        fields = EditResourceForm.Meta.fields + ['name', 'locality']
        widgets = EditResourceForm.Meta.widgets
