# -*- coding: utf-8 -*-
from booking.models import Unit, Resource, VisitOccurrence, Visit
from django.db.models import Q
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from django.views.generic.edit import UpdateView, FormView

from booking.views import LoginRequiredMixin, AccessDenied, EditorRequriedMixin
from django.views.generic.list import ListView
from profile.forms import UserCreateForm, EditMyResourcesForm
from profile.models import EmailLoginEntry
from profile.models import UserProfile, UserRole, EDIT_ROLES, NONE
from profile.models import FACULTY_EDITOR, COORDINATOR, user_role_choices

import warnings
import profile.models as profile_models


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the user's profile."""
    def get_template_names(self):
        profile = self.request.user.userprofile
        if not profile or profile.get_role() == NONE:
            return ['profile/profile_new_user.html']
        else:
            return super(ProfileView, self).get_template_names()

    def get_context_data(self, **kwargs):
        context = {'lists': []}

        context['lists'].append({
            'type': 'Resource',
            'title': _(u'Mine tilbud'),
            'titlelink': reverse('my-resources'),
            'queryset': self.request.user.userprofile.my_resources.all
        })

        context['lists'].extend(self.lists_by_role())
        context['thisurl'] = reverse('user_profile')

        context['lists'].extend([{
            'type': 'Resource',
            'title': _(u'Seneste opdaterede tilbud'),
            'queryset': Resource.get_latest_updated()
        }, {
            'type': 'Resource',
            'title': _(u'Seneste bookede tilbud'),
            'queryset': Visit.get_latest_booked()
        }, {
            'type': 'VisitOccurrence',
            'title': _(u'Dagens arrangementer'),
            'queryset': VisitOccurrence.get_todays_occurrences()
        }])

        context.update(**kwargs)
        return super(ProfileView, self).get_context_data(**context)

    def lists_by_role(self):
        role = self.request.user.userprofile.get_role()
        if role in profile_models.EDIT_ROLES:
            return self.lists_for_editors()
        elif role == profile_models.TEACHER:
            return self.lists_for_teachers()
        elif role == profile_models.HOST:
            return self.lists_for_hosts()
        else:
            return []

    def lists_for_editors(self):
        return [
            {
                'type': 'VisitOccurrence',
                'title': _(u"Arrangementer der kræver handling"),
                'queryset': VisitOccurrence.being_planned_queryset(
                    visit__unit=self.request.user.userprofile.
                        get_unit_queryset()
                )
            },
            {
                'type': 'VisitOccurrence',
                'title': _(u"Planlagte arrangementer"),
                'queryset': VisitOccurrence.planned_queryset(
                    visit__unit=self.request.user.userprofile.
                        get_unit_queryset()
                )
            }
        ]

    def lists_for_teachers(self):
        return [
            {
                'type': 'VisitOccurrence',
                'title': _(u"Arrangementer der mangler undervisere"),
                'queryset': VisitOccurrence.objects.filter(
                    visit__unit=self.request.user.userprofile.
                        get_unit_queryset(),
                    teacher_status=VisitOccurrence.STATUS_NOT_ASSIGNED
                ).exclude(
                    teachers=self.request.user
                )
            },
            {
                'type': 'VisitOccurrence',
                'title': _(u"Arrangementer hvor jeg er underviser"),
                'queryset': VisitOccurrence.objects.filter(
                    teachers=self.request.user
                )
            }
        ]

    def lists_for_hosts(self):
        return [
            {
                'type': 'VisitOccurrence',
                'title': _(u"Arrangementer der mangler værter"),
                'queryset': VisitOccurrence.objects.filter(
                    visit__unit=self.request.user.userprofile.
                        get_unit_queryset(),
                    host_status=VisitOccurrence.STATUS_NOT_ASSIGNED
                ).exclude(
                    hosts=self.request.user
                )
            },
            {
                'type': 'VisitOccurrence',
                'title': _(u"Arrangementer hvor jeg er vært"),
                'queryset': VisitOccurrence.objects.filter(
                    hosts=self.request.user
                )
            }
        ]


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

    def get_context_data(self, **kwargs):
        context = {}

        context['breadcrumbs'] = [
            {'url': reverse('user_profile'), 'text': _(u'Min side')},
            {'url': reverse('user_list'), 'text': _(u'Administrér brugere')},
        ]
        if self.object and self.object.pk:
            context['breadcrumbs'].append({
                'url': reverse('user_edit', args=[self.object.pk]),
                'text': _(u"Redigér bruger '%s'") % self.object.username
            })
        else:
            context['breadcrumbs'].append({
                'url': reverse('user_create'),
                'text': _(u'Opret ny bruger')
            })

        context.update(kwargs)

        return super(CreateUserView, self).get_context_data(**context)

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


