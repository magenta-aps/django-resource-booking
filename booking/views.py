# -*- coding: utf-8 -*-

import json

from datetime import datetime, timedelta

from dateutil import parser
from dateutil.rrule import rrulestr
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic.edit import UpdateView
from django.views.defaults import bad_request

from profile.models import EDIT_ROLES
from profile.models import role_to_text

from booking.models import OtherResource, Visit, VisitOccurrence, StudyMaterial
from booking.models import Resource, Subject, GymnasieLevel
from booking.models import Room
from booking.models import PostCode, School
from booking.models import Booking
from booking.models import ResourceGymnasieFag, ResourceGrundskoleFag
from booking.forms import ResourceInitialForm, OtherResourceForm, VisitForm
from booking.forms import ClassBookingForm, TeacherBookingForm
from booking.forms import VisitStudyMaterialForm, BookingSubjectLevelForm
from booking.forms import BookerForm


i18n_test = _(u"Dette tester oversættelses-systemet")

# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


class LoginRequiredMixin(object):
    """Include this mixin to require login.

    Mainly useful for users who are not coordinators or administrators.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Check that user is logged in and dispatch."""
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class AccessDenied(PermissionDenied):
    def __init__(self, text, *args, **kwargs):
        _text = text
        print _text
        return super(AccessDenied, self).__init__(text, *args, **kwargs)

    def __unicode__(self):
        print self._text
        return unicode(self._text)


class RoleRequiredMixin(object):
    """Require that user has any of a number of roles."""

    # Roles is a list of required roles - maybe only one.
    # Each user can have only one role, and the condition is fulfilled
    # if one is found.

    roles = []  # Specify in subclass.

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            role = current_user.userprofile.get_role()
            if role in self.roles:
                return super(RoleRequiredMixin, self).dispatch(*args, **kwargs)
        else:
            pass
        txts = map(role_to_text, self.roles)
        # TODO: Render this with the error message!
        raise AccessDenied(
            u"Kun brugere med disse roller kan logge ind: " +
            u",".join(txts)
        )


