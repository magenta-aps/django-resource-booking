from booking.models import Unit
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelChoiceField, EmailField
from django.utils.translation import ugettext_lazy as _
from profile.models import UserRole
from profile.models import COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR


class UserCreateForm(UserCreationForm):
    email = EmailField(required=True)
    role = ModelChoiceField(
        required=True,
        queryset=UserRole.objects.all(),
        label=_(u'Rolle')
    )
    unit = ModelChoiceField(
        required=True,
        queryset=Unit.objects.all(),
        label=_(u'Enhed')
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        # pop off the user or the call to super will fail.
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        # self.fields does not exist until after super is called...
        super(UserCreateForm, self).__init__(*args, **kwargs)

        # Now, we can change the queryset attributes of role and unit fields
        if hasattr(self, 'user'):
            self.fields['role'].queryset = self.get_role_query_set()
            self.fields['unit'].queryset = self.get_unit_query_set()

    def get_unit_query_set(self):
        """"Get units for which user can create events."""
        return self.user.userprofile.get_unit_queryset()

    def get_role_query_set(self):
        user = self.user
        user_role = user.userprofile.get_role()
        roles_to_exclude = []

        if user_role == FACULTY_EDITOR:
            roles_to_exclude.append(ADMINISTRATOR)
        if user_role == COORDINATOR:
            roles_to_exclude.append(ADMINISTRATOR)
            roles_to_exclude.append(FACULTY_EDITOR)

        qs = UserRole.objects.all().exclude(role__in=roles_to_exclude)

        return qs
