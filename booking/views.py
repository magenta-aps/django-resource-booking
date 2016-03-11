# -*- coding: utf-8 -*-

import json

from datetime import datetime, timedelta

from dateutil import parser
from dateutil.rrule import rrulestr
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Count
from django.db.models import Min
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.views.generic import View, TemplateView, ListView, DetailView
from django.views.generic.base import ContextMixin
from django.views.generic.edit import UpdateView, FormMixin, DeleteView
from django.views.defaults import bad_request

from profile.models import EDIT_ROLES
from profile.models import role_to_text
from booking.models import Visit, VisitOccurrence, StudyMaterial, \
    KUEmailMessage
from booking.models import Resource, Subject
from booking.models import Unit
from booking.models import OtherResource
from booking.models import GymnasieLevel
from booking.models import Room, Person
from booking.models import PostCode, School
from booking.models import Booking, Booker
from booking.models import ResourceGymnasieFag, ResourceGrundskoleFag
from booking.models import EmailTemplate
from booking.models import log_action
from booking.models import LOGACTION_CREATE, LOGACTION_CHANGE
from booking.forms import ResourceInitialForm, OtherResourceForm, VisitForm, \
    GuestEmailComposeForm

from booking.forms import StudentForADayForm, InternshipForm, OpenHouseForm, \
    TeacherVisitForm, ClassVisitForm, StudyProjectForm, AssignmentHelpForm, \
    StudyMaterialForm

from booking.forms import ClassBookingForm, TeacherBookingForm
from booking.forms import ResourceStudyMaterialForm, BookingSubjectLevelForm
from booking.forms import BookerForm
from booking.forms import EmailTemplateForm, EmailTemplatePreviewContextForm
from booking.forms import EmailComposeForm
from booking.forms import AdminVisitSearchForm
from booking.forms import VisitAutosendFormSet
from booking.utils import full_email

import urls


i18n_test = _(u"Dette tester oversættelses-systemet")


# Method for importing views from another module
def import_views(from_module):
    module_prefix = from_module.__name__
    import_dict = globals()
    for name, value in from_module.__dict__.iteritems():
        # Skip stuff that is not classes
        if not isinstance(value, type):
            continue
        # Skip stuff that is not views
        if not issubclass(value, View):
            continue

        # Skip stuff that is not native to the booking.models module
        if not value.__module__ == module_prefix:
            continue

        import_dict[name] = value


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
        print _text.encode('utf-8')
        return super(AccessDenied, self).__init__(text, *args, **kwargs)

    def __unicode__(self):
        print self._text.encode('utf-8')
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


class HasBackButtonMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(HasBackButtonMixin, self).get_context_data(**kwargs)
        context['oncancel'] = self.request.GET.get('back')
        return context


class ContactComposeView(FormMixin, HasBackButtonMixin, TemplateView):
    template_name = 'email/compose.html'
    form_class = GuestEmailComposeForm

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def post(self, request, *args, **kwargs):
        recipient_id = kwargs.get("recipient")
        form = self.get_form()
        if form.is_valid():
            template = EmailTemplate.get_template(
                EmailTemplate.SYSTEM__BASICMAIL_ENVELOPE,
                None
            )
            if template is None:
                raise Exception(_(u"There are no root templates with "
                                  u"the SYSTEM__BASICMAIL_ENVELOPE key"))
            context = {}
            context.update(form.cleaned_data)
            recipients = Person.objects.get(id=recipient_id)
            KUEmailMessage.send_email(template, context, recipients)
            return super(ContactComposeView, self).form_valid(form)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_success_url(self):
        return self.request.GET.get("back", "/")