class UserListView(EditorRequriedMixin, ListView):
    model = User
    template_name = 'profile/user_list.html'
    context_object_name = "users"
    selected_unit = None
    selected_role = None

    def get_queryset(self):
        user = self.request.user
        unit_qs = user.userprofile.get_unit_queryset()

        qs = self.model.objects.filter(userprofile__unit__in=unit_qs)

        try:
            self.selected_unit = int(self.request.GET.get("unit", None))
        except:
            pass
        if self.selected_unit:
            qs = qs.filter(userprofile__unit=self.selected_unit)

        try:
            self.selected_role = int(self.request.GET.get("role", None))
        except:
            pass
        if self.selected_role:
            qs = qs.filter(userprofile__user_role__role=self.selected_role)

        q = self.request.GET.get("q", None)
        if q:
            qs = qs.filter(
                Q(username__contains=q) | Q(first_name__contains=q) |
                Q(last_name__contains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = {}

        user = self.request.user
        context['user_role'] = user.userprofile.get_role_name()

        unit_qs = user.userprofile.get_unit_queryset()
        context['selected_unit'] = self.selected_unit
        context['possible_units'] = [
            (x.pk, x.name) for x in unit_qs.order_by('name')
        ]

        context['selected_role'] = self.selected_role
        context['possible_roles'] = user_role_choices

        context['breadcrumbs'] = [
            {'url': reverse('user_profile'), 'text': _(u'Min side')},
            {'text': _(u'Administrér brugere')},
        ]

        context.update(kwargs)
        return super(UserListView, self).get_context_data(**context)


class UnitListView(EditorRequriedMixin, ListView):
    model = Unit

    def get_context_data(self, **kwargs):
        context = super(UnitListView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        user = self.request.user
        return user.userprofile.get_unit_queryset()


class EmailLoginView(DetailView):
    model = EmailLoginEntry
    template_name = "profile/email_login.html"
    slug_field = 'uuid'
    expired = False

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Already logged in users should be sent where they need to go
        # or logged out if they are the wrong user.
        if request.user.is_authenticated():
            if request.user == self.object.user:
                return self.redirect_to_destination(request, *args, **kwargs)
            else:
                logout(request)
                return self.redirect_to_self(request, *args, **kwargs)

        # If not expired, log the user in and send them where they need to
        # go.
        if not self.object.is_expired():
            user = authenticate(user_from_email_login=self.object.user)
            login(request, user)
            return self.redirect_to_destination(request, *args, **kwargs)
        else:
            self.expired = True

        return super(EmailLoginView, self).dispatch(request, *args, **kwargs)

    def redirect_to_self(self, request, *args, **kwargs):
        return redirect(self.object.as_url())

    def redirect_to_destination(self, request, *args, **kwargs):
        dest = self.object.success_url

        if 'dest_url' in kwargs and kwargs['dest_url'] != dest:
            warnings.warn(
                "URL mistmatch when loggin user '%s' in: '%s' vs '%s'" % (
                    self.object.user,
                    kwargs['dest_url'],
                    dest
                )
            )

        return redirect(dest)


class EditMyResourcesView(EditorRequriedMixin, UpdateView):
    model = UserProfile
    form_class = EditMyResourcesForm
    template_name = 'profile/my_resources.html'

    def get_form(self, form_class=None):
        form = super(EditMyResourcesView, self).get_form(form_class=form_class)

        userprofile = self.request.user.userprofile

        form.fields['my_resources'].queryset = Resource.objects.filter(
            unit=userprofile.get_unit_queryset()
        ).order_by('title')

        return form

    def get_object(self, queryset=None):
        return self.request.user.userprofile

    def post(self, request, *args, **kwargs):
        if request.POST.get("cancel"):
            return redirect(self.get_success_url())

        return super(EditMyResourcesView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('user_profile')
