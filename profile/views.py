# -*- coding: utf-8 -*-
from booking.models import Unit, Resource, VisitOccurrence
from booking.models import EmailTemplate
from booking.models import KUEmailMessage
from django.contrib import messages
from django.db.models import F
from django.db.models import Q
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView

from booking.views import LoginRequiredMixin, AccessDenied
from booking.views import EditorRequriedMixin, VisitOccurrenceCustomListView
from django.views.generic.list import ListView

from profile.forms import UserCreateForm, EditMyResourcesForm
from profile.models import AbsDateDist
from profile.models import EmailLoginEntry
from profile.models import UserProfile, UserRole, EDIT_ROLES, NONE
from profile.models import FACULTY_EDITOR, COORDINATOR, user_role_choices

import warnings
import profile.models as profile_models


class ProfileView(LoginRequiredMixin, TemplateView):

    HEADING_RED = 'alert-danger'
    HEADING_GREEN = 'alert-success'
    HEADING_BLUE = 'alert-info'
    HEADING_YELLOW = 'alert-warning'

    """Display the user's profile."""
    def get_template_names(self):
        profile = self.request.user.userprofile
        if not profile or profile.get_role() == NONE:
            return ['profile/profile_new_user.html']
        else:
            return super(ProfileView, self).get_template_names()

    def get_context_data(self, **kwargs):
        context = {'lists': []}

        context['lists'].extend(self.lists_by_role())
        context['thisurl'] = reverse('user_profile')

        context['lists'].extend([{
            'color': self.HEADING_GREEN,
            'type': 'VisitOccurrence',
            'title': _(u'Seneste afviklede besøg'),
            'queryset': VisitOccurrence.get_recently_held(),
            'limit': 10,
            'button': {
                'text': _(u'Vis alle'),
                'link': reverse('visit-occ-customlist') + "?type=%s" %
                VisitOccurrenceCustomListView.TYPE_LATEST_COMPLETED
            }
        }, {
            'color': self.HEADING_BLUE,
            'type': 'VisitOccurrence',
            'title': _(u'Dagens besøg'),
            'queryset': VisitOccurrence.get_todays_occurrences(),
            'limit': 10,
            'button': {
                'text': _(u'Vis alle'),
                'link': reverse('visit-occ-customlist') + "?type=%s" %
                VisitOccurrenceCustomListView.TYPE_TODAY
            }
        }])

        context.update(**kwargs)
        return super(ProfileView, self).get_context_data(**context)

    def sort_vo_queryset(self, qs):
        return qs.annotate(
            datediff=AbsDateDist(
                F('start_datetime') - timezone.now()
            )
        ).order_by('datediff')

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
        visitlist = {
            'color': self.HEADING_BLUE,
            'type': 'Resource',
            'title': {
                'text': _(u'Tilbud i min enhed'),
                'link': reverse('search') + '?u=-3'
            },
            'queryset': Resource.objects.filter(
                unit=self.request.user.userprofile.get_unit_queryset()
            ).order_by("title"),
        }

        if len(visitlist['queryset']) > 10:
            visitlist['limited_qs'] = visitlist['queryset'][:10]
            visitlist['button'] = {
                'text': _(u'Søg i alle'),
                'link': reverse('search') + '?u=-3'
            }

        unit_qs = self.request.user.userprofile.get_unit_queryset()

        unplanned = {
            'color': self.HEADING_RED,
            'type': 'VisitOccurrence',
            'title': _(u"Besøg der kræver handling"),
            'queryset': self.sort_vo_queryset(
                VisitOccurrence.being_planned_queryset(visit__unit=unit_qs).
                    annotate(num_participants=(
                        Coalesce(Count("bookings__booker__pk"), 0) +
                        Coalesce(Sum("bookings__booker__attendee_count"), 0)
                    )
                ).filter(num_participants__gte=1)
                # See also VisitOccurrenceSearchView.filter_by_participants
            )
        }
        if len(unplanned['queryset']) > 10:
            unplanned['limited_qs'] = unplanned['queryset'][:10]
            unplanned['button'] = {
                'text': _(u'Vis alle'),
                'link': reverse('visit-occ-search') + '?u=-3&w=-1&go=1&p_min=1'
            }

        planned = {
            'color': self.HEADING_GREEN,
            'type': 'VisitOccurrence',
            'title': _(u"Planlagte besøg"),
            'queryset': self.sort_vo_queryset(
                VisitOccurrence.planned_queryset(visit__unit=unit_qs)
            )
        }
        if len(planned['queryset']) > 10:
            planned['limited_qs'] = planned['queryset'][:10]
            planned['button'] = {
                'text': _(u'Vis alle'),
                'link': reverse('visit-occ-search') + '?u=-3&w=-2&go=1'
            }

        return [visitlist, unplanned, planned]

    def lists_for_teachers(self):
        user = self.request.user
        taught_vos = user.taught_visitoccurrences.all()
        unit_qs = self.request.user.userprofile.get_unit_queryset()

        return [
            {
                'color': self.HEADING_BLUE,
                'type': 'Resource',
                'title': {
                    'text': _(u'Mine tilbud'),
                    'link': reverse('search') + '?u=-3'
                },
                'queryset': Resource.objects.filter(
                    Q(visit__visitoccurrence=taught_vos) |
                    Q(visit__default_teachers=self.request.user)
                ).order_by("title"),
            },
            {
                'color': self.HEADING_RED,
                'type': 'VisitOccurrence',
                'title': _(u"Besøg der mangler undervisere"),
                'queryset': self.sort_vo_queryset(
                    VisitOccurrence.objects.filter(
                        visit__unit=unit_qs,
                        teacher_status=VisitOccurrence.STATUS_NOT_ASSIGNED
                    ).exclude(
                        teachers=self.request.user
                    )
                )
            },
            {
                'color': self.HEADING_GREEN,
                'type': 'VisitOccurrence',
                'title': _(u"Besøg hvor jeg er underviser"),
                'queryset': self.sort_vo_queryset(taught_vos)
            }
        ]

    def lists_for_hosts(self):
        user = self.request.user
        hosted_vos = user.hosted_visitoccurrences.all()

        return [
            {
                'color': self.HEADING_BLUE,
                'type': 'Resource',
                'title': {
                    'text': _(u'Mine tilbud'),
                    'link': reverse('search') + '?u=-3'
                },
                'queryset': Resource.objects.filter(
                    Q(visit__visitoccurrence=hosted_vos) |
                    Q(visit__default_hosts=user)
                ).order_by("title"),
            },
            {
                'color': self.HEADING_RED,
                'type': 'VisitOccurrence',
                'title': _(u"Besøg der mangler værter"),
                'queryset': VisitOccurrence.objects.filter(
                    visit__unit=self.request.user.userprofile.
                        get_unit_queryset(),
                    host_status=VisitOccurrence.STATUS_NOT_ASSIGNED
                ).exclude(
                    hosts=self.request.user
                )
            },
            {
                'color': self.HEADING_GREEN,
                'type': 'VisitOccurrence',
                'title': _(u"Besøg hvor jeg er vært"),
                'queryset': hosted_vos
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

            # Send email to newly created users
            if not pk:
                KUEmailMessage.send_email(
                    EmailTemplate.SYSTEM__USER_CREATED,
                    {
                        'user': user,
                        'password': form.cleaned_data['password1'],
                    },
                    [user],
                    user
                )

            messages.add_message(
                request,
                messages.INFO,
                _(u'Brugeren %s blev gemt' % user.username)
            )

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
            return reverse("user_list")
        except:
            return '/'


class DeleteUserView(DeleteView):

    model = User
    template_name = 'profile/user_confirm_delete.html'

    def get_success_url(self):
        return "/profile/users"


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
        if self.selected_role is not None:
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
