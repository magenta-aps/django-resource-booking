# -*- coding: utf-8 -*-
from datetime import datetime

from booking.models import OrganizationalUnit, Product, Visit, Booking
from booking.models import EmailTemplateType, KUEmailMessage
from booking.models import VisitComment
from booking.utils import UnicodeWriter
from django.contrib import messages
from django.db.models import Q
from django.db.models.aggregates import Count, Sum
from django.db.models.functions import Coalesce
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import Promise
from django.utils.translation import ugettext as _, ungettext_lazy
from django.views.generic import TemplateView, DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView

from booking.views import LoginRequiredMixin, AccessDenied
from booking.views import EditorRequriedMixin, VisitCustomListView
from django.views.generic.list import ListView
from profile.forms import UserCreateForm, EditMyProductsForm, StatisticsForm
from profile.models import EmailLoginURL
from profile.models import UserProfile, UserRole, EDIT_ROLES, NONE
from profile.models import HOST, TEACHER
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

        unit_qs = self.request.user.userprofile.get_unit_queryset()

        today_qs = Visit.get_todays_visits().filter(
            eventtime__product__organizationalunit=unit_qs
        )
        recent_qs = Visit.get_recently_held().filter(
            eventtime__product__organizationalunit=unit_qs
        )

        context['lists'].extend([{
            'color': self.HEADING_GREEN,
            'type': 'Visit',
            'title': ungettext_lazy(
                u'%(count)d senest afviklet besøg',
                u'%(count)d seneste afviklede besøg',
                'count'
            ) % {'count': recent_qs.count()},
            'queryset': recent_qs,
            'limit': 10,
            'limited_qs': recent_qs[:10],
            'button': {
                'text': _(u'Søg i alle'),
                'link': reverse('visit-customlist') + "?type=%s" %
                VisitCustomListView.TYPE_LATEST_COMPLETED
            }
        }, {
            'color': self.HEADING_BLUE,
            'type': 'Visit',
            'title': ungettext_lazy(
                u'%(count)d dagens besøg',
                u'%(count)d dagens besøg',
                'count'
            ) % {'count': today_qs.count()},
            'queryset': today_qs,
            'limit': 10,
            'limited_qs': today_qs[:10],
            'button': {
                'text': _(u'Søg i alle'),
                'link': reverse('visit-customlist') + "?type=%s" %
                VisitCustomListView.TYPE_TODAY
            }
        }])

        context['is_editor'] = self.request.user.userprofile.has_edit_role()

        for list in context['lists']:
            if 'title' in list:
                if type(list['title']) == dict:
                    if isinstance(list['title']['text'], Promise):
                        list['title']['text'] = \
                            list['title']['text'] % \
                            {'count': list['queryset'].count()}
                elif isinstance(list['title'], Promise):
                    list['title'] = list['title'] % \
                        {'count': list['queryset'].count()}

        context.update(**kwargs)
        return super(ProfileView, self).get_context_data(**context)

    datediff_sql = """
        LEAST(
            ABS(
                EXTRACT(
                    EPOCH FROM
                    (
                        "booking_visit"."needs_attention_since" -
                        STATEMENT_TIMESTAMP()
                    )
                )
            ),
            ABS(
                EXTRACT(
                    EPOCH FROM
                    "booking_eventtime"."start"  - STATEMENT_TIMESTAMP()
                )
            )
        )
    """

    def sort_vo_queryset(self, qs):
        return qs.extra(
            select={'datediff': self.datediff_sql}
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
            'type': 'Product',
            'title': {
                'text': ungettext_lazy(
                    u'%(count)d tilbud i min enhed',
                    u'%(count)d tilbud i min enhed',
                    'count'
                ),
                'link': reverse('search') + '?u=-3'
            },
            'queryset': Product.objects.filter(
                organizationalunit=self.request.user
                .userprofile.get_unit_queryset()
            ).order_by("-statistics__created_time"),
        }

        if visitlist['queryset'].count() > 10:
            visitlist['limited_qs'] = visitlist['queryset'][:10]
            visitlist['button'] = {
                'text': _(u'Søg i alle'),
                'link': reverse('search') + '?u=-3'
            }

        unit_qs = self.request.user.userprofile.get_unit_queryset()

        unplanned = {
            'color': self.HEADING_RED,
            'type': 'Visit',
            'title': ungettext_lazy(
                u"%(count)d besøg under planlægning",
                u"%(count)d besøg under planlægning",
                'count'
            ),
            'queryset': self.sort_vo_queryset(
                Visit.unit_filter(
                    Visit.being_planned_queryset(
                        is_multi_sub=False
                    ),
                    unit_qs
                ).annotate(num_participants=(
                    Coalesce(Count("bookings__booker__pk"), 0) +
                    Coalesce(
                        Sum("bookings__booker__attendee_count"),
                        0
                    )
                )).filter(num_participants__gte=1)
                # See also VisitSearchView.filter_by_participants
            )
        }
        if unplanned['queryset'].count() > 10:
            unplanned['limited_qs'] = unplanned['queryset'][:10]
            unplanned['button'] = {
                'text': _(u'Søg i alle'),
                'link': reverse('visit-search') + '?u=-3&w=-1&go=1&p_min=1'
            }

        planned = {
            'color': self.HEADING_GREEN,
            'type': 'Visit',
            'title': ungettext_lazy(
                u"%(count)d planlagt besøg",
                u"%(count)d planlagte besøg",
                'count'
            ),
            'queryset': self.sort_vo_queryset(
                Visit.unit_filter(
                    Visit.planned_queryset(
                        is_multi_sub=False
                    ),
                    unit_qs
                )
            )
        }
        if planned['queryset'].count() > 10:
            planned['limited_qs'] = planned['queryset'][:10]
            planned['button'] = {
                'text': _(u'Søg i alle'),
                'link': reverse('visit-search') + '?u=-3&w=-2&go=1'
            }

        return [visitlist, unplanned, planned]

    def lists_for_teachers(self):
        unit_qs = self.request.user.userprofile.get_unit_queryset()
        profile = self.request.user.userprofile

        return [
            {
                'color': self.HEADING_BLUE,
                'type': 'Product',
                'title': {
                    'text': _(u'Mine tilbud'),
                    'link': reverse('search') + '?u=-3'
                },
                'queryset': Product.objects.filter(
                    eventtime__visit=profile.potentially_assigned_visits
                ).distinct().order_by("title"),
            },
            {
                'color': self.HEADING_RED,
                'type': 'Visit',
                'title': ungettext_lazy(
                    u"%(count)d besøg der mangler undervisere",
                    u"%(count)d besøg der mangler undervisere",
                    'count'
                ),
                'queryset': Visit.unit_filter(
                    profile.can_be_assigned_to_qs, unit_qs
                ).order_by(
                    'eventtime__start', 'eventtime__end'
                )
            },
            {
                'color': self.HEADING_GREEN,
                'type': 'Visit',
                'title': ungettext_lazy(
                    u"%(count)d besøg hvor jeg er underviser",
                    u"%(count)d besøg hvor jeg er underviser",
                    'count'
                ),
                'queryset': self.sort_vo_queryset(
                    Visit.unit_filter(
                        profile.all_assigned_visits(),
                        unit_qs
                    )
                )
            }
        ]

    def lists_for_hosts(self):
        unit_qs = self.request.user.userprofile.get_unit_queryset()
        profile = self.request.user.userprofile

        return [
            {
                'color': self.HEADING_BLUE,
                'type': 'Product',
                'title': {
                    'text': _(u'Mine tilbud'),
                    'link': reverse('search') + '?u=-3'
                },
                'queryset': Product.objects.filter(
                    eventtime__visit=profile.potentially_assigned_visits
                ).distinct().order_by("title"),
            },
            {
                'color': self.HEADING_RED,
                'type': 'Visit',
                'title': ungettext_lazy(
                    u"%(count)d besøg der mangler værter",
                    u"%(count)d besøg der mangler værter",
                    'count',
                ),
                'queryset': Visit.unit_filter(
                    profile.can_be_assigned_to_qs, unit_qs
                ).order_by(
                    'eventtime__start', 'eventtime__end'
                )
            },
            {
                'color': self.HEADING_GREEN,
                'type': 'Visit',
                'title': ungettext_lazy(
                    u"%(count)d besøg hvor jeg er vært",
                    u"%(count)d besøg hvor jeg er vært",
                    'count'
                ),
                'queryset': self.sort_vo_queryset(
                    Visit.unit_filter(
                        profile.all_assigned_visits(), unit_qs
                    )
                )
            }
        ]


