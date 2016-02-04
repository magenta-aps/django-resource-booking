# -*- coding: utf-8 -*-
from booking.models import Unit
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView, FormView

from booking.views import LoginRequiredMixin, AccessDenied
from django.views.generic.list import ListView
from profile.forms import UserCreateForm
from profile.models import UserProfile, UserRole, EDIT_ROLES
from profile.models import FACULTY_EDITOR, COORDINATOR


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the user's profile."""
    pass


class CreateUserView(FormView, UpdateView):
    model = User
    form_class = UserCreateForm
    template_name = 'profile/create_user.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(CreateUserView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        role = current_user.userprofile.get_role()
        users_unit = current_user.userprofile.unit

        if role in EDIT_ROLES:
            if self.request.method == 'POST':
                if role == FACULTY_EDITOR:
                    # This should not be possible!
                    if current_user.userprofile.unit is None:
                        raise AccessDenied(
                            _(u"Du har rollen 'Fakultetsredaktør', men " +
                              "er ikke tilknyttet nogen enhed.")
                        )
                    unit = Unit.objects.get(pk=self.request.POST[u'unit'])
                    if unit and not unit.belongs_to(users_unit):
                        raise AccessDenied(
                            _(u"Du kan kun redigere enheder, som " +
                              "ligger under dit fakultet.")
                        )
                elif role == COORDINATOR:
                    # This should not be possible!
                    if current_user.userprofile.unit is None:
                        raise AccessDenied(
                            _(u"Du har rollen 'Koordinator', men er ikke " +
                              "tilknyttet nogen enhed.")
                        )
                    unit = Unit.objects.get(pk=self.request.POST[u'unit'])
                    if unit and not unit == users_unit:
                        raise AccessDenied(
                            _(u"Du kan kun redigere enheder, som du selv er" +
                              " koordinator for.")
                        )
            return result
        else:
            raise PermissionDenied

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        # The user making the request
        user = request.user
        self.object = User() if pk is None else User.objects.get(id=pk)

        if pk and self.object and self.object.userprofile:
            user = self.object
            form = UserCreateForm(
                user=user,
                initial={
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': self.object.userprofile.user_role,
                    'unit': self.object.userprofile.unit
                }
            )
        else:
            form = UserCreateForm(user=user)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if not hasattr(self, 'object') or self.object is None:
            self.object = None if pk is None else User.objects.get(id=pk)
        form = self.get_form()
        if form.is_valid():
            user_role_id = int(self.request.POST[u'role'])
            unit_id = int(self.request.POST[u'unit'])

            user = form.save()
            user_role = UserRole.objects.get(pk=user_role_id)
            unit = Unit.objects.get(pk=unit_id)
            # Create
            if not pk:
                user_profile = UserProfile(
                    user=user,
                    user_role=user_role,
                    unit=unit
                )
            else:
                # Update
                user_profile = user.userprofile
                user_profile.user = user
                user_profile.user_role = user_role
                user_profile.unit = unit
            user_profile.save()

            return super(CreateUserView, self).form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super(CreateUserView, self).get_form_kwargs()
        # kwargs['user'] = self.request.user

        return kwargs

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_success_url(self):
        try:
            return "/profile/user/%d" % self.object.id
        except:
            return '/'


class UnitListView(ListView):
    model = Unit

    def get_context_data(self, **kwargs):
        context = super(UnitListView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        user = self.request.user
        user_role = user.userprofile.get_role()
        if user_role == FACULTY_EDITOR:
            uu = user.userprofile.unit
            if uu is not None:
                qs = uu.get_descendants()
            else:
                qs = Unit.objects.none()
        elif user_role == COORDINATOR:
            uu = user.userprofile.unit
            if uu is not None:
                # Needs to be iterable or the template will fail
                qs = Unit.objects.filter(id=uu.id)
            else:
                qs = Unit.objects.none()
        else:
            # User must be an administrator and may attach any unit.
            qs = Unit.objects.all()
        return qs