class EmailComposeView(FormMixin, HasBackButtonMixin, TemplateView):
    template_name = 'email/compose.html'
    form_class = EmailComposeForm
    recipients = []
    template_key = None
    template_context = {}
    modal = True

    RECIPIENT_BOOKER = 'booker'
    RECIPIENT_PERSON = 'person'
    RECIPIENT_USER = 'user'
    RECIPIENT_CUSTOM = 'custom'
    RECIPIENT_SEPARATOR = ':'

    def dispatch(self, request, *args, **kwargs):
        try:  # see if there's a template key defined in the URL params
            self.template_key = int(request.GET.get("template", None))
        except (ValueError, TypeError):
            pass
        return super(EmailComposeView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        form.fields['recipients'].choices = self.recipients
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        form.fields['recipients'].choices = self.recipients
        if form.is_valid():
            data = form.cleaned_data
            template = EmailTemplate(
                subject=data['subject'],
                body=data['body']
            )
            context = self.template_context
            recipients = self.lookup_recipients(
                form.cleaned_data['recipients'])
            KUEmailMessage.send_email(template, context, recipients)
            return super(EmailComposeView, self).form_valid(form)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_initial(self):
        initial = super(EmailComposeView, self).get_initial()
        if self.template_key is not None:
            template = \
                EmailTemplate.get_template(self.template_key,
                                           self.get_unit())
            if template is not None:
                initial['subject'] = template.subject
                initial['body'] = template.body
        initial['recipients'] = [id for (id, label) in self.recipients]
        return initial

    def get_context_data(self, **kwargs):
        context = {}
        context['templates'] = EmailTemplate.get_template(self.template_key,
                                                          self.get_unit(),
                                                          True)
        context['template_key'] = self.template_key
        context['template_unit'] = self.get_unit()
        context['modal'] = self.modal
        context.update(kwargs)
        return super(EmailComposeView, self).get_context_data(**context)

    def lookup_recipients(self, recipient_ids):
        booker_ids = []
        person_ids = []
        user_ids = []
        customs = []
        for value in recipient_ids:
            (type, id) = value.split(self.RECIPIENT_SEPARATOR, 1)
            if type == self.RECIPIENT_BOOKER:
                booker_ids.append(id)
            elif type == self.RECIPIENT_PERSON:
                person_ids.append(id)
            elif type == self.RECIPIENT_USER:
                user_ids.append(id)
            elif type == self.RECIPIENT_CUSTOM:
                customs.append(id)
        return list(Booker.objects.filter(id__in=booker_ids)) + \
            list(Person.objects.filter(id__in=person_ids)) + \
            list(User.objects.filter(username__in=user_ids)) + \
            customs

    def get_unit(self):
        return self.request.user.userprofile.unit

    def get_template_names(self):
        if self.modal:
            return ['email/compose_modal.html']
        else:
            return ['email/compose.html']


class EmailSuccessView(TemplateView):
    template_name = "email/success.html"


class EditorRequriedMixin(RoleRequiredMixin):
    roles = EDIT_ROLES


class UnitAccessRequiredMixin(object):

    def check_item(self, item):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            if current_user.userprofile.can_edit(item):
                return
        raise AccessDenied(_(u"You cannot edit an object for a unit "
                             u"that you don't belong to"))

    def check_unit(self, unit):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            if current_user.userprofile.unit_access(unit):
                return
        raise AccessDenied(_(u"You cannot edit an object for a unit "
                             u"that you don't belong to"))


class AutologgerMixin(object):
    _old_state = {}

    def _as_state(self, obj=None):
        if obj is None:
            obj = self.object
        if obj and obj.pk:
            return model_to_dict(obj)
        else:
            return {}

    def _get_changed_fields(self, compare_state):
        new_state = self._as_state()

        result = {}

        for key in compare_state:
            if key in new_state:
                if compare_state[key] != new_state[key]:
                    result[key] = (compare_state[key], new_state[key])
                del new_state[key]
            else:
                result[key] = (compare_state[key], None)

        for key in new_state:
            result[key] = (None, new_state[key])

        return result

    def _field_value_to_display(self, fieldname, value):
        field = self.model._meta.get_field(fieldname)
        fname = field.verbose_name

        if value is None:
            return (fname, unicode(value))

        if field.many_to_one:
            try:
                o = field.related_model.objects.get(pk=value)
                return (fname, unicode(o))
            except:
                return (fname, unicode(value))

        if field.many_to_many or field.one_to_many:
            res = []
            for x in value:
                try:
                    o = field.related_model.objects.get(pk=x)
                    res.append(unicode(o))
                except:
                    res.append(unicode(x))
            return (fname, ", ".join(res))

        if field.choices:
            d = dict(field.choices)
            if value in d:
                return (fname, unicode(d[value]))

        return (fname, unicode(value))

    def _changes_to_text(self, changes):
        if not changes:
            return ""

        result = {}
        for key, val in changes.iteritems():
            name, value = self._field_value_to_display(key, val[1])
            result[name] = value

        return "\n".join([
            u"%s: >>>%s<<<" % (x, result[x]) for x in sorted(result)
        ])

    def _log_changes(self):
        if self._old_state:
            action = LOGACTION_CHANGE
            msg = _(u"Ændrede felter:\n%s")
        else:
            action = LOGACTION_CREATE
            msg = _(u"Oprettet med felter:\n%s")

        changeset = self._get_changed_fields(self._old_state)

        log_action(
            self.request.user,
            self.object,
            action,
            msg % self._changes_to_text(changeset)
        )

    def get_object(self, queryset=None):
        res = super(AutologgerMixin, self).get_object(queryset)

        self._old_state = self._as_state(res)

        return res

    def form_valid(self, form):
        res = super(AutologgerMixin, self).form_valid(form)

        self._log_changes()

        return res


class LoggedViewMixin(object):
    def get_log_queryset(self):
        types = [ContentType.objects.get_for_model(self.model)]

        for rel in self.model._meta.get_all_related_objects():
            if not rel.one_to_one:
                continue

            rel_model = rel.related_model

            if self.model not in rel_model._meta.get_parent_list():
                continue

            types.append(
                ContentType.objects.get_for_model(rel_model)
            )

        qs = LogEntry.objects.filter(
            object_id=self.object.pk,
            content_type__in=types
        ).order_by('action_time')

        return qs

    def get_context_data(self, **kwargs):
        return super(LoggedViewMixin, self).get_context_data(
            log_entries=self.get_log_queryset(),
            **kwargs
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
    admin_form = None

    boolean_choice = (
        (1, _(u'Ja')),
        (0, _(u'Nej')),
    )

    def get_admin_form(self):
        if self.admin_form is None:
            if self.request.user.is_authenticated():
                self.admin_form = AdminVisitSearchForm(
                    self.request.GET,
                    user=self.request.user
                )
                self.admin_form.is_valid()
            else:
                self.admin_form = False

        return self.admin_form

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

            qs = qs.annotate(
                num_bookings=Count('visit__visitoccurrence__bookings')
            )

            date_cond = None

            # Filter on from-time if one is specified or from current time
            # if not
            t_from = self.get_date_from_request("from")
            if t_from is None:
                t_from = timezone.now()
            self.from_datetime = t_from

            # Search for either resources without dates specified or
            # resources that have times available in the future
            date_cond = (
                Q(visit__visitoccurrence__bookable=True) &
                Q(visit__visitoccurrence__start_datetime__gt=t_from)
            )

            # To time will match latest end time if it exists and else
            # match the first endtime
            t_to = self.get_date_from_request("to")
            if t_to:
                date_cond = date_cond & Q(
                    Q(visit__visitoccurrence__start_datetime__lte=t_from)
                )
            self.to_datetime = t_to

            qs = qs.filter(
                # Stuff that is not bookable
                Q(visit__isnull=True) |
                # Anything without any specific booking times
                Q(visit__visitoccurrence__isnull=True) |
                # Bookable occurences that matches the date conditions
                date_cond
            )

            qs = qs.distinct()

            self.base_queryset = qs

        return self.base_queryset

    def annotate(self, qs):
        return qs.annotate(
            num_occurences=Count('visit__visitoccurrence__pk'),
            first_occurence=Min('visit__visitoccurrence__start_datetime')
        )

    def get_filters(self):
        if self.filters is None:
            self.filters = {}

            for filter_method in (
                self.filter_by_audience,
                self.filter_by_type,
                self.filter_by_gymnasiefag,
                self.filter_by_grundskolefag
            ):
                try:
                    filter_method()
                except Exception as e:
                    print "Error while filtering query: %s" % e

            if not self.request.user.is_authenticated():
                self.filter_for_public_view()
            else:
                self.filter_for_admin_view(self.get_admin_form())

        return self.filters

    def filter_for_public_view(self):
        # Public users can only see active resources
        self.filters["state__in"] = [Resource.ACTIVE]

    def filter_by_audience(self):
        # Audience will always include a search for resources marked for
        # all audiences.
        a = [x for x in self.request.GET.getlist("a")]
        if a:
            a.append(Resource.AUDIENCE_ALL)
            self.filters["audience__in"] = a

    def filter_by_type(self):
        t = self.request.GET.getlist("t")
        if t:
            self.filters["type__in"] = t

    def filter_by_gymnasiefag(self):
        f = set(self.request.GET.getlist("f"))
        if f:
            self.filters["gymnasiefag__in"] = f

    def filter_by_grundskolefag(self):
        g = self.request.GET.getlist("g")
        if g:
            self.filters["grundskolefag__in"] = g

    def filter_for_admin_view(self, form):
        for filter_method in (
            self.filter_by_state,
            self.filter_by_enabled,
            self.filter_by_is_visit,
            self.filter_by_has_bookings,
            self.filter_by_unit,
        ):
            try:
                filter_method(form)
            except Exception as e:
                print "Error while admin-filtering query: %s" % e

    def filter_by_state(self, form):
        s = form.cleaned_data.get("s", "")
        if s != "":
            self.filters["state"] = s

    def filter_by_enabled(self, form):
        e = form.cleaned_data.get("e", "")
        if e != "":
            self.filters["enabled"] = e

    def filter_by_is_visit(self, form):
        v = form.cleaned_data.get("v", "")

        if v == "":
            return

        v = int(v)

        if v == AdminVisitSearchForm.IS_VISIT:
            self.filters["visit__pk__isnull"] = False
        elif v == AdminVisitSearchForm.IS_NOT_VISIT:
            self.filters["otherresource__pk__isnull"] = False

    def filter_by_has_bookings(self, form):
        b = form.cleaned_data.get("b", "")

        if b == "":
            return

        b = int(b)

        if b == AdminVisitSearchForm.HAS_BOOKINGS:
            self.filters["num_bookings__gt"] = 0
        elif b == AdminVisitSearchForm.HAS_NO_BOOKINGS:
            self.filters["num_bookings"] = 0

    def filter_by_unit(self, form):
        u = form.cleaned_data.get("u", "")

        if u == "":
            return

        u = int(u)

        if u == AdminVisitSearchForm.MY_UNIT:
            self.filters["unit"] = self.request.user.userprofile.unit
        elif u == AdminVisitSearchForm.MY_FACULTY:
            self.filters["unit"] = \
                self.request.user.userprofile.unit.get_faculty_queryset()
        elif u == AdminVisitSearchForm.MY_UNITS:
            self.filters["unit"] = \
                self.user.userprofile.get_unit_queryset()
        else:
            self.filters["unit__pk"] = u

    def get_queryset(self):
        filters = self.get_filters()
        qs = self.get_base_queryset().filter(**filters)
        qs = self.annotate(qs)
        return qs

    def make_facet(self, facet_field, choice_tuples, selected,
                   selected_value='checked="checked"',
                   add_to_all=None):

        hits = {}

        # Remove filter for the field we want to facetize
        new_filters = {}
        for k, v in self.get_filters().iteritems():
            if not k.startswith(facet_field):
                new_filters[k] = v

        base_qs = self.get_base_queryset().filter(**new_filters)

        qs = Resource.objects.filter(
            pk__in=base_qs
        ).values(facet_field).annotate(hits=Count("pk"))

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

        return self.choices_from_hits(choice_tuples, hits, selected,
                                      selected_value=selected_value)

    def choices_from_hits(self, choice_tuples, hits, selected,
                          selected_value='checked="checked"'):
        selected = set(selected)
        choices = []

        for value, name in choice_tuples:
            if value not in hits:
                continue

            if unicode(value) in selected:
                sel = 'checked="checked"'
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

        context['adminform'] = self.get_admin_form()

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
            "gymnasiefag",
            gym_subject_choices,
            gym_selected,
        )

        gs_selected = self.request.GET.getlist("g")
        context["grundskole_selected"] = gs_selected
        context["grundskole_choices"] = self.make_facet(
            "grundskolefag",
            gs_subject_choices,
            gs_selected,
        )

        context['from_datetime'] = self.from_datetime
        context['to_datetime'] = self.to_datetime

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'text': _(u'Søgeresultat')},
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
            context['thisurl'] = context['fullquery']
        else:
            context['fullquery'] = None
            context['thisurl'] = reverse('search')

        if (self.request.user.is_authenticated() and
                self.request.user.userprofile.has_edit_role()):

            context['has_edit_role'] = True

        context.update(kwargs)
        return super(SearchView, self).get_context_data(**context)

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)

        if size == "all":
            return None

        return size


