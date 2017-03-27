# -*- coding: utf-8 -*-
from booking.models import OrganizationalUnit
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelChoiceField, EmailField
from django.utils.translation import ugettext_lazy as _
from profile.models import UserRole, UserProfile


class UserCreateForm(UserCreationForm):
    email = EmailField(required=True)
    role = ModelChoiceField(
        required=True,
        queryset=UserRole.objects.all(),
        label=_(u'Rolle')
    )
    organizationalunit = ModelChoiceField(
        required=True,
        queryset=OrganizationalUnit.objects.all(),
        label=_(u'Enhed')
    )
    additional_information = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label=UserProfile._meta.get_field_by_name(
            'additional_information'
        )[0].verbose_name
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',
                  'password1', 'password2')

    user = None

    def __init__(self, *args, **kwargs):
        # pop off the user or the call to super will fail.
        if 'user' in kwargs:
            self.user = kwargs.pop('user')

        # self.fields does not exist until after super is called...
        super(UserCreateForm, self).__init__(*args, **kwargs)

        # Now, we can change the queryset attributes of role and unit fields
        if self.user is not None:
            self.fields['role'].queryset = self.get_role_query_set()
            self.fields['organizationalunit'].queryset = \
                self.get_unit_query_set()

        if kwargs.get('instance') is not None:
            # We are editing an existing user
            self.fields['password1'].required = False
            self.fields['password2'].required = False
        self.fields['password1'].widget.attrs = {'autocomplete': 'off'}
        self.fields['password2'].widget.attrs = {'autocomplete': 'off'}

        if hasattr(self.instance, 'userprofile'):
            up = self.instance.userprofile
            self.initial.update({
                'role': up.user_role,
                'organizationalunit': up.organizationalunit,
                'additional_information': up.additional_information
            })

    def get_unit_query_set(self):
        """"Get units for which user can create events."""
        return self.user.userprofile.get_unit_queryset()

    def get_role_query_set(self):
        roles = self.user.userprofile.available_roles
        if self.instance == self.user:
            roles.append(self.user.userprofile.get_role())
        qs = UserRole.objects.filter(role__in=roles)
        return qs

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if (password1 or password2) and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.is_staff = True

        password1 = self.cleaned_data.get("password1")
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
        return user


class EditMyProductsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('my_resources',)
        widgets = {'my_resources': forms.CheckboxSelectMultiple()}


class StatisticsForm(forms.Form):
    organizationalunits = forms.ModelMultipleChoiceField(
        queryset=OrganizationalUnit.objects.none(),
        widget=forms.SelectMultiple(attrs={'class':'form-control', 'style':'height:10em'}),
        error_messages={'required': _(u'Dette felt er påkrævet!')},
    )
    from_date = forms.DateField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control input-sm datepicker datepicker-admin'
            }
        )
    )
    to_date = forms.DateField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control input-sm datepicker datepicker-admin'
            }
        )
    )