class SearchView(ListView):
    """Class for handling main search."""
    model = Resource
    template_name = "resource/searchresult.html"
    context_object_name = "results"
    paginate_by = 10
    base_queryset = None
    filters = None
    from_datetime = None
    to_datetime = None

    def get_date_from_request(self, queryparam):
        val = self.request.GET.get(queryparam)
        if not val:
            return None
        try:
            val = datetime.strptime(val, '%d-%m-%Y')
            val = timezone.make_aware(val)
        except Exception:
            val = None
        return val

    def get_base_queryset(self):
        if self.base_queryset is None:
            searchexpression = self.request.GET.get("q", "")

            qs = self.model.objects.search(searchexpression)

            date_cond = None

            # Filter on from-time if one is specified or from current time
            # if not
            t_from = self.get_date_from_request("from")
            if t_from is None:
                t_from = timezone.now()
            self.from_datetime = t_from

            # Search for either resources without dates specified or
            # resources that have times available in the future
            date_cond = Q(
                Q(visit__visitoccurrence__start_datetime__isnull=True) |
                Q(visit__visitoccurrence__start_datetime__gt=t_from)
            )

            # To time will match latest end time if it exists and else
            # match the first endtime
            t_to = self.get_date_from_request("to")
            if t_to:
                date_cond = date_cond & Q(
                    Q(
                        Q(visit__visitoccurrence__end_datetime2__isnull=True) &
                        Q(visit__visitoccurrence__end_datetime1__lte=t_to)
                    ) |
                    Q(
                        visit__visitoccurrence__end_datetime2__lte=t_to
                    )
                )
            self.to_datetime = t_to

            # Only do date matching on resources that are actual visits
            qs = qs.filter(Q(visit__isnull=True) | date_cond)

            self.base_queryset = qs

        return self.base_queryset

    def annotate(self, qs):
        return qs.annotate(
            occ_starttime=F('visit__visitoccurrence__start_datetime')
        )

    def get_filters(self):
        if self.filters is None:
            self.filters = {}

            # Audience will always include a search for resources marked for
            # all audiences.
            a = self.request.GET.getlist("a")
            if a:
                a.append(Resource.AUDIENCE_ALL)
                self.filters["audience__in"] = a

            t = self.request.GET.getlist("t")
            if t:
                self.filters["type__in"] = t
            f = set(self.request.GET.getlist("f"))
            for g in self.request.GET.getlist("g"):
                f.add(g)
            if f:
                self.filters["subjects__in"] = f
            self.filters["state__in"] = [Resource.ACTIVE]

        return self.filters

    def get_queryset(self):
        filters = self.get_filters()
        qs = self.get_base_queryset().filter(**filters)
        qs = self.annotate(qs)
        return qs

    def make_facet(self, facet_field, choice_tuples, selected,
                   selected_value='checked="checked"',
                   add_to_all=None):

        selected = set(selected)
        hits = {}
        choices = []

        # Remove filter for the field we want to facetize
        new_filters = {}
        for k, v in self.get_filters().iteritems():
            if not k.startswith(facet_field):
                new_filters[k] = v

        qs = self.get_base_queryset().filter(**new_filters)
        qs = qs.values(facet_field).annotate(hits=Count("pk"))
        for item in qs:
            hits[item[facet_field]] = item["hits"]

        # This adds all hits on a certain keys to the hits of all other keys.
        if add_to_all is not None:
            keys = set(add_to_all)
            to_add = 0

            for key in keys:
                if key in hits:
                    to_add = to_add + hits[key]
                    del hits[key]

            for v, n in choice_tuples:
                if v in keys:
                    continue

                if v in hits:
                    hits[v] += to_add
                else:
                    hits[v] = to_add

        for value, name in choice_tuples:
            if value not in hits:
                continue

            if unicode(value) in selected:
                sel = selected_value
            else:
                sel = ''

            choices.append({
                'label': name,
                'value': value,
                'selected': sel,
                'hits': hits[value]
            })

        return choices

    def get_context_data(self, **kwargs):
        context = {}

        # Store the querystring without the page and pagesize arguments
        qdict = self.request.GET.copy()
        if "page" in qdict:
            qdict.pop("page")
        if "pagesize" in qdict:
            qdict.pop("pagesize")
        context["qstring"] = qdict.urlencode()

        context['pagesizes'] = [5, 10, 15, 20]

        context["audience_choices"] = self.make_facet(
            "audience",
            self.model.audience_choices,
            self.request.GET.getlist("a"),
            add_to_all=[Resource.AUDIENCE_ALL]
        )

        context["type_choices"] = self.make_facet(
            "type",
            self.model.resource_type_choices,
            self.request.GET.getlist("t"),
        )

        gym_subject_choices = []
        gs_subject_choices = []

        for s in Subject.objects.all():
            val = (s.pk, s.name)

            if s.subject_type & Subject.SUBJECT_TYPE_GYMNASIE:
                gym_subject_choices.append(val)

            if s.subject_type & Subject.SUBJECT_TYPE_GRUNDSKOLE:
                gs_subject_choices.append(val)

        gym_selected = self.request.GET.getlist("f")
        context["gymnasie_selected"] = gym_selected
        context["gymnasie_choices"] = self.make_facet(
            "subjects",
            gym_subject_choices,
            gym_selected,
        )

        gs_selected = self.request.GET.getlist("g")
        context["grundskole_selected"] = gs_selected
        context["grundskole_choices"] = self.make_facet(
            "subjects",
            gs_subject_choices,
            gs_selected,
        )

        context['from_datetime'] = self.from_datetime
        context['to_datetime'] = self.to_datetime

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'text': _(u'Søgeresultatliste')},
        ]

        querylist = []
        for key in ['q', 'page', 'pagesize', 't', 'a', 'f', 'g', 'from', 'to']:
            values = self.request.GET.getlist(key)
            if values is not None and len(values) > 0:
                for value in values:
                    if value is not None and len(unicode(value)) > 0:
                        querylist.append("%s=%s" % (key, value))
        if len(querylist) > 0:
            context['fullquery'] = reverse('search') + \
                "?" + "&".join(querylist)
        else:
            context['fullquery'] = None

        context.update(kwargs)
        return super(SearchView, self).get_context_data(**context)

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)

        if size == "all":
            return None

        return size