class EditResourceInitialView(HasBackButtonMixin, TemplateView):

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
            back = urlquote(request.GET.get('back'))
            if type_id in Visit.applicable_types:
                return redirect(reverse('visit-create') +
                                "?type=%d&back=%s" % (type_id, back))
            else:
                return redirect(reverse('otherresource-create') +
                                "?type=%d&back=%s" % (type_id, back))

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


class EditResourceView(HasBackButtonMixin, UpdateView):

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
                      u" koordinator for.")
                )
        return result

    forms = {}

    def get_form_class(self):
        if self.object.type in self.forms:
            return self.forms[self.object.type]
        return self.form_class

    def get_forms(self):
        if self.request.method == 'GET':
            return {
                'form': self.get_form(),
                'fileformset': ResourceStudyMaterialForm(None,
                                                         instance=self.object)
            }
        if self.request.method == 'POST':
            return {
                'form': self.get_form(),
                'fileformset': ResourceStudyMaterialForm(self.request.POST),
            }

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.set_object(pk, request)

        return self.render_to_response(
            self.get_context_data(**self.get_forms())
        )

    def set_object(self, pk, request, is_cloning=False):
        if is_cloning or not hasattr(self, 'object') or self.object is None:
            if pk is None:
                self.object = self.model()
                try:
                    type = int(request.GET['type'])
                    if type in self.model.applicable_types:
                        self.object.type = type
                except:
                    pass
            else:
                try:
                    self.object = self.model.objects.get(id=pk)
                    if is_cloning:
                        self.object.pk = None
                        self.object.id = None
                except ObjectDoesNotExist:
                    raise Http404

    def get_context_data(self, **kwargs):
        context = {}

        context['gymnasiefag_choices'] = Subject.gymnasiefag_qs()
        context['grundskolefag_choices'] = Subject.grundskolefag_qs()
        context['gymnasie_level_choices'] = \
            GymnasieLevel.objects.all().order_by('level')

        context['gymnasiefag_selected'] = self.gymnasiefag_selected()
        context['grundskolefag_selected'] = self.grundskolefag_selected()

        context['klassetrin_range'] = range(1, 10)

        if self.object and self.object.id:
            context['thisurl'] = reverse('resource-edit',
                                         args=[self.object.id])
        else:
            context['thisurl'] = reverse('resource-create')

        # context['oncancel'] = self.request.GET.get('back')

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

    def save_studymaterials(self):
        fileformset = ResourceStudyMaterialForm(self.request.POST)
        if fileformset.is_valid():
            # Attach uploaded files
            for fileform in fileformset:
                try:
                    instance = StudyMaterial(
                        resource=self.object,
                        file=self.request.FILES["%s-file" % fileform.prefix]
                    )
                    instance.save()
                except:
                    pass

    def save_subjects(self):
        existing_gym_fag = {}
        for x in self.object.resourcegymnasiefag_set.all():
            existing_gym_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('gymnasiefag', []):
            if gval in existing_gym_fag:
                del existing_gym_fag[gval]
            else:
                ResourceGymnasieFag.create_from_submitvalue(self.object, gval)

        # Delete any remaining values that were not submitted
        for x in existing_gym_fag.itervalues():
            x.delete()

        existing_gs_fag = {}
        for x in self.object.resourcegrundskolefag_set.all():
            existing_gs_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('grundskolefag', []):
            if gval in existing_gs_fag:
                del existing_gs_fag[gval]
            else:
                ResourceGrundskoleFag.create_from_submitvalue(
                    self.object, gval
                )

        # Delete any remaining values that were not submitted
        for x in existing_gs_fag.itervalues():
            x.delete()


