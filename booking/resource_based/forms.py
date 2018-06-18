# encoding: utf-8
from booking.models import OrganizationalUnit
from booking.models import Resource
from booking.models import ResourceType
from booking.models import ItemResource, RoomResource
from booking.models import TeacherResource, HostResource, VehicleResource
from booking.models import ResourcePool
from booking.models import ResourceRequirement
from booking.models import VisitResource
from booking.fields import MultipleChoiceDisableField
from booking.widgets import CheckboxSelectMultipleDisable
from django import forms
from django.core.validators import RegexValidator
from django.forms import CheckboxSelectMultiple, NumberInput
from django.forms import formset_factory, BaseFormSet
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as __


class CreateTimesFromRulesForm(forms.Form):
    hh_mm_validator = RegexValidator("^[0-2][0-9]:[0-5][0-9]$")

    start_time = forms.CharField(
        label=_(u'Fra'),
        required=True,
        initial='08:00',
        validators=[hh_mm_validator]
    )
    end_time = forms.CharField(
        label=_(u'Til'),
        required=True,
        initial='16:00',
        validators=[hh_mm_validator]
    )
    extra_days = forms.ChoiceField(
        label=_(u'Fulde dage'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=((x, x) for x in range(0, 11))
    )


class ResourceTypeForm(forms.Form):

    EXCEPT_TYPES = [
        ResourceType.RESOURCE_TYPE_TEACHER,
        ResourceType.RESOURCE_TYPE_HOST,
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
    unit = forms.ModelChoiceField(
        label=_(u'Enhed'),
        queryset=OrganizationalUnit.objects.all(),
    )

    def __init__(self, **kwargs):
        user = kwargs.pop("user")
        try:
            kwargs['initial']['unit'] = user.userprofile.organizationalunit.pk
        except AttributeError:
            pass
        super(ResourceTypeForm, self).__init__(**kwargs)
        self['unit'].field.queryset = user.userprofile.get_unit_queryset()


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
            values = tuple(self.cleaned_data['resourcepools'])

            old_save_m2m()
            instance.resourcepool_set.clear()
            instance.resourcepool_set.add(*values)

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
    unit = forms.ModelChoiceField(
        label=_(u'Enhed'),
        queryset=OrganizationalUnit.objects.all()
    )

    def __init__(self, **kwargs):
        user = kwargs.pop("user")
        try:
            kwargs['initial']['unit'] = user.userprofile.organizationalunit.pk
        except AttributeError:
            pass
        super(ResourcePoolTypeForm, self).__init__(**kwargs)
        self['unit'].field.queryset = user.userprofile.get_unit_queryset()


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
        choices = []
        for resource in Resource.objects.filter(
            organizationalunit=self.instance.organizationalunit,
            resource_type=self.instance.resource_type
        ):
            try:
                # This lookup might fail, see ticket #20705
                si = resource.subclass_instance
                choices.append((si.id, si.get_name()))
            except:
                pass
        self.fields['resources'].choices = choices


class EditResourceRequirementForm(forms.ModelForm):

    class Meta:
        model = ResourceRequirement
        fields = ['resource_pool', 'required_amount']
        widgets = {
            'required_amount': NumberInput(attrs={
                'min': 1,
                'class': 'form-control input-sm'
            })
        }

    def __init__(self, product=None, *args, **kwargs):
        super(EditResourceRequirementForm, self).__init__(*args, **kwargs)
        if product is not None:
            self.product = product
            unit = product.organizationalunit
            self.fields['resource_pool'].choices = [(None, "-----------")] + [
                (pool.id, pool.name)
                for pool in ResourcePool.objects.filter(
                    organizationalunit=unit
                )
            ]

    def save(self, commit=True):
        if getattr(self.instance, 'product', None) is None \
                and self.product is not None:
            self.instance.product = self.product
        return super(EditResourceRequirementForm, self).save(commit)


class EditVisitResourceForm(forms.Form):
    # resources = forms.MultipleChoiceField(
    #     label='Ressourcer',
    #     required=False,
    #     widget=CheckboxSelectMultiple()
    # )
    resources = MultipleChoiceDisableField(
        label='Ressourcer',
        required=False,
        widget=CheckboxSelectMultipleDisable
    )

    def __init__(self, visit, resource_requirement, *args, **kwargs):
        super(EditVisitResourceForm, self).__init__(*args, **kwargs)
        self.visit = visit
        self.resource_requirement = resource_requirement
        resourcefield = self.fields['resources']

        if resource_requirement.resource_pool:
            resourcefield.label = \
                resource_requirement.resource_pool.resource_type.plural or \
                resource_requirement.resource_pool.resource_type.name
            resourcefield.label_suffix = \
                resource_requirement.resource_pool.name

            resourcefield.choices = [
                (resource.id, resource.get_name())
                for resource
                in resource_requirement.resource_pool.specific_resources
            ]
            resourcefield.disabled_values = [
                resource.id
                for resource
                in resource_requirement.resource_pool.specific_resources
                if not resource.available_for_visit(visit)
            ]
        else:
            resourcefield.label = _(u"Ukendt ressourcebehov")
            resourcefield.label_suffix = _(u"Tilbuddet har et uspecificeret "
                                           u"ressourcebehov. Dette er et "
                                           u"problem som skal rettes")

        resourcefield.help_text = __(
            u"%(count)d nødvendig",
            u"%(count)d nødvendige",
            'count'
        ) % {'count': resource_requirement.required_amount}

    def save(self):
        resources = set(
            Resource.objects.get(id=resource_id)
            for resource_id in self.cleaned_data['resources']
        )
        existing = set(
            Resource.objects.filter(
                visitresource__visit=self.visit,
                visitresource__resource_requirement=self.resource_requirement
            )
        )
        # Create new references
        for resource in resources - existing:
            VisitResource(
                visit=self.visit,
                resource_requirement=self.resource_requirement,
                resource=resource
            ).save()
        # Delete obsolete references
        VisitResource.objects.filter(
            visit=self.visit,
            resource_requirement=self.resource_requirement
        ).exclude(
            resource__in=resources
        ).delete()


class EditVisitResourceFormset(BaseFormSet):

    def __init__(self, visit, *args, **kwargs):
        super(EditVisitResourceFormset, self).__init__(*args, **kwargs)
        self.visit = visit
        self.requirements = self.visit.product.resourcerequirement_set.all()
        self.absolute_max = len(self.requirements)

    def _construct_form(self, index, **kwargs):
        kwargs.update(self.get_form_kwargs(index))
        return super(EditVisitResourceFormset, self)._construct_form(
            index,
            **kwargs
        )

    def get_form_kwargs(self, index):
        kwargs = {}
        kwargs['visit'] = self.visit
        kwargs['resource_requirement'] = self.requirements[index]
        return kwargs

    def save(self):
        for form in self.forms:
            form.save()


EditVisitResourcesForm = formset_factory(
    EditVisitResourceForm,
    formset=EditVisitResourceFormset,
    extra=0
)