class EditResourceInitialView(TemplateView):

    template_name = 'resource/form.html'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            if OtherResource.objects.filter(id=pk).count() > 0:
                return redirect(reverse('otherresource-edit', args=[pk]))
            elif Visit.objects.filter(id=pk).count() > 0:
                return redirect(reverse('visit-edit', args=[pk]))
            else:
                raise Http404
        else:
            form = ResourceInitialForm()
            return self.render_to_response(
                self.get_context_data(form=form)
            )

    def post(self, request, *args, **kwargs):
        form = ResourceInitialForm(request.POST)
        if form.is_valid():
            type_id = int(form.cleaned_data['type'])
            if type_id in Visit.applicable_types:
                return redirect(reverse('visit-create') + "?type=%d" % type_id)
            else:
                return redirect(reverse('otherresource-create') +
                                "?type=%d" % type_id)

        return self.render_to_response(
            self.get_context_data(form=form)
        )


class ResourceDetailView(View):

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            if OtherResource.objects.filter(id=pk).count() > 0:
                return redirect(reverse('otherresource-view', args=[pk]))
            elif Visit.objects.filter(id=pk).count() > 0:
                return redirect(reverse('visit-view', args=[pk]))
        raise Http404


class EditResourceView(UpdateView):

    def __init__(self, *args, **kwargs):
        super(EditResourceView, self).__init__(*args, **kwargs)
        self.object = None

    def get_form_kwargs(self):
        kwargs = super(EditResourceView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(EditResourceView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else self.model.objects.get(id=pk)
        if self.object is not None and self.object.unit:
            if not current_user.userprofile.can_edit(self.object):
                raise AccessDenied(
                    _(u"Du kan kun redigere enheder,som du selv er" +
                      " koordinator for.")
                )
        return result

    def get_context_data(self, **kwargs):
        context = {}

        context['gymnasiefag_choices'] = Subject.gymnasiefag_qs()
        context['grundskolefag_choices'] = Subject.grundskolefag_qs()
        context['gymnasie_level_choices'] = \
            GymnasieLevel.objects.all().order_by('level')

        context['gymnasiefag_selected'] = self.gymnasiefag_selected()
        context['grundskolefag_selected'] = self.grundskolefag_selected()

        context['klassetrin_range'] = range(1, 9)

        context.update(kwargs)

        return super(EditResourceView, self).get_context_data(**context)

    def gymnasiefag_selected(self):
        result = []
        obj = self.object
        if self.request.method == 'GET':
            if obj and obj.pk:
                for x in obj.resourcegymnasiefag_set.all():
                    result.append({
                        'submitvalue': x.as_submitvalue(),
                        'description': x.display_value()
                    })
        elif self.request.method == 'POST':
            submitvalue = self.request.POST.getlist('gymnasiefag', [])
            for sv_text in submitvalue:
                sv = sv_text.split(",")
                subject_pk = sv.pop(0)
                subject = Subject.objects.get(pk=subject_pk)
                result.append({
                    'submitvalue': sv_text,
                    'description': ResourceGymnasieFag.display(
                        subject,
                        [GymnasieLevel.objects.get(pk=x) for x in sv]
                    )
                })

        return result

    def grundskolefag_selected(self):
        result = []
        obj = self.object
        if self.request.method == 'GET':
            if obj and obj.pk:
                for x in obj.resourcegrundskolefag_set.all():
                    result.append({
                        'submitvalue': x.as_submitvalue(),
                        'description': x.display_value()
                    })
        elif self.request.method == 'POST':
            submitvalue = self.request.POST.getlist('grundskolefag', [])
            for sv_text in submitvalue:
                sv = sv_text.split(",")
                subject_pk = sv.pop(0)
                lv_min = sv.pop(0)
                lv_max = sv.pop(0)
                subject = Subject.objects.get(pk=subject_pk)
                result.append({
                    'submitvalue': sv_text,
                    'description': ResourceGrundskoleFag.display(
                        subject, lv_min, lv_max
                    )
                })

        return result

    def save_subjects(self, obj):
        existing_gym_fag = {}
        for x in obj.resourcegymnasiefag_set.all():
            existing_gym_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('gymnasiefag', []):
            if gval in existing_gym_fag:
                del existing_gym_fag[gval]
            else:
                ResourceGymnasieFag.create_from_submitvalue(obj, gval)

        # Delete any remaining values that were not submitted
        for x in existing_gym_fag.itervalues():
            x.delete()

        existing_gs_fag = {}
        for x in obj.resourcegrundskolefag_set.all():
            existing_gs_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('grundskolefag', []):
            if gval in existing_gs_fag:
                del existing_gs_fag[gval]
            else:
                ResourceGrundskoleFag.create_from_submitvalue(
                    obj, gval
                )

        # Delete any remaining values that were not submitted
        for x in existing_gs_fag.itervalues():
            x.delete()
        


class EditOtherResourceView(EditResourceView):

    template_name = 'otherresource/form.html'
    form_class = OtherResourceForm
    model = OtherResource

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = EDIT_ROLES

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        try:
            self.object = OtherResource() if pk is None\
                else OtherResource.objects.get(id=pk)
        except ObjectDoesNotExist:
            raise Http404
        try:
            type = int(request.GET['type'])
            if type in OtherResource.applicable_types:
                self.object.type = type
        except:
            pass
        form = self.get_form()
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        is_cloning = kwargs.get("clone", False)
        if is_cloning or not hasattr(self, 'object') or self.object is None:
            if pk is None or is_cloning:
                self.object = None
            else:
                try:
                    self.object = OtherResource.objects.get(id=pk)
                    if is_cloning:
                        self.object.pk = None
                except ObjectDoesNotExist:
                    raise Http404
        form = self.get_form()
        if form.is_valid():
            obj = form.save()

            # Save subjects
            self.save_subjects(obj)

            return super(EditOtherResourceView, self).form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        try:
            return reverse('otherresource-view', args=[self.object.id])
        except:
            return '/'


class OtherResourceDetailView(DetailView):
    """Display Visit details"""
    model = OtherResource
    template_name = 'otherresource/details.html'

    def get_queryset(self):
        """Get queryset, only include active visits."""
        qs = super(OtherResourceDetailView, self).get_queryset()
        # Dismiss visits that are not active.
        if not self.request.user.is_authenticated():
            qs = qs.filter(state=Resource.ACTIVE)
        return qs

    def get_context_data(self, **kwargs):
        context = {}

        user = self.request.user

        if (hasattr(user, 'userprofile') and
                user.userprofile.can_edit(self.object)):
            context['can_edit'] = True
        else:
            context['can_edit'] = False

        # if self.object.type in [Resource.STUDENT_FOR_A_DAY,
        #                        Resource.STUDY_PROJECT,
        #                        Resource.GROUP_VISIT,
        #                        Resource.TEACHER_EVENT]:
        #    context['can_book'] = True
        # else:
        context['can_book'] = False

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': self.request.GET.get("search", reverse('search')),
             'text': _(u'Søgeresultatliste')},
            {'text': _(u'Detaljevisning')},
        ]

        context.update(kwargs)

        return super(OtherResourceDetailView, self).get_context_data(**context)