class CreateUserView(FormView, UpdateView):
    model = User
    form_class = UserCreateForm
    template_name = 'profile/create_user.html'
    object = None

    def get_object(self):
        if self.object is None:
            pk = self.kwargs.get('pk')
            self.object = User.objects.get(id=pk) if pk is not None else None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(CreateUserView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        current_profile = current_user.userprofile
        current_role = current_profile.get_role()
        current_unit = current_profile.organizationalunit

        self.get_object()

        if current_role in EDIT_ROLES:
            if self.request.method == 'POST':
                if current_role == FACULTY_EDITOR:
                    # This should not be possible!
                    if current_profile.organizationalunit is None:
                        raise AccessDenied(
                            _(u"Du har rollen 'Fakultetsredaktør', men " +
                              "er ikke tilknyttet nogen enhed.")
                        )
                    unit = OrganizationalUnit.objects.get(
                        pk=self.request.POST[u'organizationalunit']
                    )
                    if unit and not unit.belongs_to(current_unit):
                        raise AccessDenied(
                            _(u"Du kan kun redigere enheder, som " +
                              "ligger under dit fakultet.")
                        )
                elif current_role == COORDINATOR:
                    # This should not be possible!
                    if current_profile.organizationalunit is None:
                        raise AccessDenied(
                            _(u"Du har rollen 'Koordinator', men er ikke " +
                              "tilknyttet nogen enhed.")
                        )
                    unit = OrganizationalUnit.objects.get(
                        pk=self.request.POST[u'organizationalunit']
                    )
                    if unit and not unit == current_unit:
                        raise AccessDenied(
                            _(u"Du kan kun redigere enheder, som du selv er" +
                              " koordinator for.")
                        )
            if hasattr(self.object, 'userprofile'):
                object_role = self.object.userprofile.get_role()
                if self.object != current_user and \
                        object_role not in current_profile.available_roles:
                    raise AccessDenied(
                        _(u"Du har ikke rettigheder til at redigere brugere "
                          u"med rollen \"%s\""
                          % profile_models.role_to_text(object_role))
                    )
            return result
        else:
            # Allow all users to edit themselves
            if self.object.pk == self.request.user.pk:
                return result
            else:
                raise PermissionDenied

    def get(self, request, *args, **kwargs):
        self.get_object()
        return self.render_to_response(
            self.get_context_data(form=self.get_form())
        )

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        self.get_object()

        form = self.get_form()
        if form.is_valid():
            user_role_id = int(self.request.POST[u'role'])
            unit_id = int(self.request.POST[u'organizationalunit'])

            user = form.save()
            user_role = UserRole.objects.get(pk=user_role_id)
            unit = OrganizationalUnit.objects.get(pk=unit_id)

            cd = form.cleaned_data
            add_info = cd['additional_information']

            # Create
            if not pk:
                user_profile = UserProfile(
                    user=user,
                    user_role=user_role,
                    organizationalunit=unit,
                    additional_information=add_info,
                )
            else:
                # Update
                user_profile = user.userprofile
                user_profile.user = user
                user_profile.user_role = user_role
                user_profile.organizationalunit = unit
                cd = form.cleaned_data
                user_profile.additional_information = add_info

            user_profile.save()

            # Send email to newly created users
            if not pk:
                try:
                    KUEmailMessage.send_email(
                        EmailTemplateType.system__user_created,
                        {
                            'user': user,
                            'password': form.cleaned_data['password1'],
                        },
                        [user],
                        user
                    )
                except Exception as e:
                    print "Error sending mail to user: %s" % e

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
        kwargs['user'] = self.request.user

        return kwargs

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_success_url(self):
        try:
            if self.request.user.userprofile.get_role() in EDIT_ROLES:
                return reverse("user_list")
            else:
                return reverse("user_profile")
        except:
            return '/'


class DeleteUserView(DeleteView):

    model = User
    template_name = 'profile/user_confirm_delete.html'

    def get_success_url(self):
        return "/profile/users"

    def delete(self, request, *args, **kwargs):
        VisitComment.on_delete_user(self.get_object())
        return super(DeleteUserView, self).delete(request, *args, **kwargs)


class UserListView(EditorRequriedMixin, ListView):
    model = User
    template_name = 'profile/user_list.html'
    context_object_name = "users"
    selected_unit = None
    selected_role = None

    def get_queryset(self):

        user = self.request.user
        unit_qs = user.userprofile.get_unit_queryset()

        qs = self.model.objects.filter(
            userprofile__organizationalunit__in=unit_qs
        )

        try:
            self.selected_unit = int(
                self.request.GET.get("unit", None)
            )
        except:
            pass
        if self.selected_unit:
            qs = qs.filter(userprofile__organizationalunit=self.selected_unit)

        try:
            self.selected_role = int(self.request.GET.get("role", None))
        except:
            pass
        if self.selected_role is not None:
            qs = qs.filter(userprofile__user_role__role=self.selected_role)

        q = self.request.GET.get("q", None)
        if q:
            qs = qs.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )

        return qs.order_by('first_name', 'last_name', 'username')

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
    model = OrganizationalUnit

    def get_context_data(self, **kwargs):
        context = super(UnitListView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        user = self.request.user
        return user.userprofile.get_unit_queryset()


class StatisticsView(EditorRequriedMixin, TemplateView):
    template_name = "profile/statistics.html"
    form_class = StatisticsForm
    organizationalunits = []

    def get_context_data(self, **kwargs):
        context = {}
        context['user'] = self.request.user
        current_tz = timezone.get_current_timezone()
        from_date = None
        to_date = None
        if self.request.GET.get('from_date') \
                and self.request.GET.get('from_date') != '':
            from_date = datetime.strptime(
                self.request.GET.get('from_date', None),
                '%d-%m-%Y'
            )
            from_date = current_tz.localize(from_date)
        if self.request.GET.get('to_date') \
                and self.request.GET.get('to_date') != '':
            to_date = datetime.strptime(
                self.request.GET.get('to_date', None),
                '%d-%m-%Y'
            )
            to_date = current_tz.localize(to_date)

        if self.organizationalunits:
            context['organizationalunits'] = self.organizationalunits
            qs = Booking.objects\
                .select_related(
                    'visit__productresource_ptr__organizationalunit'
                ) \
                .select_related('booker__school')\
                .prefetch_related('bookinggymnasiesubjectlevel_set__subject') \
                .prefetch_related('bookinggymnasiesubjectlevel_set__level') \
                .prefetch_related('bookinggrundskolesubjectlevel_set'
                                  '__subject')\
                .prefetch_related('bookinggrundskolesubjectlevel_set__level') \
                .filter(
                    visit__productresource_ptr__organizationalunit_id__in=self
                    .organizationalunits
                )
            if from_date:
                qs = qs.filter(visit__eventtime__start__gte=from_date)
            if to_date:
                qs = qs.filter(visit__eventtime__end__lt=to_date)
            qs = qs.order_by('visit__productresource_ptr')
            context['bookings'] = qs
        context.update(kwargs)

        return super(StatisticsView, self).get_context_data(**context)

    def get(self, request, *args, **kwargs):
        user = self.request.user
        form = self.form_class()
        form.fields['organizationalunits'].queryset = \
            user.userprofile.get_unit_queryset()
        unit_ids = []
        for unit_id in self.request.GET.getlist('organizationalunits', None):
            unit_ids.append(int(unit_id))
        if user.userprofile.organizationalunit:
            form.fields['organizationalunits'].initial = \
                [user.userprofile.organizationalunit.pk]
            form.fields['organizationalunits'].empty_label = None
        if len(unit_ids) > 0:
            self.organizationalunits = OrganizationalUnit.objects.all()\
                .filter(pk__in=unit_ids)
            form.fields['organizationalunits'].initial = \
                self.organizationalunits
        if self.request.GET.get('from_date') != '':
            form.fields['from_date'].initial = \
                self.request.GET.get('from_date', None)
        if self.request.GET.get('to_date') != '':
            form.fields['to_date'].initial = \
                self.request.GET.get('to_date', None)
        # Handle csv download
        if self.request.GET.get('view') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response[
                'Content-Disposition'] = 'attachment; filename="statistik.csv"'
            return self._write_csv(response)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def _write_csv(self, response):
        context = self.get_context_data()
        writer = UnicodeWriter(response, delimiter=';')

        # Heading
        writer.writerow([
            _(u"Enhed"), _(u"Tilmelding"), _(u"Type"), _(u"Tilbud"),
            _(u"Besøgsdato"), _(u"Klassetrin/Niveau"), _(u"Antal deltagere"),
            _(u"Oplæg om uddannelser"), _(u"Rundvisning"), _(u"Andet"),
            _(u"Region"), _(u"Skole"), _(u"Postnummer og by"), _(u"Adresse"),
            _(u"Lærer"), _(u"Lærer email"), _(u"Bemærkninger fra koordinator"),
            _(u"Bemærkninger fra lærer"), _(u"Værter"), _(u"Undervisere")
        ])
        # Rows
        for booking in context['bookings']:
            no = _(u'Nej')
            yes = _(u'Ja')
            presentation_desired = no
            tour_desired = no
            custom_desired = no
            has_classbooking = False
            try:
                has_classbooking = (booking.classbooking is not None)
            except:
                pass

            if has_classbooking:
                if booking.classbooking.presentation_desired:
                    presentation_desired = yes
                if booking.classbooking.tour_desired:
                    tour_desired = yes
                if booking.classbooking.custom_desired:
                    custom_desired = yes

            writer.writerow([
                booking.visit.product.resource_ptr.organizationalunit.name,
                booking.__unicode__(),
                booking.visit.get_type_display(),
                booking.visit.product.resource_ptr.title,
                str(booking.visit.first_eventtime.start) + " til " +
                str(booking.visit.first_eventtime.end),
                u", ".join([
                    u'%s/%s' % (x.subject, x.level)
                    for x in booking.bookinggrundskolesubjectlevel_set.all()
                ]) +
                u", ".join([
                    u'%s/%s' % (x.subject, x.level)
                    for x in
                    booking.bookinggymnasiesubjectlevel_set.all()
                ]),
                str(booking.booker.attendee_count),
                presentation_desired,
                tour_desired,
                custom_desired,
                booking.booker.school.postcode.region.name or "",
                (booking.booker.school.name or "") + "(" +
                booking.booker.school.get_type_display() + ")",
                str(booking.booker.school.postcode.number) + " " +
                booking.booker.school.postcode.city,
                str(booking.booker.school.address),
                booking.booker.get_full_name(),
                booking.booker.get_email(),
                booking.visit.product.resource_ptr.comment,
                booking.comments,
                u", ".join([
                    u'%s' % (x.get_full_name())
                    for x in
                    booking.hosts.all()
                ]),
                u", ".join([
                    u'%s' % (x.get_full_name())
                    for x in
                    booking.teachers.all()
                ]),
            ])

        return response


class EmailLoginView(DetailView):
    model = EmailLoginURL
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
            return redirect(
                reverse('standard_login') +
                "?next=" + self.get_dest(request, *args, **kwargs)
            )

        return super(EmailLoginView, self).dispatch(request, *args, **kwargs)

    def redirect_to_self(self, request, *args, **kwargs):
        return redirect(self.object.as_url())

    def get_dest(self, request, *args, **kwargs):
        dest = self.object.success_url

        if 'dest_url' in kwargs and kwargs['dest_url'] != dest:
            warnings.warn(
                "URL mistmatch when loggin user '%s' in: '%s' vs '%s'" % (
                    self.object.user,
                    kwargs['dest_url'],
                    dest
                )
            )
        return dest

    def redirect_to_destination(self, request, *args, **kwargs):
        return redirect(self.get_dest(request, *args, **kwargs))


class EditMyProductsView(EditorRequriedMixin, UpdateView):
    model = UserProfile
    form_class = EditMyProductsForm
    template_name = 'profile/my_resources.html'

    def get_form(self, form_class=None):
        form = super(EditMyProductsView, self).get_form(form_class=form_class)

        userprofile = self.request.user.userprofile

        form.fields['my_resources'].queryset = Product.objects.filter(
            organizationalunit=userprofile.get_unit_queryset()
        ).order_by('title')

        return form

    def get_object(self, queryset=None):
        return self.request.user.userprofile

    def post(self, request, *args, **kwargs):
        if request.POST.get("cancel"):
            return redirect(self.get_success_url())

        return super(EditMyProductsView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('user_profile')


class AvailabilityView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'profile/availability.html'

    def get_object(self, queryset=None):
        """ Look up the userprofile from the user pk.
            Only allow lookups of TEACHERs and HOSTs.
        """
        try:
            # Get the single item from the filtered queryset
            obj = self.model.objects.get(
                user__pk=self.kwargs.get("user_pk"),
                user_role__role__in=[TEACHER, HOST]
            )
        except self.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': self.model._meta.verbose_name})
        return obj

    def get_context_data(self, **kwargs):
        context = {}

        context['accepted'] = self.to_datelist(
            self.object.all_assigned_visits()
        )

        if self.object.is_teacher:
            unaccepted_qs = self.object.requested_as_teacher_for_qs(
                exclude_accepted=True
            ).order_by('eventtime__start')
            context['unaccepted'] = self.to_datelist(unaccepted_qs)
        elif self.object.is_host:
            unaccepted_qs = self.object.requested_as_host_for_qs(
                exclude_accepted=True
            ).order_by('eventtime__start')
            context['unaccepted'] = self.to_datelist(unaccepted_qs)
        else:
            context['not_a_teacher'] = True

        context.update(kwargs)

        return super(
            AvailabilityView, self
        ).get_context_data(**context)

    def to_datelist(self, qs):
        dates = []
        current = None
        today = timezone.localtime(timezone.now()).date()
        for x in qs:
            if x.eventtime and x.eventtime.start:
                date = timezone.localtime(x.eventtime.start).date()
            else:
                date = None
            if current is None or current['date'] != date:
                if today and date > today:
                    dates.append({
                        'date': today,
                        'today': True,
                        'items': []
                    })
                    today = None

                current = {
                    'date': date,
                    'items': [],
                    'today': False
                }

                if today and today == date:
                    current['today'] = True
                    today = None

                dates.append(current)

            current['items'].append(x)

        if today:
            dates.append({
                'date': today,
                'today': True,
                'items': []
            })

        return dates
