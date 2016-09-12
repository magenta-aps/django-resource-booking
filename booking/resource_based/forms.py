# encoding: utf-8
from booking.models import OrganizationalUnit
from booking.models import Resource
from booking.models import ResourceType
from booking.models import ItemResource, RoomResource
from booking.models import TeacherResource, HostResource, VehicleResource
from booking.models import ResourcePool
from django import forms
from django.forms import CheckboxSelectMultiple
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
            }),
        }

    resourcepools = forms.ModelMultipleChoiceField(
        queryset=ResourcePool.objects.filter(),
        widget=CheckboxSelectMultiple(),
        required=False,
        label=_(u'Ressourcegrupper')
    )

    def __init__(self, *args, **kwargs):
        # Populate initial values from the reverse m2m relation

        forms.ModelForm.__init__(self, *args, **kwargs)

        if self.instance.pk:
            self.initial['resourcepools'] = [
                p.pk for p in self.instance.resourcepool_set.all()
            ]

        # Limit choices to the same unit and type
        self.fields['resourcepools'].queryset = ResourcePool.objects.filter(
            organizationalunit=self.instance.organizationalunit,
            resource_type=self.instance.resource_type
        )

    # Cribbed from
    # http://stackoverflow.com/questions/2216974/
    # Save the choices in the reverse m2m relation
    def save(self, commit=True):
        instance = forms.ModelForm.save(self, False)
        old_save_m2m = self.save_m2m

        def save_m2m():
            old_save_m2m()
            instance.resourcepool_set.clear()
            for resourcepool in self.cleaned_data['resourcepools']:
                instance.resourcepool_set.add(resourcepool)

        self.save_m2m = save_m2m
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    @staticmethod
    def get_resource_form_class(resource_type):
        if resource_type == ResourceType.RESOURCE_TYPE_ITEM:
            return EditItemResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_ROOM:
            return EditRoomResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_TEACHER:
            return EditTeacherResourceForm
        elif resource_type == ResourceType.RESOURCE_TYPE_HOST:
            return EditHostResourceForm
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


class EditHostResourceForm(EditResourceForm):
    class Meta:
        model = HostResource
        fields = EditResourceForm.Meta.fields
        widgets = EditResourceForm.Meta.widgets


class EditVehicleResourceForm(EditResourceForm):
    class Meta:
        model = VehicleResource
        fields = EditResourceForm.Meta.fields + ['name', 'locality']
        widgets = EditResourceForm.Meta.widgets


class ResourcePoolTypeForm(forms.Form):
    type = forms.ChoiceField(
        label=_(u'Type'),
        choices=[
            (x.id, x.name) for x in ResourceType.objects.all()
        ],
        required=True
    )
    unit = forms.ChoiceField(
        label=_(u'Enhed'),
        choices=[
            (x.id, x.name) for x in OrganizationalUnit.objects.all()
        ]
    )


class EditResourcePoolForm(forms.ModelForm):
    class Meta:
        model = ResourcePool
        fields = ['name', 'resources']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control input-sm',
                'rows': 1, 'size': 62
            }),
            'resources': forms.CheckboxSelectMultiple()
        }

    def __init__(self, *args, **kwargs):
        super(EditResourcePoolForm, self).__init__(*args, **kwargs)
        # Limit choices to the same unit and type
        self.fields['resources'].choices = [
            (resource.subclass_instance.id,
             resource.subclass_instance.get_name())
            for resource in Resource.objects.filter(
                organizationalunit=self.instance.organizationalunit,
                resource_type=self.instance.resource_type
            )
        ]