class EditVisitView(RoleRequiredMixin, EditResourceView):

    template_name = 'visit/form.html'
    form_class = VisitForm
    model = Visit

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = EDIT_ROLES

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        try:
            self.object = Visit() if pk is None else Visit.objects.get(id=pk)
        except ObjectDoesNotExist:
            raise Http404
        try:
            type = int(request.GET['type'])
            if type in Visit.applicable_types:
                self.object.type = type
        except:
            pass
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(None, instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        is_cloning = kwargs.get("clone", False)
        if is_cloning or not hasattr(self, 'object') or self.object is None:
            if pk is None or is_cloning:
                self.object = None
            else:
                try:
                    self.object = Visit.objects.get(id=pk)
                    if is_cloning:
                        self.object.pk = None
                except ObjectDoesNotExist:
                    raise Http404
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(request.POST)
        if form.is_valid():
            visit = form.save()
            if fileformset.is_valid():
                visit.save()

                # Update rooms
                existing_rooms = set([x.name for x in visit.room_set.all()])

                new_rooms = request.POST.getlist("rooms")
                for roomname in new_rooms:
                    if roomname in existing_rooms:
                        existing_rooms.remove(roomname)
                    else:
                        new_room = Room(visit=visit, name=roomname)
                        new_room.save()

                # Delete any rooms left in existing rooms
                if len(existing_rooms) > 0:
                    visit.room_set.all().filter(
                        name__in=existing_rooms
                    ).delete()

                # Attach uploaded files
                for fileform in fileformset:
                    try:
                        instance = StudyMaterial(
                            visit=visit,
                            file=request.FILES["%s-file" % fileform.prefix]
                        )
                        instance.save()
                    except:
                        pass
            # update occurrences
            existing_visit_occurrences = \
                set([x.start_datetime
                     for x in visit.visitoccurrence_set.all()])

            # convert date strings to datetimes
            dates = request.POST.getlist(u'occurrences')

            datetimes = []
            if dates is not None:
                for date in dates:
                    dt = timezone.make_aware(
                        parser.parse(date, dayfirst=True),
                        timezone.pytz.timezone('Europe/Copenhagen')
                    )
                    datetimes.append(dt)
            # remove existing to avoid duplicates,
            # then save the rest...
            for date_t in datetimes:
                if date_t in existing_visit_occurrences:
                    existing_visit_occurrences.remove(date_t)
                else:
                    duration = request.POST[u'duration']
                    hours = int(duration[0:2])
                    minutes = int(duration[3:5])
                    end_datetime = date_t
                    if duration is not None:
                        end_datetime = date_t + timedelta(
                            hours=hours,
                            minutes=minutes
                        )
                    instance = VisitOccurrence(
                        start_datetime=date_t,
                        end_datetime1=end_datetime,
                        visit=visit
                    )
                    instance.save()
            # If the set of existing occurrences still is not empty,
            # it means that the user un-ticket one or more existing.
            # So, we remove those to...
            if len(existing_visit_occurrences) > 0:
                visit.visitoccurrence_set.all().filter(
                    start_datetime__in=existing_visit_occurrences
                ).delete()

            # Save subjects
            self.save_subjects(visit)

            return super(EditVisitView, self).form_valid(form)
        else:
            return self.form_invalid(form, fileformset)

    def get_context_data(self, **kwargs):
        context = {}

        if self.object and self.object.pk:
            context['rooms'] = self.object.room_set.all()
        else:
            context['rooms'] = []

        search_unit = None
        if self.object and self.object.unit:
            search_unit = self.object.unit
        else:
            if self.request.user and self.request.user.userprofile:
                search_unit = self.request.user.userprofile.unit

        if search_unit is not None:
            context['existingrooms'] = Room.objects.filter(
                visit__unit=search_unit
            ).order_by("name").distinct("name")
        else:
            context['existinrooms'] = []

        context['gymnasiefag_choices'] = Subject.gymnasiefag_qs()
        context['grundskolefag_choices'] = Subject.grundskolefag_qs()
        context['gymnasie_level_choices'] = \
            GymnasieLevel.objects.all().order_by('level')

        context['gymnasiefag_selected'] = self.gymnasiefag_selected()
        context['grundskolefag_selected'] = self.grundskolefag_selected()

        context['klassetrin_range'] = range(1, 9)

        context.update(kwargs)

        return super(EditVisitView, self).get_context_data(**context)

    def get_success_url(self):
        try:
            return reverse('visit-view', args=[self.object.id])
        except:
            return '/'

    def form_invalid(self, form, fileformset=None):
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )


