# encoding: utf-8
from booking.models import OrganizationalUnit
from booking.models import Resource
from booking.models import ResourceType
from booking.models import ItemResource, RoomResource
from booking.models import TeacherResource, VehicleResource
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

    @staticmethod
    def get_resource_form_class(resource_type):
        if resource_type == ResourceType.RESOURCE_TYPE_ITEM:
            return EditItemResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_ROOM:
            return EditRoomResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_TEACHER:
            return EditTeacherResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_VEHICLE:
            return EditVehicleResourceForm


class EditItemResourceForm(EditResourceForm):
    class Meta:
        model = ItemResource
        fields = EditResourceForm.Meta.fields + ['name', 'locality']
        widgets = EditResourceForm.Meta.widgets


class EditRoomResourceForm(EditResourceForm):
    class Meta:
        model = RoomResource
        fields = EditResourceForm.Meta.fields
        widgets = EditResourceForm.Meta.widgets


class EditTeacherResourceForm(EditResourceForm):
    class Meta:
        model = TeacherResource
        fields = EditResourceForm.Meta.fields
        widgets = EditResourceForm.Meta.widgets


class EditVehicleResourceForm(EditResourceForm):
    class Meta:
        model = VehicleResource
        fields = EditResourceForm.Meta.fields + ['name', 'locality']
        widgets = EditResourceForm.Meta.widgets