class EditOtherResourceView(EditResourceView):

    template_name = 'otherresource/form.html'
    form_class = OtherResourceForm
    model = OtherResource

    forms = {
        Resource.STUDIEPRAKTIK: InternshipForm,
        Resource.OPEN_HOUSE: OpenHouseForm,
        Resource.STUDY_PROJECT: StudyProjectForm,
        Resource.ASSIGNMENT_HELP: AssignmentHelpForm,
        Resource.STUDY_MATERIAL: StudyMaterialForm
    }

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = EDIT_ROLES

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        is_cloning = kwargs.get("clone", False)
        self.set_object(pk, request, is_cloning)
        forms = self.get_forms()

        if forms['form'].is_valid():
            self.object = forms['form'].save()

            self.save_studymaterials()

            self.save_subjects()

            return super(EditOtherResourceView, self).form_valid(forms['form'])
        else:
            return self.form_invalid(forms['form'])

    def get_success_url(self):
        try:
            return reverse('otherresource-view', args=[self.object.id])
        except:
            return '/'

    def get_context_data(self, **kwargs):
        context = {}
        if self.object is not None and self.object.id:
            context['thisurl'] = reverse('otherresource-edit',
                                         args=[self.object.id])
        else:
            context['thisurl'] = reverse('otherresource-create')
        context.update(kwargs)
        return super(EditOtherResourceView, self).get_context_data(**context)


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
             'text': _(u'Søgeresultat')},
            {'text': _(u'Om tilbuddet')},
        ]

        context['thisurl'] = reverse('otherresource-view',
                                     args=[self.object.id])

        context.update(kwargs)

        return super(OtherResourceDetailView, self).get_context_data(**context)