class VisitDetailView(DetailView):
    """Display Visit details"""
    model = Visit
    template_name = 'visit/details.html'

    def get_queryset(self):
        """Get queryset, only include active visits."""
        qs = super(VisitDetailView, self).get_queryset()
        # Dismiss visits that are not active.
        if not self.request.user.is_authenticated():
            qs = qs.filter(state=Resource.ACTIVE)
        return qs

    def get_context_data(self, **kwargs):
        context = {}

        user = self.request.user

        if (hasattr(user, 'userprofile') and
                user.userprofile.can_edit(self.object)):
            context['can_edit'] = True
        else:
            context['can_edit'] = False

        if self.object.type in [Resource.STUDENT_FOR_A_DAY,
                                Resource.STUDY_PROJECT,
                                Resource.GROUP_VISIT,
                                Resource.TEACHER_EVENT]:
            context['can_book'] = True
        else:
            context['can_book'] = False

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': self.request.GET.get("search", reverse('search')),
             'text': _(u'Søgeresultatliste')},
            {'text': _(u'Detaljevisning')},
        ]

        context.update(kwargs)

        return super(VisitDetailView, self).get_context_data(**context)


class RrulestrView(View):

    def post(self, request):
        """
        Handle Ajax requests: Essentially, dateutil.rrule.rrulestr function
        exposed as a web service, expanding RRULEs to a list of datetimes.
        In addition, we add RRDATEs and return the sorted list in danish
        date format. If the string doesn't contain an UNTIL clause, we set it
        to 90 days in the future from datetime.now().
        If multiple start_times are present, the Cartesian product of
        dates x start_times is returned.
        """
        rrulestring = request.POST['rrulestr']
        now = timezone.now()
        tz = timezone.pytz.timezone('Europe/Copenhagen')
        dates = []
        lines = rrulestring.split("\n")
        times_list = request.POST[u'start_times'].split(',')
        visit_id = None
        if request.POST[u'visit_id'] != 'None':
            visit_id = int(request.POST[u'visit_id'])
        existing_dates_strings = set()

        if visit_id is not None:
            visit = Visit.objects.get(pk=visit_id)

            for occurrence in visit.visitoccurrence_set.all():
                existing_dates_strings.add(
                    occurrence.start_datetime.strftime('%d-%m-%Y %H:%M')
                )

        for line in lines:
            # When handling RRULEs, we don't want to send all dates until
            # 9999-12-31 to the client, which apparently is rrulestr() default
            # behaviour. Hence, we set a default UNTIL clause to 90 days in
            # the future from datetime.now()
            # Todo: This should probably be handled more elegantly
            if u'RRULE' in line and u'UNTIL=' not in line:
                line += u';UNTIL=%s' % (now + timedelta(90))\
                    .strftime('%Y%m%dT%H%M%S')
                dates += [
                    timezone.make_aware(x, tz) for x in rrulestr(
                        line, ignoretz=True
                    )
                ]
            # RRDATEs are appended to the dates list
            elif u'RDATE' in line:
                dates += [
                    timezone.make_aware(x, tz)for x in rrulestr(
                        line,
                        ignoretz=True
                    )
                ]
        # sort the list while still in ISO 8601 format,
        dates = sorted(set(dates))
        # Cartesian product: AxB
        # ['2016-01-01','2016-01-02'] x ['10:00','12:00'] ->
        # ['2016-01-01 10:00','2016-01-01 12:00',
        # '2016-01-02 10:00','2016-01-02 12:00']
        cartesian_dates = \
            [val.replace(  # parse time format: '00:00'
                hour=int(_[0:2]),
                minute=int(_[4:6]),
                second=0,
                microsecond=0
            ) for val in dates for _ in times_list]

        # convert to danish date format strings and off we go...
        date_strings = [x.strftime('%d-%m-%Y %H:%M') for x in cartesian_dates]

        dates_without_existing_dates = \
            [x for x in date_strings if x not in existing_dates_strings]
        return HttpResponse(
            json.dumps(dates_without_existing_dates),
            content_type='application/json'
        )