class EditVisitView(RoleRequiredMixin, EditResourceView):

    template_name = 'visit/form.html'
    form_class = VisitForm
    model = Visit

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = EDIT_ROLES

    forms = {
        Resource.STUDENT_FOR_A_DAY: StudentForADayForm,
        Resource.TEACHER_EVENT: TeacherVisitForm,
        Resource.GROUP_VISIT: ClassVisitForm,
        Resource.STUDIEPRAKTIK: InternshipForm,
        Resource.OPEN_HOUSE: OpenHouseForm,
        Resource.STUDY_PROJECT: StudyProjectForm,
        Resource.ASSIGNMENT_HELP: AssignmentHelpForm,
        Resource.STUDY_MATERIAL: StudyMaterialForm
    }

    def get_forms(self):
        forms = super(EditVisitView, self).get_forms()
        if self.request.method == 'GET':
            forms['autosendformset'] = VisitAutosendFormSet(
                None, instance=self.object
            )
        if self.request.method == 'POST':
            forms['autosendformset'] = VisitAutosendFormSet(
                self.request.POST, instance=self.object
            )
        return forms

    def _is_any_booking_outside_new_attendee_count_bounds(
            self,
            visit_id,
            min=0,
            max=0
    ):
        if min is None or min == '':
            min = 0
        if max is None or max == '':
            max = 1000
        """
        Check if any existing bookings exists with attendee count outside
        the new min-/max_attendee_count bounds.
        :param visit_id:
        :param min:
        :param max:
        :return: Boolean
        """
        if min == u'':
            min = 0
        if max == u'':
            max = 0

        existing_bookings_outside_bounds = Booker.objects.filter(
            booking__visitoccurrence__visit__pk=visit_id
        ).exclude(
            attendee_count__gte=min,
            attendee_count__lte=max
        )
        return existing_bookings_outside_bounds.exists()

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            if self._is_any_booking_outside_new_attendee_count_bounds(
                pk,
                request.POST.get(u'minimum_number_of_visitors'),
                request.POST.get(u'maximum_number_of_visitors'),
            ):
                messages.add_message(
                    request,
                    messages.INFO,
                    _(u'Der findes arrangementer for tilbudet med '
                      u'deltagerantal udenfor de angivne min-/max-grænser for '
                      u'deltagere!')
                )
        is_cloning = kwargs.get("clone", False)
        self.set_object(pk, request, is_cloning)
        forms = self.get_forms()

        if forms['form'].is_valid():
            self.object = forms['form'].save()

            self.save_autosend()

            self.save_studymaterials()

            self.save_rooms()

            self.save_occurrences()

            self.save_subjects()

            return super(EditVisitView, self).form_valid(forms['form'])
        else:
            return self.form_invalid(forms)

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

        context['klassetrin_range'] = range(1, 10)

        if self.object is not None and self.object.id:
            context['thisurl'] = reverse('visit-edit', args=[self.object.id])
        else:
            context['thisurl'] = reverse('visit-create')

        context['template_keys'] = list(
            set(
                template.key
                for template in EmailTemplate.get_templates(self.object.unit)
            )
        )
        context['unit'] = self.object.unit

        context['hastime'] = self.object.type in [
            Resource.STUDENT_FOR_A_DAY, Resource.STUDIEPRAKTIK,
            Resource.OPEN_HOUSE, Resource.TEACHER_EVENT, Resource.GROUP_VISIT,
            Resource.STUDY_PROJECT
        ]

        context.update(kwargs)

        return super(EditVisitView, self).get_context_data(**context)

    def save_autosend(self):
        autosendformset = VisitAutosendFormSet(
            self.request.POST, instance=self.object
        )
        if autosendformset.is_valid():
            # Update autosend
            for autosendform in autosendformset:
                if autosendform.is_valid():
                    try:
                        autosendform.save()
                    except:
                        pass

    def save_rooms(self):
        # Update rooms
        existing_rooms = set([x.name for x in self.object.room_set.all()])

        new_rooms = self.request.POST.getlist("rooms")
        for roomname in new_rooms:
            if roomname in existing_rooms:
                existing_rooms.remove(roomname)
            else:
                new_room = Room(visit=self.object, name=roomname)
                new_room.save()

        # Delete any rooms left in existing rooms
        if len(existing_rooms) > 0:
            self.object.room_set.all().filter(
                name__in=existing_rooms
            ).delete()

    def save_occurrences(self):
        # update occurrences
        existing_visit_occurrences = \
            set([x.start_datetime
                 for x in self.object.bookable_occurrences])

        # convert date strings to datetimes
        dates = self.request.POST.get(u'occurrences').split(',')

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
                instance = self.object.make_occurrence(date_t, True)
                instance.save()
        # If the set of existing occurrences still is not empty,
        # it means that the user un-ticket one or more existing.
        # So, we remove those to...
        if len(existing_visit_occurrences) > 0:
            self.object.bookable_occurrences.filter(
                start_datetime__in=existing_visit_occurrences
            ).delete()

    def get_success_url(self):
        try:
            return reverse('visit-view', args=[self.object.id])
        except:
            return '/'

    def form_invalid(self, forms):
        return self.render_to_response(
            self.get_context_data(**forms)
        )

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(EditVisitView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else Visit.objects.get(id=pk)
        if self.object is not None and self.object.unit:
            if not current_user.userprofile.can_edit(self.object):
                raise AccessDenied(
                    _(u"Du kan kun redigere enheder, som du selv er" +
                      u" koordinator for.")
                )
        return result

    def get_form_kwargs(self):
        kwargs = super(EditVisitView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


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
                                Resource.GROUP_VISIT,
                                Resource.TEACHER_EVENT]:
            context['can_book'] = True
        else:
            context['can_book'] = False

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': self.request.GET.get("search", reverse('search')),
             'text': _(u'Søgeresultat')},
            {'text': _(u'Om tilbuddet')},
        ]

        context['thisurl'] = reverse('visit-view', args=[self.object.id])

        context['EmailTemplate'] = EmailTemplate

        context.update(kwargs)

        return super(VisitDetailView, self).get_context_data(**context)


class VisitOccurrenceNotifyView(EmailComposeView):

    def dispatch(self, request, *args, **kwargs):
        self.recipients = []
        pk = kwargs['pk']
        self.object = VisitOccurrence.objects.get(id=pk)

        self.template_context['visit'] = self.object.visit
        return super(VisitOccurrenceNotifyView, self).\
            dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        visitoccurrence = self.object
        visit = visitoccurrence.visit
        unit = visit.unit
        context = {}
        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': reverse('search'), 'text': _(u'Søgeresultat')},
            {'url': reverse('visit-occ-view', args=[visitoccurrence.id]),
             'text': _(u'Om tilbuddet')},
            {'text': _(u'Send notifikation')},
        ]
        context['recp'] = {
            'guests': {
                'label': _(u'Gæster'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_BOOKER,
                                self.RECIPIENT_SEPARATOR,
                                booking.booker.id):
                    booking.booker.get_full_email()
                    for booking in visitoccurrence.bookings.all()
                }
            },
            'contacts': {
                'label': _(u'Kontaktpersoner'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_PERSON,
                                self.RECIPIENT_SEPARATOR,
                                person.id):
                    person.get_full_email()
                    for person in visit.contact_persons.all()
                }
            },
            'assigned_hosts': {
                'label': _(u'Tildelte værter'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in visitoccurrence.hosts.all()
                    if user.email is not None
                }
            },
            'assigned_teachers': {
                'label': _(u'Tildelte undervisere'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in visitoccurrence.teachers.all()
                    if user.email is not None
                }
            },
            'potential_hosts': {
                'label': _(u'Potentielle værter'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in unit.get_hosts()
                    if user.email is not None
                }
            },
            'potential_teachers': {
                'label': _(u'Potentielle undervisere'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in unit.get_teachers()
                    if user.email is not None
                }
            }
        }
        context.update(kwargs)
        return super(VisitOccurrenceNotifyView, self).\
            get_context_data(**context)

    def get_unit(self):
        return self.object.visit.unit

    def get_success_url(self):
        if self.modal:
            return reverse('visit-occ-notify-success', args=[self.object.id])
        else:
            return reverse('visit-occ-view', args=[self.object.id])


class BookingNotifyView(EmailComposeView):

    def dispatch(self, request, *args, **kwargs):
        self.recipients = []
        pk = kwargs['pk']
        self.object = Booking.objects.get(id=pk)

        self.template_context['visit'] = self.object.visitoccurrence.visit
        return super(BookingNotifyView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': reverse('search'), 'text': _(u'Søgeresultat')},
            {'url': reverse('booking-view', args=[self.object.id]),
             'text': _(u'Detaljevisning')},
            {'text': _(u'Send notifikation')},
        ]
        context['recp'] = {
            'guests': {
                'label': _(u'Gæster'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_BOOKER,
                                self.RECIPIENT_SEPARATOR,
                                self.object.booker.id):
                    self.object.booker.get_full_email()
                }
            },
            'contacts': {
                'label': _(u'Kontaktpersoner'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_PERSON,
                                self.RECIPIENT_SEPARATOR, person.id):
                                    person.get_full_email()
                    for person in self.object.visit.contact_persons.all()
                }
            },
            'hosts': {
                'label': _(u'Værter'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                    full_email(user.email, user.get_full_name())
                    for user in self.object.hosts.all()
                    if user.email is not None
                    }
            },
            'teachers': {
                'label': _(u'Undervisere'),
                'items': {
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                    full_email(user.email, user.get_full_name())
                    for user in self.object.teachers.all()
                    if user.email is not None
                    }
            }
        }

        context.update(kwargs)
        return super(BookingNotifyView, self).get_context_data(**context)

    def get_unit(self):
        return self.object.visitoccurrence.visit.unit

    def get_success_url(self):
        if self.modal:
            return reverse('booking-notify-success', args=[self.object.id])
        else:
            return reverse('booking-view', args=[self.object.id])


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
        type = request.GET.get('t')
        items = School.search(query, type)
        json = {'schools':
                [
                    {'name': item.name,
                     'postcode': item.postcode.number
                     if item.postcode is not None else None,
                     'type': item.type}
                    for item in items
                ]
                }
        return JsonResponse(json)


class BookingView(AutologgerMixin, UpdateView):
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

        data = {
            'visit': self.visit,
            'level_map': Booker.level_map
        }

        self.object = Booking()
        data.update(self.get_forms())
        return self.render_to_response(
            self.get_context_data(**data)
        )

    def post(self, request, *args, **kwargs):
        self.set_visit(kwargs.get("visit"))
        if self.visit is None:
            return bad_request(request)

        data = {
            'visit': self.visit,
            'level_map': Booker.level_map
        }

        self.object = Booking()

        self._old_state = self._as_state()

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

            if not booking.visitoccurrence:
                # Make an anonymous visitoccurrence
                occ = self.visit.make_occurrence(
                    None, False
                )
                occ.save()
                booking.visitoccurrence = occ

            if 'bookerform' in forms:
                booking.booker = forms['bookerform'].save()

            booking.save()
            # Trigger updating of search index
            booking.visitoccurrence.save()

            booking.autosend(EmailTemplate.NOTIFY_GUEST__BOOKING_CREATED)

            booking.autosend(EmailTemplate.NOTIFY_HOST__BOOKING_CREATED)

            booking.autosend(EmailTemplate.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER)

            booking.autosend(EmailTemplate.NOTIFY_HOST__REQ_HOST_VOLUNTEER)

            # We can't fetch this form before we have
            # a saved booking object to feed it, or we'll get an error
            if hadSubjectForm:
                subjectform = BookingSubjectLevelForm(request.POST,
                                                      instance=booking)
                if subjectform.is_valid():
                    subjectform.save()

            self.object = booking
            self.model = booking.__class__

            self._log_changes()

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
            forms['bookerform'] = \
                BookerForm(data, visit=self.visit,
                           language=self.request.LANGUAGE_CODE)

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