class PostcodeView(View):
    def get(self, request, *args, **kwargs):
        code = int(kwargs.get("code"))
        postcode = PostCode.get(code)
        city = postcode.city if postcode is not None else None
        region = {'id': postcode.region.id, 'name': postcode.region.name} \
            if postcode is not None else None
        return JsonResponse({'code': code, 'city': city, 'region': region})


class SchoolView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET['q']
        items = School.search(query)
        json = {'schools':
                [
                    {'name': item.name,
                     'postcode': item.postcode.number} for item in items
                ]
                }
        return JsonResponse(json)


class BookingView(UpdateView):

    visit = None

    def set_visit(self, visit_id):
        if visit_id is not None:
            try:
                self.visit = Visit.objects.get(id=visit_id)
            except:
                pass

    def get(self, request, *args, **kwargs):
        self.set_visit(kwargs.get("visit"))
        if self.visit is None:
            return bad_request(request)

        data = {'visit': self.visit}

        self.object = Booking()
        data.update(self.get_forms())
        return self.render_to_response(
            self.get_context_data(**data)
        )

    def post(self, request, *args, **kwargs):
        self.set_visit(kwargs.get("visit"))
        if self.visit is None:
            return bad_request(request)

        data = {'visit': self.visit}

        self.object = Booking()
        forms = self.get_forms(request.POST)

        # Hack: remove this form; we'll add it later when
        # we have our booking object
        hadSubjectForm = False
        if 'subjectform' in forms:
            del forms['subjectform']
            hadSubjectForm = True

        valid = True
        for (name, form) in forms.items():
            if not form.is_valid():
                valid = False

        if valid:
            if 'bookingform' in forms:
                booking = forms['bookingform'].save(commit=False)
            else:
                booking = self.object
            booking.visit = self.visit
            if 'bookerform' in forms:
                booking.booker = forms['bookerform'].save()

            booking.save()

            # We can't fetch this form before we have
            # a saved booking object to feed it, or we'll get an error
            if hadSubjectForm:
                subjectform = BookingSubjectLevelForm(request.POST,
                                                      instance=booking)
                if subjectform.is_valid():
                    subjectform.save()
            return redirect("/visit/%d/book/success" % self.visit.id)
        else:
            forms['subjectform'] = BookingSubjectLevelForm(request.POST)

        data.update(forms)
        return self.render_to_response(
            self.get_context_data(**data)
        )

    def get_forms(self, data=None):
        forms = {}
        if self.visit is not None:
            forms['bookerform'] = BookerForm(data, visit=self.visit)

            if self.visit.type == Resource.GROUP_VISIT:
                forms['bookingform'] = ClassBookingForm(data, visit=self.visit)
                forms['subjectform'] = BookingSubjectLevelForm(data)

            elif self.visit.audience == Resource.AUDIENCE_TEACHER:
                forms['bookingform'] = TeacherBookingForm(data,
                                                          visit=self.visit)
        return forms

    def get_template_names(self):
        if self.visit is None:
            return [""]
        if self.visit.type == Resource.STUDENT_FOR_A_DAY:
            return ["booking/studentforaday.html"]
        if self.visit.type == Resource.STUDY_PROJECT:
            return ["booking/srp.html"]
        if self.visit.type == Resource.GROUP_VISIT:
            return ["booking/classvisit.html"]
        if self.visit.type == Resource.TEACHER_EVENT:
            return ["booking/teachervisit.html"]


class BookingSuccessView(TemplateView):
    template_name = "booking/success.html"

    def get(self, request, *args, **kwargs):
        visit_id = kwargs.get("visit")
        visit = None
        if visit_id is not None:
            try:
                visit = Visit.objects.get(id=visit_id)
            except:
                pass
        if visit is None:
            return bad_request(request)

        data = {'visit': visit}

        return self.render_to_response(
            self.get_context_data(**data)
        )