class EmbedcodesView(TemplateView):
    template_name = "embedcodes.html"

    def get_context_data(self, **kwargs):
        context = {}

        embed_url = 'embed/' + kwargs['embed_url']

        # We only want to test the part before ? (or its encoded value, %3F):
        test_url = embed_url.split('?', 1)[0]
        test_url = test_url.split('%3F', 1)[0]

        can_embed = False

        for x in urls.embedpatterns:
            if x.regex.match(test_url):
                can_embed = True
                break

        context['can_embed'] = can_embed
        context['full_url'] = self.request.build_absolute_uri('/' + embed_url)

        context['breadcrumbs'] = [
            {
                'url': '/embedcodes/',
                'text': 'Indlering af side'
            },
            {
                'url': self.request.path,
                'text': '/' + kwargs['embed_url']
            }
        ]

        context.update(kwargs)

        return super(EmbedcodesView, self).get_context_data(**context)


class VisitOccurrenceSearchView(LoginRequiredMixin, ListView):
    model = VisitOccurrence
    template_name = "booking/searchresult.html"
    context_object_name = "results"
    paginate_by = 10

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

    def get_queryset(self):
        searchexpression = self.request.GET.get("q", "")

        # Filter by searchexpression
        qs = self.model.objects.search(searchexpression)

        # Filter by user access
        qs = Booking.queryset_for_user(self.request.user, qs)

        qs = qs.order_by("-pk")

        return qs

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

        if self.request.user.userprofile.is_administrator:
            context['unit_limit_text'] = \
                u'Alle enheder (administrator-søgning)'
        else:
            context['unit_limit_text'] = \
                u'Bookinger relateret til enheden %s' % (
                    self.request.user.userprofile.unit
                )

        context['breadcrumbs'] = [
            {
                'url': reverse('visit-occ-search'),
                'text': _(u'Arrangementer')
            },
            {'text': _(u'Søgeresultatliste')},
        ]

        context.update(kwargs)

        return super(VisitOccurrenceSearchView, self).get_context_data(
            **context
        )

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)

        if size == "all":
            return None

        return size


class BookingDetailView(LoggedViewMixin, DetailView):
    """Display Booking details"""
    model = Booking
    template_name = 'booking/details.html'

    def get_context_data(self, **kwargs):
        context = {}

        context['breadcrumbs'] = [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {'url': '#', 'text': _(u'Søgeresultatliste')},
            {'text': _(u'Detaljevisning')},
        ]

        context['thisurl'] = reverse('booking-view', args=[self.object.id])
        context['modal'] = BookingNotifyView.modal

        user = self.request.user
        if hasattr(user, 'userprofile') and \
                user.userprofile.can_notify(self.object):
            context['can_notify'] = True

        context['emailtemplates'] = [
            (key, label)
            for (key, label) in EmailTemplate.key_choices
            if key in EmailTemplate.booking_manual_keys
        ]

        context.update(kwargs)

        return super(BookingDetailView, self).get_context_data(**context)


class VisitOccurrenceDetailView(LoggedViewMixin, DetailView):
    """Display Booking details"""
    model = VisitOccurrence
    template_name = 'visitoccurrence/details.html'

    def get_context_data(self, **kwargs):
        context = {}

        context['breadcrumbs'] = [
            {
                'url': reverse('visit-occ-search'),
                'text': _(u'Søg i arrangementer')
            },
            {'text': _(u'Arrangement #%s') % self.object.pk},
        ]

        context['thisurl'] = reverse('visit-occ-view', args=[self.object.id])
        context['modal'] = VisitOccurrenceNotifyView.modal

        context['emailtemplates'] = [
            (key, label)
            for (key, label) in EmailTemplate.key_choices
            if key in EmailTemplate.visitoccurrence_manual_keys
        ]

        context['can_edit'] = self.request.user.userprofile.can_edit(
            self.object
        )

        user = self.request.user
        if hasattr(user, 'userprofile') and \
                user.userprofile.can_notify(self.object):
            context['can_notify'] = True

        context.update(kwargs)

        return super(VisitOccurrenceDetailView, self).get_context_data(
            **context
        )


class EmailTemplateListView(ListView):
    template_name = 'email/list.html'
    model = EmailTemplate

    def get_context_data(self, **kwargs):
        context = {}
        context['duplicates'] = []
        for i in xrange(0, len(self.object_list)):
            objectA = self.object_list[i]
            for j in xrange(i, len(self.object_list)):
                objectB = self.object_list[j]
                if objectA != objectB \
                        and objectA.key == objectB.key \
                        and objectA.unit == objectB.unit:
                    context['duplicates'].extend([objectA, objectB])
        context['breadcrumbs'] = [
            {'text': _(u'Emailskabelonliste')},
        ]
        context['thisurl'] = reverse('emailtemplate-list')
        context.update(kwargs)
        return super(EmailTemplateListView, self).get_context_data(**context)

    def get_queryset(self):
        qs = super(EmailTemplateListView, self).get_queryset()
        qs = [item
              for item in qs
              if self.request.user.userprofile.can_edit(item)]
        return qs


class EmailTemplateEditView(UpdateView, UnitAccessRequiredMixin,
                            HasBackButtonMixin):
    template_name = 'email/form.html'
    form_class = EmailTemplateForm
    model = EmailTemplate

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is None:
            self.object = EmailTemplate()
        else:
            self.object = EmailTemplate.objects.get(pk=pk)
            self.check_item(self.object)
        form = self.get_form()
        if 'key' in request.GET:
            form.initial['key'] = request.GET['key']
        if 'unit' in request.GET:
            form.initial['unit'] = request.GET['unit']
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def post(self, request, *args, **kwargs):

        pk = kwargs.get("pk")
        is_cloning = kwargs.get("clone", False)

        if pk is None or is_cloning:
            self.object = EmailTemplate()
        else:
            self.object = EmailTemplate.objects.get(pk=pk)
            self.check_item(self.object)

        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            self.object = form.save()
            return redirect(reverse('emailtemplate-list'))

        return self.render_to_response(
            self.get_context_data(**context)
        )

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {'url': reverse('emailtemplate-list'),
             'text': _(u'Emailskabelonliste')}]
        if self.object and self.object.id:
            context['breadcrumbs'].extend([
                {'url': reverse('emailtemplate-view', args={self.object.id}),
                 'text': _(u'Emailskabelon')},
                {'text': _(u'Redigér')},
            ])
        else:
            context['breadcrumbs'].append({'text': _(u'Opret')})

        if self.object is not None and self.object.id is not None:
            context['thisurl'] = reverse('emailtemplate-edit',
                                         args=[self.object.id])
        else:
            context['thisurl'] = reverse('emailtemplate-create')

        context.update(kwargs)
        return super(EmailTemplateEditView, self).get_context_data(**context)

    def get_form_kwargs(self):
        args = super(EmailTemplateEditView, self).get_form_kwargs()
        args['user'] = self.request.user
        return args


class EmailTemplateDetailView(View):
    template_name = 'email/preview.html'

    classes = {'Unit': Unit,
               # 'OtherResource': OtherResource,
               'Visit': Visit,
               # 'VisitOccurrence': VisitOccurrence,
               # 'StudyMaterial': StudyMaterial,
               # 'Resource': Resource,
               # 'Subject': Subject,
               # 'GymnasieLevel': GymnasieLevel,
               # 'Room': Room,
               # 'PostCode': PostCode,
               # 'School': School,
               'Booking': Booking,
               # 'ResourceGymnasieFag': ResourceGymnasieFag,
               # 'ResourceGrundskoleFag': ResourceGrundskoleFag
               }

    @staticmethod
    def _getObjectJson():
        return json.dumps({
            key: [
                {'text': unicode(object), 'value': object.id}
                for object in type.objects.all()
            ]
            for key, type in EmailTemplateDetailView.classes.items()
        })

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        formset = EmailTemplatePreviewContextForm()
        self.object = EmailTemplate.objects.get(pk=pk)

        context = {}
        if self.object is not None:
            variables = self.object.get_template_variables()
            formset.initial = []
            for variable in variables:
                base_variable = variable.split(".")[0]
                if base_variable not in context:
                    type = base_variable.title()
                    if type in self.classes.keys():
                        clazz = self.classes[type]
                        try:
                            value = clazz.objects.all()[0]
                            context[base_variable] = value
                            formset.initial.append({
                                'key': base_variable,
                                'type': type,
                                'value': value.id
                            })
                        except clazz.DoesNotExist:
                            pass

        data = {'form': formset,
                'subject': self.object.expand_subject(context, True),
                'body': self.object.expand_body(context, True),
                'objects': self._getObjectJson(),
                'template': self.object
                }

        data.update(self.get_context_data())
        return render(request, self.template_name, data)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        formset = EmailTemplatePreviewContextForm(request.POST)
        self.object = EmailTemplate.objects.get(pk=pk)

        context = {}
        formset.full_clean()

        for form in formset:
            if form.is_valid():
                type = form.cleaned_data['type']
                value = form.cleaned_data['value']
                if type in self.classes.keys():
                    clazz = self.classes[type]
                    try:
                        value = clazz.objects.get(pk=value)
                    except clazz.DoesNotExist:
                        pass
                context[form.cleaned_data['key']] = value

        data = {'form': formset,
                'subject': self.object.expand_subject(context, True),
                'body': self.object.expand_body(context, True),
                'objects': self._getObjectJson(),
                'template': self.object
                }
        data.update(self.get_context_data())

        return render(request, self.template_name, data)

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {'url': reverse('emailtemplate-list'),
             'text': _(u'Emailskabelonliste')},
            {'text': _(u'Emailskabelon')},
        ]
        context['thisurl'] = reverse('emailtemplate-view',
                                     args=[self.object.id])
        return context


class EmailTemplateDeleteView(HasBackButtonMixin, DeleteView):
    template_name = 'email/delete.html'
    model = EmailTemplate
    success_url = reverse_lazy('emailtemplate-list')

    def get_context_data(self, **kwargs):
        context = super(EmailTemplateDeleteView, self). \
            get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'url': reverse('emailtemplate-list'),
             'text': _(u'Emailskabelonliste')},
            {'url': reverse('emailtemplate-view', args={self.object.id}),
             'text': _(u'Emailskabelon')},
            {'text': _(u'Slet')},
        ]
        return context


import booking_workflows.views  # noqa
import_views(booking_workflows.views)
