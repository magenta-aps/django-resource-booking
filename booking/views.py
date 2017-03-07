# -*- coding: utf-8 -*-

import json
import urllib

from datetime import datetime, timedelta

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
from django.db.models import Sum
from django.db.models.functions import Coalesce
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
from django.views.generic.edit import CreateView, UpdateView, DeleteView, \
from django.views.generic.edit import FormMixin, ModelFormMixin
from django.views.generic.edit import FormView, ProcessFormView
from django.views.defaults import bad_request

from profile.models import EDIT_ROLES
from profile.models import role_to_text
from booking.models import Product, Visit, StudyMaterial
from booking.models import KUEmailMessage
from booking.models import Subject
from booking.models import OrganizationalUnit
from booking.models import GymnasieLevel
from booking.models import Room
from booking.models import PostCode, School
from booking.models import Booking, Guest
from booking.models import ProductGymnasieFag, ProductGrundskoleFag
from booking.models import EmailTemplateType, EmailTemplate
from booking.models import log_action
from booking.models import LOGACTION_CREATE, LOGACTION_CHANGE
from booking.models import RoomResponsible
from booking.models import BookerResponseNonce

from booking.models import MultiProductVisit
from booking.models import MultiProductVisitTemp

from booking.forms import ProductInitialForm, ProductForm
from booking.forms import GuestEmailComposeForm, StudentForADayBookingForm
from booking.forms import OtherProductForm, StudyProjectBookingForm
from booking.forms import BookingGrundskoleSubjectLevelForm, BookingListForm
from booking.forms import StudentForADayForm, InternshipForm, OpenHouseForm
from booking.forms import TeacherProductForm, ClassProductForm
from booking.forms import StudyProjectForm, AssignmentHelpForm
from booking.forms import StudyMaterialForm

from booking.forms import BookingForm
from booking.forms import ClassBookingForm, TeacherBookingForm
from booking.forms import ProductStudyMaterialForm, \
    BookingGymnasieSubjectLevelForm
from booking.forms import BookerForm
from booking.forms import EmailTemplateForm, EmailTemplatePreviewContextForm
from booking.forms import EmailComposeForm
from booking.forms import EmailReplyForm
from booking.forms import EvaluationOverviewForm
from booking.forms import AdminProductSearchForm
from booking.forms import ProductAutosendFormSet
from booking.forms import VisitSearchForm
from booking.forms import AcceptBookingForm
from booking.forms import MultiProductVisitTempDateForm
from booking.forms import MultiProductVisitTempProductsForm

from booking.utils import full_email, get_model_field_map
from booking.utils import get_related_content_types, merge_dicts


import booking.models as booking_models
import re
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

    HEADING_RED = 'alert-danger'
    HEADING_GREEN = 'alert-success'
    HEADING_BLUE = 'alert-info'
    HEADING_YELLOW = 'alert-warning'

    template_name = 'frontpage.html'

    def get_context_data(self, **kwargs):
        context = {
            'lists': [
                {
                    'color': self.HEADING_GREEN,
                    'type': 'Product',
                    'title': _(u'Senest opdaterede tilbud'),
                    'queryset': Product.get_latest_updated(self.request.user),
                    'limit': 10,
                    'button': {
                        'text': _(u'Vis alle'),
                        'link': reverse('product-customlist') + "?type=%s" %
                        ProductCustomListView.TYPE_LATEST_UPDATED
                    }
                }, {
                    'color': self.HEADING_BLUE,
                    'type': 'Product',
                    'title': _(u'Senest bookede tilbud'),
                    'queryset': Product.get_latest_booked(self.request.user),
                    'limit': 10,
                    'button': {
                        'text': _(u'Vis alle'),
                        'link': reverse('product-customlist') + "?type=%s" %
                        ProductCustomListView.TYPE_LATEST_BOOKED
                    }
                }
            ]
        }
        for list in context['lists']:
            if len(list['queryset']) > 10:
                list['limited_qs'] = list['queryset'][:10]

        context.update(kwargs)
        return super(MainPageView, self).get_context_data(**context)


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


class BackMixin(ContextMixin):
    backparam = "back"
    just_preserve_back = False
    back_on_success = True
    back_on_cancel = True

    def redirect(self, regular):
        if self.backparam in self.request.GET:
            back = self.request.GET[self.backparam]
            if self.just_preserve_back:
                url = regular + ('?' if '?' not in regular else '&') + \
                    "back=%s" % back
            else:
                url = back
        else:
            url = regular
        return redirect(url)

    def get_success_url(self, regular=None):
        if self.back_on_success:
            if regular is None:
                regular = self.success_url
            if self.backparam in self.request.GET:
                back = self.request.GET[self.backparam]
                if self.just_preserve_back:
                    return regular + ('?' if '?' not in regular else '&') + \
                        "back=%s" % back
                else:
                    return back
            else:
                return regular
        elif hasattr(self, 'success_url') and self.success_url is not None:
            return self.success_url
        else:
            return super(BackMixin, self).get_success_url()

    def get_context_data(self, **kwargs):
        context = super(BackMixin, self).get_context_data(**kwargs)
        if self.back_on_cancel:
            context['oncancel'] = self.request.GET.get('back')
        return context


class ModalMixin(object):
    modalid = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.modalid = request.GET["modalid"]
        except:
            try:
                self.modalid = request.POST["modalid"]
            except:
                pass
        return super(ModalMixin, self).dispatch(request, *args, **kwargs)

    def get_hash(self):
        return "id=" + self.modalid if self.modalid is not None else ""

    def modalurl(self, url):
        url += ";" if "#" in url else "#"
        url += self.get_hash()
        return url


class ProductBookingDetailView(DetailView):

    def on_display(self):
        try:
            self.object.ensure_statistics()
        except:
            return
        self.object.statistics.on_display()

    def get(self, request, *args, **kwargs):
        response = super(ProductBookingDetailView, self).\
            get(request, *args, **kwargs)
        self.on_display()
        return response


class ProductBookingUpdateView(UpdateView):

    def on_update(self):
        try:
            self.object.ensure_statistics()
        except:
            return
        self.object.statistics.on_update()

    def form_valid(self, form):
        self.on_update()
        return super(ProductBookingUpdateView, self).form_valid(form)


class EmailComposeView(FormMixin, HasBackButtonMixin, TemplateView):
    template_name = 'email/compose.html'
    form_class = EmailComposeForm
    recipients = []
    template_type = None
    template_context = {}
    modal = True

    RECIPIENT_BOOKER = 'booker'
    RECIPIENT_USER = 'user'
    RECIPIENT_CUSTOM = 'custom'
    RECIPIENT_ROOMRESPONSIBLE = 'roomresponsible'
    RECIPIENT_SEPARATOR = ':'

    def get_template_type(self, request):
        try:  # see if there's a template key defined in the URL params
            self.template_type = EmailTemplateType.objects.get(
                id=int(request.GET.get("template", None))
            )
        except:
            pass

    def dispatch(self, request, *args, **kwargs):
        self.get_template_type(request)
        return super(EmailComposeView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        form.fields['recipients'].choices = self.recipients
        recipient_ids = request.GET.getlist("recipients", None)
        if recipient_ids is not None:
            # If the URL defines recipients, add them and set them as defaults
            form.fields['recipients'].choices = [
                self.encode_recipient(recipient)
                for recipient in self.lookup_recipients(recipient_ids)
            ]
            form.initial['recipients'] = [
                id
                for (id, label) in form.fields['recipients'].choices
            ]
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
            try:
                typeid = int(request.POST.get("template", None))
                template.type = EmailTemplateType.objects.get(id=typeid)
                template.key = template.type.key
            except (ValueError, TypeError):
                pass
            context = self.template_context
            recipients = self.lookup_recipients(
                form.cleaned_data['recipients']
            )
            KUEmailMessage.send_email(
                template, context, recipients, self.object
            )
            return super(EmailComposeView, self).form_valid(form)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_initial(self):
        initial = super(EmailComposeView, self).get_initial()
        if self.template_type is not None:
            template = \
                EmailTemplate.get_template(self.template_type, self.get_unit())
            if template is not None:
                initial['subject'] = template.subject
                initial['body'] = template.body
        initial['recipients'] = [id for (id, label) in self.recipients]
        return initial

    def get_context_data(self, **kwargs):
        context = {}
        print self.template_type
        print self.get_unit()
        context['templates'] = EmailTemplate.get_template(
            self.template_type, self.get_unit(), True
        )
        print context['templates']
        context['template_type'] = self.template_type.id
        context['template_unit'] = self.get_unit()
        context['modal'] = self.modal
        context.update(kwargs)
        return super(EmailComposeView, self).get_context_data(**context)

    @staticmethod
    def encode_recipient(recipient):
        recipient_type = None
        id = None
        email = None
        if isinstance(recipient, Booking):
            recipient = recipient.booker
        if isinstance(recipient, Guest):
            recipient_type = EmailComposeView.RECIPIENT_BOOKER
            id = recipient.id
            email = recipient.get_full_email()
        elif isinstance(recipient, User):
            recipient_type = EmailComposeView.RECIPIENT_USER
            id = recipient.username
            email = full_email(recipient.email, recipient.get_full_name())
        elif isinstance(recipient, RoomResponsible):
            recipient_type = EmailComposeView.RECIPIENT_ROOMRESPONSIBLE
            id = recipient.id
            email = full_email(recipient.email, recipient.get_full_name())
        key = recipient_type + EmailComposeView.RECIPIENT_SEPARATOR + str(id)
        return key, email

    @staticmethod
    def lookup_recipient(recipient_key):
        (recipient_type, id) = recipient_key.split(
            EmailComposeView.RECIPIENT_SEPARATOR, 1
        )
        if recipient_type == EmailComposeView.RECIPIENT_BOOKER:
            return Guest.objects.filter(id=id)
        elif recipient_type == EmailComposeView.RECIPIENT_USER:
            return User.objects.filter(username=id)
        elif recipient_type == EmailComposeView.RECIPIENT_CUSTOM:
            return id

    @staticmethod
    def lookup_recipients(recipient_ids):
        booker_ids = []
        user_ids = []
        roomresponsible_ids = []
        customs = []
        if type(recipient_ids) != list:
            recipient_ids = [recipient_ids]
        for value in recipient_ids:
            (recipient_type, id) = value.split(
                EmailComposeView.RECIPIENT_SEPARATOR, 1
            )
            if recipient_type == "booking":  # We allow booking ids for #13804
                try:
                    id = Booking.objects.get(id=id).booker.id
                    recipient_type = EmailComposeView.RECIPIENT_BOOKER
                except:
                    pass
            if recipient_type == EmailComposeView.RECIPIENT_BOOKER:
                booker_ids.append(id)
            elif recipient_type == EmailComposeView.RECIPIENT_USER:
                user_ids.append(id)
            elif recipient_type == EmailComposeView.RECIPIENT_CUSTOM:
                customs.append(id)
            elif recipient_type == EmailComposeView.RECIPIENT_ROOMRESPONSIBLE:
                roomresponsible_ids.append(id)

        return list(Guest.objects.filter(id__in=booker_ids)) + \
            list(User.objects.filter(username__in=user_ids)) + \
            list(RoomResponsible.objects.filter(
                id__in=roomresponsible_ids)
            ) + customs

    def get_unit(self):
        return self.request.user.userprofile.organizationalunit

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
        types = get_related_content_types(self.model)

        qs = LogEntry.objects.filter(
            object_id=self.object.pk,
            content_type__in=types
        ).order_by('-action_time')

        return qs

    def get_context_data(self, **kwargs):
        return super(LoggedViewMixin, self).get_context_data(
            log_entries=self.get_log_queryset(),
            **kwargs
        )


class BreadcrumbMixin(ContextMixin):

    def get_breadcrumbs(self):
        try:
            return self.build_breadcrumbs(*self.get_breadcrumb_args())
        except:
            return []

    def get_breadcrumb_args(self):
        return []

    def get_context_data(self, **kwargs):
        breadcrumbs = self.get_breadcrumbs()
        if len(breadcrumbs) > 0 and 'url' in breadcrumbs[-1]:
            del breadcrumbs[-1]['url']
        context = {'breadcrumbs': breadcrumbs}
        context.update(kwargs)
        return super(BreadcrumbMixin, self).get_context_data(**context)


class SearchView(BreadcrumbMixin, ListView):
    """Class for handling main search."""
    model = Product
    template_name = "product/searchresult.html"
    context_object_name = "results"
    paginate_by = 10
    base_queryset = None
    filters = None
    from_datetime = None
    to_datetime = None
    admin_form = None
    facet_queryset = None

    boolean_choice = (
        (1, _(u'Ja')),
        (0, _(u'Nej')),
    )

    def dispatch(self, request, *args, **kwargs):
        id_match_url = self.check_search_by_id()
        if id_match_url:
            return redirect(id_match_url)

        return super(SearchView, self).dispatch(request, *args, **kwargs)

    def check_search_by_id(self):
        # Check if we're searching for a given id
        if self.request.method.lower() != 'get':
            return None

        q = self.request.GET.get("q", "").strip()
        if re.match('^#?\d+$', q):
            if q[0] == "#":
                q = q[1:]
            try:
                res = Product.objects.get(pk=q)
                return reverse('product-view', args=[res.pk])
            except Product.DoesNotExist:
                pass
        return None

    def get_admin_form(self):
        if self.admin_form is None:
            if self.request.user.is_authenticated():
                self.admin_form = AdminProductSearchForm(
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

            date_cond = Q()

            t_from = self.get_date_from_request("from")
            t_to = self.get_date_from_request("to")

            is_public = not self.request.user.is_authenticated()

            if t_from:
                date_cond = date_cond & Q(eventtime__start__gt=t_from)

            if t_to:
                # End datetime is midnight of the next day
                next_midnight = t_to + timedelta(hours=24)
                date_cond = date_cond & Q(eventtime__start__lte=next_midnight)

            if is_public:
                # Public searches are always from todays date and onward
                if t_from is None:
                    t_from = timezone.now()
                    date_cond = date_cond & Q(eventtime__start__gt=t_from)

                # Public users only want to search within bookable dates
                ok_states = Visit.BOOKABLE_STATES
                in_bookable_state = (
                    Q(eventtime__bookable=True) &
                    Q(
                        Q(eventtime__visit__isnull=True) |
                        Q(eventtime__visit__workflow_status__in=ok_states)
                    )
                )

                res_controlled = Product.TIME_MODE_RESOURCE_CONTROLLED
                eventtime_cls = booking_models.EventTime
                nonblocked = eventtime_cls.NONBLOCKED_RESOURCE_STATES
                not_resource_blocked = (
                    (~Q(time_mode=res_controlled)) |
                    Q(
                        time_mode=res_controlled,
                        eventtime__resource_status__in=nonblocked
                    )
                )
                always_bookable = Q(
                    time_mode__in=[
                        Product.TIME_MODE_NONE,
                        Product.TIME_MODE_GUEST_SUGGESTED,
                    ]
                )
                qs = qs.filter(
                    (in_bookable_state & not_resource_blocked & date_cond) |
                    always_bookable
                )
            else:
                # Need this for search for products with/without bookings
                qs = qs.annotate(
                    num_bookings=Count('eventtime__visit__bookings')
                )
                qs = qs.filter(date_cond)

            self.from_datetime = t_from or ""
            self.to_datetime = t_to or ""

            qs = qs.distinct()

            self.base_queryset = qs

        return self.base_queryset

    def annotate(self, qs):
        qs = qs.annotate(
            eventtime_count=Count('eventtime__visit__pk', distinct=True),
            first_eventtime=Min('eventtime__start')
        )
        return qs

    def get_filters(self):
        if self.filters is None:
            self.filters = {}

            for filter_method in (
                self.filter_by_institution,
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
        self.filters["state__in"] = [Product.ACTIVE]

    def filter_by_institution(self):
        i = [x for x in self.request.GET.getlist("i")]
        if i:
            i.append(Subject.SUBJECT_TYPE_BOTH)
            self.filters["institution_level__in"] = i

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

    def filter_by_is_visit(self, form):
        v = form.cleaned_data.get("v", "")

        if v == "":
            return

        v = int(v)

        if v == AdminProductSearchForm.IS_VISIT:
            self.filters["time_mode__in"] = [
                x[0] for x in Product.time_mode_choices
                if x[0] != Product.TIME_MODE_NONE
            ]
        else:
            self.filters["time_mode"] = Product.TIME_MODE_NONE

    def filter_by_has_bookings(self, form):
        b = form.cleaned_data.get("b", "")

        if b == "":
            return

        b = int(b)

        if b == AdminProductSearchForm.HAS_BOOKINGS:
            self.filters["num_bookings__gt"] = 0
        elif b == AdminProductSearchForm.HAS_NO_BOOKINGS:
            self.filters["num_bookings"] = 0

    def filter_by_unit(self, form):
        u = form.cleaned_data.get("u", "")

        if u == "":
            return

        u = int(u)

        if u == AdminProductSearchForm.MY_UNIT:
            self.filters["organizationalunit"] = \
                self.request.user.userprofile.organizationalunit
        elif u == AdminProductSearchForm.MY_FACULTY:
            self.filters["organizationalunit"] = \
                self.request.user.userprofile\
                    .organizationalunit.get_faculty_queryset()
        elif u == AdminProductSearchForm.MY_UNITS:
            self.filters["organizationalunit"] = \
                self.user.userprofile.get_unit_queryset()
        else:
            self.filters["organizationalunit__pk"] = u

    def get_facet_queryset(self):
        if not self.facet_queryset:
            self.facet_queryset = Product.objects.filter(
                pk__in=[x.pk for x in self.get_base_queryset()]
            ).annotate(
                num_bookings=Count('eventtime__visit__bookings')
            )
        return self.facet_queryset

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

        facet_qs = Product.objects.filter(
            pk__in=self.get_facet_queryset().filter(**new_filters)
        )

        qs = facet_qs.values(facet_field).annotate(hits=Count("pk"))

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

        context["institution_choices"] = self.make_facet(
            "institution_level",
            self.model.institution_choices,
            self.request.GET.getlist("i"),
            add_to_all=[Subject.SUBJECT_TYPE_BOTH]
        )

        context["type_choices"] = self.make_facet(
            "type",
            self.model.resource_type_choices,
            self.request.GET.getlist("t"),
        )
        context['hiddenrepeats'] = []
        list = self.request.GET.getlist("i", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "i", 'value': x})
        list = self.request.GET.getlist("a", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "a", 'value': x})
        list = self.request.GET.getlist("t", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "t", 'value': x})
        list = self.request.GET.getlist("f", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "f", 'value': x})
        list = self.request.GET.getlist("from", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "from", 'value': x})
        list = self.request.GET.getlist("to", None)
        if list is not None:
            for x in list:
                context['hiddenrepeats'].append({'name': "to", 'value': x})
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

        querylist = []
        for key in ['q', 'page', 'pagesize', 't',
                    'a', 'i' 'f', 'g', 'from', 'to']:
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

        if (self.request.user.is_authenticated() and
                self.request.user.userprofile.has_edit_role()):

            context['has_edit_role'] = True

        context.update(kwargs)
        return super(SearchView, self).get_context_data(**context)

    @staticmethod
    def build_breadcrumbs(request=None):
        breadcrumbs = [
            {'url': reverse('search'), 'text': _(u'Søgning')}
        ]
        if request and 'search' in request.GET:
            breadcrumbs.append({
                'url': request.GET.get("search", reverse('search')),
                'text': _(u'Søgeresultat')
            })
        return breadcrumbs

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)

        if size == "all":
            return None

        return size


class ProductCustomListView(BreadcrumbMixin, ListView):

    TYPE_LATEST_BOOKED = "latest_booked"
    TYPE_LATEST_UPDATED = "latest_updated"

    template_name = "product/list.html"
    model = Product
    context_object_name = "results"
    paginate_by = 10

    def get_queryset(self):
        try:
            listtype = self.request.GET.get("type", "")

            if listtype == self.TYPE_LATEST_BOOKED:
                return Product.get_latest_booked(self.request.user)
            elif listtype == self.TYPE_LATEST_UPDATED:
                return Product.get_latest_updated(self.request.user)

        except:
            pass
        raise Http404

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

        context.update(kwargs)

        return super(ProductCustomListView, self).get_context_data(
            **context
        )

    @staticmethod
    def build_breadcrumbs():
        return [
            {'text': _(u'Tilbudsliste')}
        ]

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)

        if size == "all":
            return None

        return size


class EditProductInitialView(LoginRequiredMixin, HasBackButtonMixin,
                             BreadcrumbMixin, TemplateView):

    template_name = 'product/typeform.html'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            if Product.objects.filter(id=pk).count() > 0:
                return redirect(reverse('product-edit', args=[pk]))
            else:
                raise Http404
        else:
            form = ProductInitialForm()
            return self.render_to_response(
                self.get_context_data(form=form)
            )

    def post(self, request, *args, **kwargs):
        form = ProductInitialForm(request.POST)
        if form.is_valid():
            type_id = int(form.cleaned_data['type'])
            back = urlquote(request.GET.get('back'))
            if type_id in Product.applicable_types:
                return redirect(
                    reverse('product-create-type', args=[type_id]) +
                    "?back=%s" % back
                )

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    @staticmethod
    def build_breadcrumbs():
        return [
            {'text': _(u'Opret tilbud')}
        ]


class EditProductBaseView(LoginRequiredMixin, RoleRequiredMixin,
                          HasBackButtonMixin, ProductBookingUpdateView):
    is_creating = True

    def __init__(self, *args, **kwargs):
        super(EditProductBaseView, self).__init__(*args, **kwargs)
        self.object = None

    def get_form_kwargs(self):
        kwargs = super(EditProductBaseView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(EditProductBaseView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else self.model.objects.get(id=pk)
        if self.object is not None and self.object.organizationalunit:
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
                'fileformset': ProductStudyMaterialForm(None,
                                                        instance=self.object)
            }
        if self.request.method == 'POST':
            return {
                'form': self.get_form(),
                'fileformset': ProductStudyMaterialForm(self.request.POST),
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
                    type = int(self.kwargs['type'])
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

        if self.object.pk:
            self.is_creating = False
        else:
            self.is_creating = True
            self.object.created_by = self.request.user

    def get_context_data(self, **kwargs):
        context = {}

        context['gymnasiefag_choices'] = Subject.gymnasiefag_qs()
        context['grundskolefag_choices'] = Subject.grundskolefag_qs()
        context['gymnasie_level_choices'] = \
            GymnasieLevel.objects.all().order_by('level')

        context['gymnasiefag_selected'] = self.gymnasiefag_selected()
        context['grundskolefag_selected'] = self.grundskolefag_selected()

        context['klassetrin_range'] = range(0, 10)

        # context['oncancel'] = self.request.GET.get('back')

        context.update(kwargs)

        return super(EditProductBaseView, self).get_context_data(**context)

    def gymnasiefag_selected(self):
        result = []
        obj = self.object
        if self.request.method == 'GET':
            if obj and obj.pk:
                for x in obj.productgymnasiefag_set.all():
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
                    'description': ProductGymnasieFag.display(
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
                for x in obj.productgrundskolefag_set.all():
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
                    'description': ProductGrundskoleFag.display(
                        subject, lv_min, lv_max
                    )
                })

        return result

    def save_studymaterials(self):
        fileformset = ProductStudyMaterialForm(self.request.POST)
        if fileformset.is_valid():
            # Attach uploaded files
            for fileform in fileformset:
                try:
                    instance = StudyMaterial(
                        product=self.object,
                        file=self.request.FILES["%s-file" % fileform.prefix]
                    )
                    instance.save()
                except:
                    pass

    def save_subjects(self):
        existing_gym_fag = {}
        for x in self.object.productgymnasiefag_set.all():
            existing_gym_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('gymnasiefag', []):
            if gval in existing_gym_fag:
                del existing_gym_fag[gval]
            else:
                ProductGymnasieFag.create_from_submitvalue(self.object, gval)

        # Delete any remaining values that were not submitted
        for x in existing_gym_fag.itervalues():
            x.delete()

        existing_gs_fag = {}
        for x in self.object.productgrundskolefag_set.all():
            existing_gs_fag[x.as_submitvalue()] = x

        for gval in self.request.POST.getlist('grundskolefag', []):
            if gval in existing_gs_fag:
                del existing_gs_fag[gval]
            else:
                ProductGrundskoleFag.create_from_submitvalue(
                    self.object, gval
                )

        # Delete any remaining values that were not submitted
        for x in existing_gs_fag.itervalues():
            x.delete()

    def add_to_my_resources(self):
        # Newly created objects should be added to the users list of
        # resources.
        if self.is_creating:
            self.request.user.userprofile.my_resources.add(self.object)


class EditProductView(BreadcrumbMixin, EditProductBaseView):

    template_name = 'product/form.html'
    form_class = ProductForm
    model = Product

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = EDIT_ROLES

    forms = {
        Product.STUDENT_FOR_A_DAY: StudentForADayForm,
        Product.TEACHER_EVENT: TeacherProductForm,
        Product.GROUP_VISIT: ClassProductForm,
        Product.STUDIEPRAKTIK: InternshipForm,
        Product.OPEN_HOUSE: OpenHouseForm,
        Product.STUDY_PROJECT: StudyProjectForm,
        Product.ASSIGNMENT_HELP: AssignmentHelpForm,
        Product.STUDY_MATERIAL: StudyMaterialForm,
        Product.OTHER_OFFERS: OtherProductForm
    }

    def get_forms(self):
        forms = super(EditProductView, self).get_forms()
        if self.request.method == 'GET':
            if self.object.is_type_bookable:
                initial = []
                if not self.object or not self.object.pk:
                    initial = [
                        {'template_type': type, 'enabled': True}
                        for type in EmailTemplateType.objects.filter(
                            is_default=True
                        )
                    ]
                forms['autosendformset'] = ProductAutosendFormSet(
                    None, instance=self.object, initial=initial
                )

        if self.request.method == 'POST':
            forms['autosendformset'] = ProductAutosendFormSet(
                self.request.POST, instance=self.object
            )
        return forms

    def _is_any_booking_outside_new_attendee_count_bounds(
            self,
            product_id,
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
        :param product_id:
        :param min:
        :param max:
        :return: Boolean
        """
        if min == u'':
            min = 0
        if max == u'':
            max = 0

        existing_bookings_outside_bounds = Guest.objects.filter(
            booking__visit__eventtime__product__pk=product_id
        ).exclude(
            attendee_count__gte=min,
            attendee_count__lte=max
        )
        return existing_bookings_outside_bounds.exists()

    def is_cloning(self):
        return self.kwargs.get("clone", False)

    # Handle both forms, creating a Product and a number of StudyMaterials
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
                    _(u'Der findes besøg for tilbudet med '
                      u'deltagerantal udenfor de angivne min-/max-grænser for '
                      u'deltagere!')
                )
        self.set_object(pk, request, self.is_cloning())
        forms = self.get_forms()

        if forms['form'].is_valid():
            self.object = forms['form'].save()

            self.object.ensure_statistics()

            self.save_autosend()

            self.save_studymaterials()

            self.save_subjects()

            self.add_to_my_resources()

            messages.add_message(
                request,
                messages.INFO,
                _(u'Tilbuddet blev gemt.')
            )
            return super(EditProductView, self).form_valid(forms['form'])
        else:
            return self.form_invalid(forms)

    def get_context_data(self, **kwargs):
        context = {}

        context['gymnasiefag_choices'] = Subject.gymnasiefag_qs()
        context['grundskolefag_choices'] = Subject.grundskolefag_qs()
        context['gymnasie_level_choices'] = \
            GymnasieLevel.objects.all().order_by('level')

        context['gymnasiefag_selected'] = self.gymnasiefag_selected()
        context['grundskolefag_selected'] = self.grundskolefag_selected()

        context['klassetrin_range'] = range(0, 10)

        context['template_keys'] = list(
            set(
                template.key
                for template in EmailTemplate.get_templates(
                    self.object.organizationalunit
                )
            )
        )
        context['organizationalunit'] = self.object.organizationalunit
        context['autosend_enable_days'] = EmailTemplateType.get_keys(
            enable_days=True
        )

        context['hastime'] = self.object.type in [
            Product.STUDENT_FOR_A_DAY, Product.STUDIEPRAKTIK,
            Product.OPEN_HOUSE, Product.TEACHER_EVENT, Product.GROUP_VISIT,
            Product.STUDY_PROJECT, Product.OTHER_OFFERS
        ]

        context['disable_waitinglist_on_timemode_values'] = [
            Product.TIME_MODE_GUEST_SUGGESTED
        ]

        context.update(kwargs)

        return super(EditProductView, self).get_context_data(**context)

    def get_breadcrumb_args(self):
        return [self.object, self.request, self.is_cloning()]

    @staticmethod
    def build_breadcrumbs(product, request=None, cloning=False):
        if product and product.pk:
            return ProductDetailView.build_breadcrumbs(product, request) + [
                {
                    'url': reverse(
                        'product-clone' if cloning else 'product-edit',
                        args=[product.pk]
                    ),
                    'text': _(u'Kopiér') if cloning else _(u'Redigér')
                }
            ]
        else:
            return [
                {'text': _(u'Opret tilbud')}
            ]

    def save_autosend(self):
        if self.object.is_type_bookable:
            autosendformset = ProductAutosendFormSet(
                self.request.POST, instance=self.object
            )
            if autosendformset.is_valid():
                autosendformset.save()

    def get_success_url(self):
        try:
            return reverse('product-view', args=[self.object.id])
        except:
            return '/'

    def form_invalid(self, forms):
        return self.render_to_response(
            self.get_context_data(**forms)
        )

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(EditProductView, self).dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else Product.objects.get(id=pk)
        if self.object is not None and self.object.organizationalunit:
            if not current_user.userprofile.can_edit(self.object):
                raise AccessDenied(
                    _(u"Du kan kun redigere enheder, som du selv er" +
                      u" koordinator for.")
                )
        return result

    def get_form_kwargs(self):
        kwargs = super(EditProductView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class SimpleRessourcesView(LoginRequiredMixin, BreadcrumbMixin,
                           RoleRequiredMixin, UpdateView):
    roles = EDIT_ROLES
    model = Product
    fields = [
        'locality',
        'potentielle_vaerter', 'potentielle_undervisere',
        'needed_hosts', 'needed_teachers', 'rooms_needed',
    ]
    template_name = 'product/simple_ressources.html'

    def get_form(self, form_class=None):
        form = super(SimpleRessourcesView, self).get_form(form_class)

        if 'potentielle_vaerter' in form.fields:
            qs = form.fields['potentielle_vaerter']._get_queryset()
            form.fields['potentielle_vaerter']._set_queryset(
                qs.filter(
                    userprofile__organizationalunit=self.object
                    .organizationalunit
                )
            )
            form.fields['potentielle_vaerter'].label_from_instance = \
                lambda obj: "%s (%s) <%s>" % (
                    obj.get_full_name(),
                    obj.username,
                    obj.email
                )

        if 'potentielle_undervisere' in form.fields:
            qs = form.fields['potentielle_undervisere']._get_queryset()
            form.fields['potentielle_undervisere']._set_queryset(
                qs.filter(userprofile__organizationalunit=self.object
                          .organizationalunit)
            )
            form.fields['potentielle_undervisere'].label_from_instance = \
                lambda obj: "%s (%s) <%s>" % (
                    obj.get_full_name(),
                    obj.username,
                    obj.email
                )

        if 'roomresponsible' in form.fields:
            qs = form.fields['roomresponsible']._get_queryset()
            form.fields['roomresponsible']._set_queryset(
                qs.filter(organizationalunit=self.object.organizationalunit)
            )
            form.fields['roomresponsible'].label_from_instance = \
                lambda obj: "%s <%s>" % (
                    obj.get_full_name(),
                    obj.email
                )

        return form

    def get_breadcrumb_args(self):
        return [self.object, self.request]

    @staticmethod
    def build_breadcrumbs(product, request=None):
        return ProductDetailView.build_breadcrumbs(product, request) + [
            {
                'url': reverse('product-simple-ressources', args=[
                    product.id
                ]),
                'text': _(u'Redigér ressourcer')
            }
        ]

    def form_valid(self, form):
        res = super(SimpleRessourcesView, self).form_valid(form)

        self.save_rooms()

        return res

    def save_rooms(self):
        # This code is more or less the same as
        # ChangeVisitRoomsView.save_rooms()
        # If you update this you might have to update there as well.
        existing_rooms = set([x.pk for x in self.object.rooms.all()])

        new_rooms = self.request.POST.getlist("rooms")

        for roomdata in new_rooms:
            if roomdata.startswith("id:"):
                # Existing rooms are identified by "id:<pk>"
                try:
                    room_pk = int(roomdata[3:])
                    if room_pk in existing_rooms:
                        existing_rooms.remove(room_pk)
                    else:
                        self.object.rooms.add(room_pk)
                except Exception as e:
                    print 'Problem adding room: %s' % e
            elif roomdata.startswith("new:"):
                # New rooms are identified by "new:<name-of-room>"
                room = self.object.add_room_by_name(roomdata[4:])
                if room.pk in existing_rooms:
                    existing_rooms.remove(room.pk)

        # Delete any rooms left in existing rooms
        for x in existing_rooms:
            self.object.rooms.remove(x)

    def get_context_data(self, **kwargs):
        context = {}

        if self.object and self.object.pk:
            context['rooms'] = self.object.rooms.all()
        else:
            context['rooms'] = []

        context['allrooms'] = [
            {
                'id': x.pk,
                'locality_id': x.locality.pk if x.locality else None,
                'name': x.name_with_locality
            }
            for x in Room.objects.all()
        ]
        context.update(kwargs)

        return super(SimpleRessourcesView, self).get_context_data(**context)


class ProductDetailView(BreadcrumbMixin, ProductBookingDetailView):
    """Display Product details"""
    model = Product
    template_name = 'product/details.html'

    def get(self, request, *args, **kwargs):
        return super(ProductDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """Get queryset, only include active products."""
        qs = super(ProductDetailView, self).get_queryset()
        # Dismiss products that are not active.
        if not self.request.user.is_authenticated():
            qs = qs.filter(state=Product.ACTIVE)
        return qs

    def get_context_data(self, **kwargs):
        context = {}

        user = self.request.user

        if hasattr(user, 'userprofile'):
            if user.userprofile.can_edit(self.object):
                context['can_edit'] = True
            if user.userprofile.can_create:
                context['nr_bookable'] = len(
                    self.object.future_bookable_times
                )
                context['nr_unbookable'] = len(
                    self.object.eventtime_set.all()
                ) - context['nr_bookable']
                context['nr_visits'] = len(
                    self.object.get_visits()
                )
        else:
            context['can_edit'] = False

        context['searchurl'] = self.request.GET.get(
            "search",
            reverse('search')
        )

        context['EmailTemplate'] = EmailTemplate

        context.update(kwargs)

        return super(ProductDetailView, self).get_context_data(**context)

    def get_breadcrumb_args(self):
        return [self.object, self.request]

    @staticmethod
    def build_breadcrumbs(product, request=None):
        return SearchView.build_breadcrumbs(request) + [
            {
                'text': unicode(product),
                'url': reverse('product-view', args=[product.pk])
            }
        ]


class ProductInquireView(FormMixin, HasBackButtonMixin, ModalMixin,
                         TemplateView):
    template_name = 'email/compose_modal.html'
    form_class = GuestEmailComposeForm
    modal = True

    def dispatch(self, request, *args, **kwargs):
        self.object = Product.objects.get(id=kwargs['product'])
        return super(ProductInquireView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            template = EmailTemplate.get_template(
                EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE,
                None
            )
            if template is None:
                raise Exception(_(u"There are no root templates with "
                                  u"the SYSTEM__BASICMAIL_ENVELOPE key"))
            context = {
                'product': self.object
            }
            context.update(form.cleaned_data)
            recipients = []
            if self.object.tilbudsansvarlig:
                recipients.append(self.object.tilbudsansvarlig)
            elif self.object.created_by:
                recipients.append(self.object.created_by)
            else:
                recipients.extend(self.object.organizationalunit.get_editors())
            KUEmailMessage.send_email(template, context, recipients,
                                      self.object)
            return super(ProductInquireView, self).form_valid(form)

        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def get_context_data(self, **kwargs):
        context = {}
        context['modal'] = self.modal
        context['object'] = self.object
        context.update(kwargs)
        return super(ProductInquireView, self).get_context_data(**context)

    def get_success_url(self):
        if self.modal:
            return self.modalurl(
                reverse('product-inquire-success', args=[self.object.id])
            )
        else:
            return reverse('product-view', args=[self.object.id])


class ProductInquireSuccessView(TemplateView):
    template_name = "email/inquire-success.html"


class VisitNotifyView(LoginRequiredMixin, ModalMixin, BreadcrumbMixin,
                      EmailComposeView):

    def dispatch(self, request, *args, **kwargs):
        self.recipients = []
        pk = kwargs['pk']
        self.object = Visit.objects.get(id=pk)
        self.get_template_type(request)
        # template_type = EmailTemplateType.get(self.template_key)
        # if self.object.is_multi_sub and \
        #         template_type.manual_sending_mpv_enabled:
        #     self.object = self.object.multi_master
        if self.object.is_multiproductvisit:
            self.object = self.object.multiproductvisit

        self.template_context['product'] = self.object.product
        self.template_context['visit'] = self.object
        self.template_context['besoeg'] = self.object
        self.template_context['web_user'] = self.request.user
        return super(VisitNotifyView, self).\
            dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        visit = self.object
        context = {}
        products = [self.object.product]
        if self.object.is_multiproductvisit:
            products = self.object.multiproductvisit.products
        context['recp'] = {
            'guests_accepted': {
                'label': _(u'Deltagende gæster'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_BOOKER,
                                self.RECIPIENT_SEPARATOR,
                                booking.booker.id):
                                    booking.booker.get_full_email()
                    for booking in visit.booking_list
                    }
            },
            'guests_waiting': {
                'label': _(u'Gæster på venteliste'),
                'items': {
                    "%s%s%d" % (self.RECIPIENT_BOOKER,
                                self.RECIPIENT_SEPARATOR,
                                booking.booker.id):
                                    booking.booker.get_full_email()
                    for booking in visit.waiting_list
                    }
            },
            'roomadmins': {
                'label': _(u'Lokaleansvarlige'),
                'items': merge_dicts(*[{
                    "%s%s%d" % (self.RECIPIENT_ROOMRESPONSIBLE,
                                self.RECIPIENT_SEPARATOR,
                                roomresponsible.id):
                                    roomresponsible.get_full_email()
                    for roomresponsible in product.roomresponsible.all()
                } for product in products])
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
                    for user in visit.assigned_hosts.all()
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
                    for user in visit.assigned_teachers.all()
                    if user.email is not None
                }
            },
            'potential_hosts': {
                'label': _(u'Potentielle værter'),
                'items': merge_dicts(*[{
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in product.potential_hosts.all()
                    if user.email is not None and
                    user not in visit.hosts_rejected.all() and
                    user not in visit.assigned_hosts.all()
                } for product in products])
            },
            'potential_teachers': {
                'label': _(u'Potentielle undervisere'),
                'items': merge_dicts(*[{
                    "%s%s%s" % (self.RECIPIENT_USER,
                                self.RECIPIENT_SEPARATOR,
                                user.username):
                                    full_email(
                                        user.email,
                                        user.get_full_name())
                    for user in product.potential_teachers.all()
                    if user.email is not None and
                    user not in visit.teachers_rejected.all() and
                    user not in visit.assigned_teachers.all()
                } for product in products])
            }
        }
        context.update(kwargs)
        return super(VisitNotifyView, self).\
            get_context_data(**context)

    def get_unit(self):
        return self.object.organizationalunit

    def get_success_url(self):
        if self.modal:
            return self.modalurl(
                reverse('visit-notify-success', args=[self.object.id])
            )
        else:
            return reverse('visit-view', args=[self.object.id])

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(visit):
        return VisitDetailView.build_breadcrumbs(visit) + [
            {'text': _(u'Send notifikation')}
        ]


class BookingNotifyView(LoginRequiredMixin, ModalMixin, BreadcrumbMixin,
                        EmailComposeView):

    def dispatch(self, request, *args, **kwargs):
        self.recipients = []
        pk = kwargs['pk']
        self.object = Booking.objects.get(id=pk)

        self.template_context['product'] = self.object.visit.product
        self.template_context['visit'] = self.object.visit
        self.template_context['besoeg'] = self.object.visit
        self.template_context['booking'] = self.object
        return super(BookingNotifyView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = {}
        products = [self.object.visit.product]
        if hasattr(self.object.visit, 'multiproductvisit'):
            products = self.object.visit.multiproductvisit.products
        if 'nogroups' not in self.request.GET:
            recipients = {
                'guests': {
                    'label': _(u'Gæster'),
                    'items': {
                        "%s%s%d" % (self.RECIPIENT_BOOKER,
                                    self.RECIPIENT_SEPARATOR,
                                    self.object.booker.id):
                        self.object.booker.get_full_email()
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
                },
                'tilbudsansvarlig': {
                    'label': _(u'Tilbudsansvarlig'),
                    'items': merge_dicts(*[{
                        "%s%s%d" % (self.RECIPIENT_USER,
                                    self.RECIPIENT_SEPARATOR, user.id):
                        full_email(user.email, user.get_full_name())
                        for user in [
                            product.tilbudsansvarlig
                        ] if user
                    } for product in products])
                },
                'roomadmins': {
                    'label': _(u'Lokaleansvarlige'),
                    'items': merge_dicts(*[{
                        "%s%s%d" % (self.RECIPIENT_USER,
                                    self.RECIPIENT_SEPARATOR,
                                    roomresponsible.id):
                                        roomresponsible.get_full_email()
                        for roomresponsible in product.roomresponsible.all()
                    } for product in products])
                }
            }
            context['recp'] = recipients

        context.update(kwargs)
        return super(BookingNotifyView, self).get_context_data(**context)

    def get_unit(self):
        return self.object.visit.organizationalunit

    def get_success_url(self):
        if self.modal:
            return self.modalurl(
                reverse('booking-notify-success', args=[self.object.id])
            )
        else:
            return reverse('booking-view', args=[self.object.id])

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(booking):
        return BookingDetailView.build_breadcrumbs(booking) + [
            {'text': _(u'Send notifikation')}
        ]


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
        product_id = None
        if request.POST[u'product_id'] != 'None':
            product_id = int(request.POST[u'product_id'])
        existing_dates_strings = set()

        if product_id is not None:
            product = Product.objects.get(pk=product_id)

            for visit in product.visit_set.all():
                for time in visit.eventtime_set.all():
                    existing_dates_strings.add(
                        time.start.strftime('%d-%m-%Y %H:%M')
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
        json = {
            'schools': [
                {
                    'name': item.name,
                    'postcode': {
                        'number': item.postcode.number,
                        'city': item.postcode.city
                    } if item.postcode is not None else None,
                    'type': item.type
                }
                for item in items
            ]
        }
        return JsonResponse(json)


class BookingView(AutologgerMixin, ModalMixin, ProductBookingUpdateView):
    product = None
    modal = True
    back = None

    def set_product(self, product_id):
        if product_id is not None:
            try:
                self.product = Product.objects.get(id=product_id)
            except:
                pass

    def get_context_data(self, **kwargs):
        available_times = {}
        if self.product and self.product.is_guest_time_suggested:
            only_waitinglist = False
        else:
            only_waitinglist = True
            for eventtime in self.product.future_times:
                if eventtime.available_seats > 0:
                    only_waitinglist = False
                available_times[str(eventtime.pk)] = {
                    'available': eventtime.available_seats,
                    'waitinglist': eventtime.waiting_list_capacity
                }

        context = {
            'product': self.product,
            'level_map': Guest.level_map,
            'modal': self.modal,
            'back': self.back,
            'times_available': available_times,
            'only_waitinglist': only_waitinglist,
            'gymnasiefag_available': self.gymnasiefag_available(),
            'grundskolefag_available': self.grundskolefag_available()
        }
        context.update(kwargs)
        return super(BookingView, self).get_context_data(**context)

    def dispatch(self, request, *args, **kwargs):
        self.modal = request.GET.get('modal', '0') == '1'
        self.back = request.GET.get('back')
        return super(BookingView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.set_product(kwargs.get("product"))
        if self.product is None:
            return bad_request(request)

        self.object = Booking()
        return self.render_to_response(
            self.get_context_data(**self.get_forms())
        )

    def post(self, request, *args, **kwargs):
        self.set_product(kwargs.get("product"))
        if self.product is None:
            return bad_request(request)

        self.object = Booking()

        self._old_state = self._as_state()

        forms = self.get_forms(request.POST)

        # We must disregard one of the school subject forms, depending on
        # which school is selected
        forms['bookerform'].full_clean()
        school_type = forms['bookerform'].schooltype

        dep = {
            School.GYMNASIE: 'gymnasiesubjectform',
            School.ELEMENTARY_SCHOOL: 'grundskolesubjectform'
        }
        exclude = [value for key, value in dep.items() if school_type != key]
        relevant_forms = {
            name: forms[name] for name in forms if name not in exclude
        }

        valid = True
        for (name, form) in relevant_forms.items():
            form.full_clean()
            if not form.is_valid():
                valid = False

        if valid:
            if 'bookingform' in relevant_forms:
                booking = relevant_forms['bookingform'].save(commit=False)
                eventtime_pk = relevant_forms['bookingform'].cleaned_data.get(
                    'eventtime', ''
                )
            else:
                booking = self.object
                eventtime_pk = None

            if eventtime_pk:
                eventtime = self.product.eventtime_set.filter(
                    pk=eventtime_pk
                ).first()
            else:
                eventtime = None

            if not eventtime:
                # Make a non-bookable time with no time specified
                eventtime = booking_models.EventTime(
                    product=self.product,
                    bookable=False,
                )

            # If the chosen eventtime does not have a visit, create it now
            if not eventtime.visit:
                eventtime.make_visit()
                log_action(
                    self.request.user,
                    eventtime.visit,
                    LOGACTION_CREATE,
                    _(u'Besøg oprettet')
                )

            booking.visit = eventtime.visit

            available_seats = booking.visit.available_seats

            if 'bookerform' in relevant_forms:
                booking.booker = relevant_forms['bookerform'].save()

            booking = relevant_forms['bookingform'].save()

            put_in_waitinglist = False

            attendee_count = booking.booker.attendee_count
            if booking.visit.product.do_create_waiting_list and \
                    attendee_count > available_seats:
                # Put in waiting list
                put_in_waitinglist = True

                if booking.visit.waiting_list_closed:
                    booking.delete()
                    raise Exception(_(u"Cannot place booking with in waiting "
                                      u"list; the waiting list is closed"))
                waitinglist_capacity = \
                    booking.visit.waiting_list_capacity
                if attendee_count > waitinglist_capacity:
                    booking.delete()
                    raise Exception(_(u"Cannot place booking with %d attendees"
                                      u" in waiting list; there are only %d "
                                      u"spots") %
                                    (attendee_count, waitinglist_capacity))

                booking.waitinglist_spot = \
                    booking.visit.next_waiting_list_spot

            booking.save()

            for formname in ['gymnasiesubjectform', 'grundskolesubjectform']:
                subjectform = relevant_forms.get(formname)
                if subjectform:
                    subjectform.instance = booking
                    if subjectform.is_valid():
                        subjectform.save()

            booking.ensure_statistics()

            # Flag attention requirement on visit
            booking.visit.needs_attention_since = timezone.now()

            # Trigger updating of search index
            booking.visit.save()

            if put_in_waitinglist:
                booking.autosend(
                    EmailTemplateType.notify_guest__booking_created_waiting
                )
            elif booking.visit.product.uses_time_management:
                booking.autosend(
                    EmailTemplateType.notify_guest__booking_created
                )
            else:
                booking.autosend(
                    EmailTemplateType.notify_guest__booking_created_untimed
                )

            booking.autosend(
                EmailTemplateType.notify_editors__booking_created
            )

            if booking.visit.needs_teachers or \
                    booking.visit.product.is_resource_controlled:
                booking.autosend(
                    EmailTemplateType.notify_host__req_teacher_volunteer
                )

            if booking.visit.needs_hosts or \
                    booking.visit.product.is_resource_controlled:
                booking.autosend(
                    EmailTemplateType.notify_host__req_host_volunteer
                )

            self.object = booking
            self.model = booking.__class__

            self._log_changes()

            params = {
                'modal': 1 if self.modal else 0,
            }
            if self.back:
                params['back'] = self.back

            return redirect(
                self.modalurl(
                    reverse("product-book-success", args=[self.product.id]) +
                    "?" + urllib.urlencode(params)
                )
            )

        return self.render_to_response(
            self.get_context_data(**forms)
        )

    def get_forms(self, data=None):
        forms = {}
        if self.product is not None:
            forms['bookerform'] = \
                BookerForm(data, products=[self.product],
                           language=self.request.LANGUAGE_CODE)

            type = self.product.type
            if type == Product.GROUP_VISIT:
                forms['bookingform'] = ClassBookingForm(
                    data,
                    product=self.product
                )
                if self.product.productgymnasiefag_set.count() > 0:
                    forms['gymnasiesubjectform'] = \
                        BookingGymnasieSubjectLevelForm(data)

                if self.product.productgrundskolefag_set.count() > 0:
                    forms['grundskolesubjectform'] = \
                        BookingGrundskoleSubjectLevelForm(data)

            elif type == Product.TEACHER_EVENT:
                forms['bookingform'] = TeacherBookingForm(data,
                                                          product=self.product)
            elif type == Product.STUDENT_FOR_A_DAY:
                forms['bookingform'] = \
                    StudentForADayBookingForm(data, product=self.product)
            elif type == Product.STUDY_PROJECT:
                forms['bookingform'] = \
                    StudyProjectBookingForm(data, product=self.product)
        return forms

    def get_template_names(self):
        if self.product is None:
            return [""]
        if self.product.type == Product.STUDENT_FOR_A_DAY:
            if self.modal:
                return ["booking/studentforaday_modal.html"]
            else:
                return ["booking/studentforaday.html"]
        if self.product.type == Product.GROUP_VISIT:
            if self.modal:
                return ["booking/classvisit_modal.html"]
            else:
                return ["booking/classvisit.html"]
        if self.product.type == Product.TEACHER_EVENT:
            if self.modal:
                return ["booking/teachervisit_modal.html"]
            else:
                return ["booking/teachervisit.html"]
        if self.product.type == Product.STUDY_PROJECT:
            if self.modal:
                return ["booking/studyproject_modal.html"]
            else:
                return ["booking/studyproject.html"]

    def gymnasiefag_available(self):
        result = []
        obj = self.product
        if self.request.method == 'GET':
            if obj and obj.pk:
                for x in obj.productgymnasiefag_set.all():
                    result.append({
                        'submitvalue': x.as_submitvalue(),
                        'description': x.display_value()
                    })

        return result

    def grundskolefag_available(self):
        result = []
        obj = self.product
        if self.request.method == 'GET':
            if obj and obj.pk:
                for x in obj.productgrundskolefag_set.all():
                    result.append({
                        'submitvalue': x.as_submitvalue(),
                        'description': x.display_value()
                    })
        return result


class BookingSuccessView(DetailView):
    template_name = "booking/success.html"
    model = Product
    modal = True

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.modal = request.GET.get('modal', '1') == '1'
        data = {
            'back': request.GET.get('back')
        }
        return self.render_to_response(
            self.get_context_data(**data)
        )

    def get_template_names(self):
        if self.modal:
            return ["booking/success_modal.html"]
        else:
            return ["booking/success.html"]


class VisitBookingCreateView(BreadcrumbMixin, AutologgerMixin, CreateView):
    model = Booking
    visit = None
    object = None
    template_name = 'booking/form.html'
    modal = False

    def dispatch(self, request, *args, **kwargs):
        self.visit = Visit.objects.get(id=kwargs['visit'])
        return super(VisitBookingCreateView, self).dispatch(
            request, *args, **kwargs
        )

    @property
    def product(self):
        # return None
        return self.visit.product

    def get(self, request, *args, **kwargs):
        print "VisitBookingCreateView"
        return self.render_to_response(
            self.get_context_data(**self.get_forms())
        )

    def post(self, request, *args, **kwargs):
        forms = self.get_forms(request.POST)
        all_valid = True
        for key, form in forms.iteritems():
            if not form.is_valid():
                all_valid = False
        if all_valid:
            return self.form_valid(forms)
        else:
            return self.form_invalid(forms)

    def form_valid(self, forms):
        object = self.object = forms['bookingform'].save(commit=False)
        object.visit = self.visit
        if 'bookerform' in forms:
            object.booker = forms['bookerform'].save()
        object.save()

        object.autosend(
            EmailTemplateType.notify_guest__booking_created_untimed
        )

        object.autosend(EmailTemplateType.notify_editors__booking_created)

        return redirect(
            reverse(
                'visit-booking-success',
                args=[object.visit.products[0].id]
            ) + "?modal=0"
        )

    def form_invalid(self, forms):
        return self.render_to_response(self.get_context_data(**forms))

    def get_forms(self, data=None):
        forms = {}
        bookingform = None
        forms['bookerform'] = BookerForm(
            data,
            products=self.visit.products,
            language=self.request.LANGUAGE_CODE
        )
        type = None

        if self.product:
            type = self.product.type

        if type == Product.GROUP_VISIT:
            bookingform = ClassBookingForm(data, product=self.product)
            if self.product.productgymnasiefag_set.count() > 0:
                forms['subjectform'] = BookingGymnasieSubjectLevelForm(data)
            if self.product.productgrundskolefag_set.count() > 0:
                forms['grundskolesubjectform'] = \
                    BookingGrundskoleSubjectLevelForm(data)

        elif type == Product.TEACHER_EVENT:
            bookingform = TeacherBookingForm(data, product=self.product)

        elif type == Product.STUDENT_FOR_A_DAY:
            bookingform = StudentForADayBookingForm(data, product=self.product)

        elif type == Product.STUDY_PROJECT:
            bookingform = StudyProjectBookingForm(data, product=self.product)

        else:
            bookingform = BookingForm(data)

        if bookingform is not None:
            if self.visit.multiproductvisit:
                if 'tmp' in self.request.GET:
                    temp = MultiProductVisitTemp.objects.get(
                        id=self.request.GET['tmp']
                    )
                    bookingform.initial['notes'] = temp.notes
                if 'desired_time' in bookingform.fields:
                    del bookingform.fields['desired_time']

            forms['bookingform'] = bookingform
        return forms

    def get_context_data(self, **kwargs):
        available_times = {}

        if self.product:
            for eventtime in self.product.future_times:
                available_times[str(eventtime.pk)] = {
                    'available': eventtime.available_seats,
                    'waitinglist': eventtime.waiting_list_capacity
                }

        context = {
            'level_map': Guest.level_map,
            'modal': self.modal,
            'times_available': available_times
        }
        context.update(kwargs)
        return super(VisitBookingCreateView, self).get_context_data(**context)


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


class VisitListView(LoginRequiredMixin, BreadcrumbMixin, ListView):
    model = Visit
    template_name = "visit/list.html"
    context_object_name = "results"
    paginate_by = 10

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

        context.update(kwargs)

        return super(VisitListView, self).get_context_data(
            **context
        )

    def get_paginate_by(self, queryset):
        size = self.request.GET.get("pagesize", 10)
        if size == "all":
            return None
        return size

    @staticmethod
    def build_breadcrumbs():
        return VisitSearchView.build_breadcrumbs() + [
            {'text': _(u'Besøgsliste')}
        ]


class VisitCustomListView(VisitListView):

    TYPE_LATEST_COMPLETED = "latest_completed"
    TYPE_LATEST_BOOKED = "latest_booked"
    TYPE_LATEST_UPDATED = "latest_updated"
    TYPE_TODAY = "today"

    def get_queryset(self):
        try:
            listtype = self.request.GET.get("type", "")

            if listtype == self.TYPE_LATEST_COMPLETED:
                return Visit.get_recently_held()
            elif listtype == self.TYPE_LATEST_BOOKED:
                return Visit.get_latest_booked()
            elif listtype == self.TYPE_LATEST_UPDATED:
                return Visit.get_latest_updated()
            elif listtype == self.TYPE_TODAY:
                return Visit.get_todays_visits()
        except:
            pass
        raise Http404


class VisitSearchView(VisitListView):
    template_name = "visit/searchresult.html"

    form = None

    def get_form(self):
        if not self.form:
            # Make new form object
            self.form = VisitSearchForm(
                self.request.GET,
                user=self.request.user
            )
            # Process the form
            self.form.is_valid()
        return self.form

    def get_queryset(self):
        form = self.get_form()

        q = form.cleaned_data.get("q", "").strip()

        # Filtering by freetext has to be the first thing we do
        qs = self.model.objects.search(q)

        for filter_method in (
            self.filter_multiproduct_subs_off,
            self.filter_by_resource_id,
            self.filter_by_unit,
            self.filter_by_date,
            self.filter_by_workflow,
            self.filter_by_participants,
        ):
            try:
                qs = filter_method(qs)
            except Exception as e:
                print "Error while filtering VO search: %s" % e

        qs = qs.order_by("-pk")

        return qs

    def filter_multiproduct_subs_off(self, qs):
        qs = qs.filter(is_multi_sub=False)
        return qs

    def filter_by_resource_id(self, qs):
        form = self.get_form()
        t = form.cleaned_data.get("t", "").strip()

        if re.match('^#?\d+$', t):
            if t[0] == "#":
                t = t[1:]
            qs = qs.filter(product__pk=t)
        elif t:
            qs = self.model.objects.none()

        return qs

    def filter_by_unit(self, qs):
        form = self.get_form()
        u = form.cleaned_data.get("u", form.MY_UNITS)

        if u == "":
            return qs

        u = int(u)
        profile = self.request.user.userprofile
        unit_qs = None

        if u == form.MY_UNIT:
            unit_qs = profile.organizationalunit
        elif u == form.MY_FACULTY:
            unit_qs = profile.organizationalunit.get_faculty_queryset()
        elif u == form.MY_UNITS:
            unit_qs = profile.get_unit_queryset()
        else:
            unit_qs = u

        return Visit.unit_filter(qs, unit_qs)

    def filter_by_date(self, qs):
        form = self.get_form()

        from_date = form.cleaned_data.get("from_date", None)
        if from_date is not None:
            from_date = timezone.datetime(
                year=from_date.year,
                month=from_date.month,
                day=from_date.day,
                tzinfo=timezone.get_default_timezone()
            )
            qs = qs.filter(eventtime__start__gte=from_date)

        to_date = form.cleaned_data.get("to_date", None)
        if to_date is not None:
            to_date = timezone.datetime(
                year=to_date.year,
                month=to_date.month,
                day=to_date.day,
                hour=23,
                minute=59,
                tzinfo=timezone.get_default_timezone()
            )
            qs = qs.filter(eventtime__end__lte=to_date)

        return qs

    def filter_by_workflow(self, qs):
        form = self.get_form()
        w = form.cleaned_data.get("w", "")

        if w == "":
            return qs

        w = int(w)

        planned_status = Visit.WORKFLOW_STATUS_BEING_PLANNED
        if w == form.WORKFLOW_STATUS_PENDING:
            return qs.filter(workflow_status=planned_status)
        elif w == form.WORKFLOW_STATUS_READY:
            return qs.exclude(workflow_status=planned_status)
        else:
            return qs.filter(workflow_status=w)

    def filter_by_participants(self, qs):
        # Number of individual bookers plus attendee count
        qs = qs.annotate(num_participants=(
            Coalesce(Count("bookings__booker__pk"), 0) +
            Coalesce(Sum("bookings__booker__attendee_count"), 0)
        ))

        form = self.get_form()

        p_min = ""

        try:
            p_min = form.cleaned_data.get("p_min", "")
        except:
            pass

        if p_min != "":
            qs = qs.filter(num_participants__gte=p_min)

        p_max = ""

        try:
            p_max = form.cleaned_data.get("p_max", "")
        except:
            pass

        if p_max != "":
            qs = qs.filter(num_participants__lte=p_max)

        return qs

    def get_context_data(self, **kwargs):
        context = {}

        context['form'] = self.get_form()

        context.update(kwargs)

        return super(VisitSearchView, self).get_context_data(
            **context
        )

    def get_breadcrumbs(self):
        breadcrumbs = VisitSearchView.build_breadcrumbs()
        form = self.get_form()
        if len(form.cleaned_data):
            breadcrumbs.append({
                'text': _(u'Søgeresultat'),
                'url': reverse('visit-search') + '?' + '&'.join([
                    "%s=%s" % (key, unicode(value))
                    for key, value in form.cleaned_data.iteritems()
                ])
            })
        return breadcrumbs

    @staticmethod
    def build_breadcrumbs():
        return [
            {
                'url': reverse('visit-search'),
                'text': _(u'Søg i besøg')
            }
        ]


class BookingDetailView(LoginRequiredMixin, LoggedViewMixin, BreadcrumbMixin,
                        ProductBookingDetailView):
    """Display Booking details"""
    model = Booking
    template_name = 'booking/details.html'

    def get_context_data(self, **kwargs):
        context = {}

        context['modal'] = BookingNotifyView.modal

        user = self.request.user
        if hasattr(user, 'userprofile') and \
                user.userprofile.can_notify(self.object):
            context['can_notify'] = True

        if self.object.visit.is_multiproductvisit:
            context['emailtemplates'] = EmailTemplateType.get_choices(
                manual_sending_booking_mpv_enabled=True
            )
        else:
            context['emailtemplates'] = EmailTemplateType.get_choices(
                manual_sending_booking_enabled=True
            )

        context.update(kwargs)

        return super(BookingDetailView, self).get_context_data(**context)

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(booking):
        return VisitDetailView.build_breadcrumbs(booking.visit) + [
            {
                'url': reverse('booking-view', args=[booking.id]),
                'text': booking
            }
        ]


class VisitDetailView(LoginRequiredMixin, LoggedViewMixin, BreadcrumbMixin,
                      ProductBookingDetailView):
    """Display Booking details"""
    model = Visit
    template_name = 'visit/details.html'

    def get_object(self):
        object = super(VisitDetailView, self).get_object()
        try:
            return MultiProductVisit.objects.get(visit_ptr_id=object.id)
        except MultiProductVisit.DoesNotExist:
            return object

    def get_context_data(self, **kwargs):
        context = {}

        context['modal'] = VisitNotifyView.modal

        if self.object.is_multiproductvisit:
            context['emailtemplates'] = EmailTemplateType.get_choices(
                manual_sending_mpv_enabled=True
            )
        elif self.object.is_multi_sub:
            context['emailtemplates'] = EmailTemplateType.get_choices(
                manual_sending_mpv_sub_enabled=True
            )
        else:
            context['emailtemplates'] = EmailTemplateType.get_choices(
                manual_sending_visit_enabled=True
            )

        context['emailtemplate_waitinglist'] = \
            EmailTemplateType.NOTIFY_GUEST__SPOT_OPEN
        user = self.request.user

        usertype = self.kwargs.get('usertype')
        if isinstance(usertype, basestring):
            usertype = usertype.lower()

        if hasattr(user, 'userprofile'):
            # Add information about the users association with the visit
            context.update(self.object.context_for_user(
                self.request.user, usertype
            ))

        context['bookinglistform'] = self.get_bookinglist_form()
        context['waitinglistform'] = self.get_waitinglist_form()
        context['waitingattendees'] = {
            booking.id: booking.booker.attendee_count
            for booking in self.object.waiting_list
        }

        context['teacher'] = usertype == 'teacher'
        context['host'] = usertype == 'host'

        context.update(kwargs)

        return super(VisitDetailView, self).get_context_data(
            **context
        )

    def get_bookinglist_form(self, **kwargs):
        bookinglistform = BookingListForm(data=kwargs)
        bookinglistform.fields['bookings'].choices = [
            (booking.id, booking.id) for booking in self.object.booking_list
        ]
        return bookinglistform

    def get_waitinglist_form(self, **kwargs):
        waitinglistform = BookingListForm(data=kwargs)
        waitinglistform.fields['bookings'].choices = [
            (booking.id, booking.id) for booking in self.object.waiting_list
            ]
        return waitinglistform

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST['action']
        listname = request.POST['listname']

        form = None
        if listname == 'booking':
            form = self.get_bookinglist_form(**request.POST)
        elif listname == 'waiting':
            form = self.get_waitinglist_form(**request.POST)
        if form is not None:
            if form.is_valid():
                for booking_id in form.cleaned_data['bookings']:
                    booking = Booking.objects.filter(id=booking_id).first()
                    if action == 'delete':
                        booking.delete()
                    elif action == 'enqueue':
                        booking.enqueue()
                    elif action == 'dequeue':
                        booking.dequeue()
        return self.get(request, *args, **kwargs)

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(visit):
        if visit.product:
            breadcrumbs = ProductDetailView.build_breadcrumbs(visit.product)
        else:
            breadcrumbs = VisitSearchView.build_breadcrumbs()
        if visit.is_multi_sub:
            breadcrumbs.append({
                'text': visit.multi_master.id_display,
                'url': reverse('visit-view', args=[visit.multi_master.id])
            })
        breadcrumbs.append({
            'text': visit.id_display,
            'url': reverse('visit-view', args=[visit.id])
        })
        return breadcrumbs


class EmailTemplateListView(LoginRequiredMixin, BreadcrumbMixin, ListView):
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
                        and objectA.type == objectB.type \
                        and objectA.organizationalunit == \
                        objectB.organizationalunit:
                    context['duplicates'].extend([objectA, objectB])
        context.update(kwargs)
        return super(EmailTemplateListView, self).get_context_data(**context)

    def get_queryset(self):
        qs = super(EmailTemplateListView, self).get_queryset()
        qs = [item
              for item in qs
              if self.request.user.userprofile.can_edit(item)]
        return qs

    @staticmethod
    def build_breadcrumbs():
        return [
            {
                'url': reverse('emailtemplate-list'),
                'text': _(u'Emailskabelonliste')
            },
        ]


class EmailTemplateEditView(LoginRequiredMixin, UnitAccessRequiredMixin,
                            BreadcrumbMixin, UpdateView, BackMixin):
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
        if 'type' in request.GET:
            form.initial['type'] = request.GET['type']
        if 'organizationalunit' in request.GET:
            form.initial['organizationalunit'] = \
                request.GET['organizationalunit']
        return self.render_to_response(
            self.get_context_data(form=form)
        )

    def is_cloning(self):
        return self.kwargs.get("clone", False)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is None or self.is_cloning():
            self.object = EmailTemplate()
        else:
            self.object = EmailTemplate.objects.get(pk=pk)
            self.check_item(self.object)

        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            self.object = form.save()
            self.object.key = self.object.type.key
            self.object.save()
            return self.redirect(reverse('emailtemplate-list'))

        return self.render_to_response(
            self.get_context_data(**context)
        )

    def get_context_data(self, **kwargs):
        context = {}
        context['modelmap'] = modelmap = {}

        for model in [Booking, Visit, Product]:
            model_name = model.__name__
            modelmap[(model_name.lower(), model._meta.verbose_name)] = \
                get_model_field_map(model)

        context.update(kwargs)
        return super(EmailTemplateEditView, self).get_context_data(**context)

    def get_form_kwargs(self):
        args = super(EmailTemplateEditView, self).get_form_kwargs()
        args['user'] = self.request.user
        return args

    def get_breadcrumb_args(self):
        return [self.object, self.is_cloning()]

    @staticmethod
    def build_breadcrumbs(template, cloning=False):
        if template:
            return EmailTemplateDetailView.build_breadcrumbs(template) + [
                {
                    'url': reverse(
                        'emailtemplate-clone' if cloning else
                        'emailtemplate-edit',
                        args=[template.id]
                    ),
                    'text': _(u'Kopiér') if cloning else _(u'Redigér')
                },
            ]
        else:
            return EmailTemplateListView.build_breadcrumbs() + [
                {'text': _(u'Opret')}
            ]


class EmailTemplateDetailView(LoginRequiredMixin, BreadcrumbMixin, View):
    template_name = 'email/preview.html'

    classes = {'OrganizationalUnit': OrganizationalUnit,
               'Product': Product,
               'Visit': Visit,
               # 'StudyMaterial': StudyMaterial,
               # 'Product': Product,
               # 'Subject': Subject,
               # 'GymnasieLevel': GymnasieLevel,
               # 'Room': Room,
               # 'PostCode': PostCode,
               # 'School': School,
               'Booking': Booking,
               # 'ProductGymnasieFag': ProductGymnasieFag,
               # 'ProductGrundskoleFag': ProductGrundskoleFag
               }

    @staticmethod
    def _getObjectJson():
        return json.dumps({
            key: [
                {'text': unicode(object), 'value': object.id}
                for object in type.objects.order_by('id')
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
                    variable = base_variable.lower()
                    lookup = {
                        key.lower(): key
                        for key in self.classes.keys()
                    }
                    if variable in lookup:
                        type = lookup[variable]
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

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(template):
        return EmailTemplateListView.build_breadcrumbs() + [
            {
                'url': reverse('emailtemplate-view', args=[template.id]),
                'text': template.name
            }
        ]


class EmailTemplateDeleteView(HasBackButtonMixin, LoginRequiredMixin,
                              BreadcrumbMixin, DeleteView):
    template_name = 'email/delete.html'
    model = EmailTemplate
    success_url = reverse_lazy('emailtemplate-list')

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(template):
        return EmailTemplateDetailView.build_breadcrumbs(template) + [
            {
                'url': reverse('emailtemplate-delete', args=[template.id]),
                'text': _(u'Slet')
            }
        ]


class EmailReplyView(BreadcrumbMixin, DetailView):
    model = KUEmailMessage
    template_name = "email/reply.html"
    slug_field = 'reply_nonce'
    slug_url_kwarg = 'reply_nonce'
    form = None
    original_object = None

    def get_form(self):
        if self.form is None:
            if self.request.method == "GET":
                self.form = EmailReplyForm()
            else:
                self.form = EmailReplyForm(self.request.POST)
        return self.form

    def get_original_object(self):
        if self.original_object is None:
            try:
                ct = ContentType.objects.get(pk=self.object.content_type_id)
                self.original_object = ct.get_object_for_this_type(
                    pk=self.object.object_id
                )
            except Exception as e:
                print "Error when getting email-reply object: %s" % e

        return self.original_object

    def get_product(self):
        orig_obj = self.get_original_object()
        if type(orig_obj) == Visit:
            return orig_obj.product
        elif type(orig_obj) == Product:
            return orig_obj

        return None

    def get_context_data(self, **kwargs):
        context = {}
        context['form'] = self.get_form()
        context['product'] = self.get_product()
        context.update(kwargs)
        return super(EmailReplyView, self).get_context_data(**context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            self.object = self.get_object()
            orig_obj = self.get_original_object()
            orig_message = self.object
            visit = orig_obj if type(orig_obj) == Visit else None
            reply = form.cleaned_data.get('reply', "").strip()
            product = self.get_product()

            recipients = product.get_responsible_persons()

            KUEmailMessage.send_email(
                EmailTemplateType.system__email_reply,
                {
                    'visit': visit,
                    'product': product,
                    'orig_object': orig_obj,
                    'orig_message': orig_message,
                    'reply': reply,
                    'log_message': _(u"Svar:") + "\n" + reply
                },
                recipients,
                orig_obj,
                organizationalunit=product.organizationalunit
            )
            result_url = reverse(
                'reply-to-email', args=[self.object.reply_nonce]
            )

            # Mark visit as needing attention
            if visit:
                visit.set_needs_attention()

            return redirect(result_url + '?thanks=1')
        else:
            return self.get(request, *args, **kwargs)

    def get_breadcrumb_args(self):
        return [self.get_product()]

    @staticmethod
    def build_breadcrumbs(product):
        breadcrumbs = []
        if product:
            breadcrumbs = ProductDetailView.build_breadcrumbs(product)
        breadcrumbs.append({'text': _(u'Svar på e-mail')})
        return breadcrumbs


class EvaluationOverviewView(LoginRequiredMixin, BreadcrumbMixin, ListView):
    model = Visit
    template_name = "evaluation/list.html"
    context_object_name = "results"
    form = None

    def get_form(self):
        if not self.form:
            self.form = EvaluationOverviewForm(
                self.request.GET,
                user=self.request.user
            )
            self.form.is_valid()

        return self.form

    def get_queryset(self):
        form = self.get_form()

        if form.is_valid():
            formdata = form.cleaned_data
            qs = self.model.objects.filter(
                product__organizationalunit__in=form.user
                .userprofile.get_unit_queryset(),
                evaluation_link__isnull=False,
            ).exclude(
                evaluation_link="",
            )
            unit_limit = formdata.get('organizationalunit', [])
            if unit_limit:
                qs = qs.filter(
                    product__organizationalunit__in=unit_limit
                )
            if formdata.get('limit_to_personal'):
                user = self.request.user
                qs = qs.filter(
                    Q(product__created_by=user) |
                    Q(teachers=user) |
                    Q(hosts=user) |
                    Q(product__tilbudsansvarlig=user)
                )
        else:
            qs = self.model.objects.none()

        return qs.order_by('-eventtime__start', '-eventtime__end')

    def get_context_data(self, **kwargs):
        return super(EvaluationOverviewView, self).get_context_data(
            form=self.get_form(),
            **kwargs
        )

    @staticmethod
    def build_breadcrumbs():
        return [
            {
                'url': reverse('evaluations'),
                'text': _(u'Oversigt over evalueringer')
            }
        ]


import booking_workflows.views  # noqa
import_views(booking_workflows.views)

import resource_based.views  # noqa
import_views(resource_based.views)


class BookingAcceptView(BreadcrumbMixin, FormView):
    template_name = "booking/accept_spot.html"
    form_class = AcceptBookingForm
    object = None
    answer = None
    dequeued = False

    # Placeholder for storing a deleted booking's id for display
    object_id = None

    def dispatch(self, request, *args, **kwargs):
        token = kwargs.get('token')
        if not token:
            raise Http404
        try:
            bookerentry = BookerResponseNonce.objects.get(uuid=token)
            self.object = Booking.objects.get(booker=bookerentry.booker)
        except Booking.DoesNotExist:
            raise AccessDenied(_(u"Booking findes ikke længere"))
        except BookerResponseNonce.DoesNotExist:
            raise AccessDenied(_(u"Ugyldig token"))
        if bookerentry.is_expired():
            raise AccessDenied(_(u"Token er udløbet"))
        if self.object.booker != bookerentry.booker:
            raise AccessDenied(_(u"Ugyldig token"))
        return super(BookingAcceptView, self).\
            dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(BookingAcceptView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            self.answer = request.POST.get('answer')
            if self.answer == 'yes':
                if self.object.can_dequeue:
                    self.object.dequeue()
                    self.dequeued = True
                    self.object.autosend(
                        EmailTemplateType.notify_guest__spot_accepted
                    )
            elif self.answer == 'no':
                self.object.autosend(
                    EmailTemplateType.notify_guest__spot_rejected
                )
                self.object.autosend(
                    EmailTemplateType.notify_editors__spot_rejected
                )
                self.object_id = self.object.id
                self.object.delete()

            comment = form.cleaned_data['comment']
            self.object.visit.add_comment(None, comment)

        return self.render_to_response(
            self.get_context_data(comment_added=True)
        )

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context['object_id'] = self.object_id
        context['answer'] = self.answer
        context['dequeued'] = self.dequeued

        context.update(kwargs)
        return super(BookingAcceptView, self).get_context_data(**context)

    def get_breadcrumb_args(self):
        return [self.object, self.object_id]

    @staticmethod
    def build_breadcrumbs(booking, object_id=None):
        breadcrumbs = BookingDetailView.build_breadcrumbs(booking)
        if object_id:
            breadcrumbs[-1]['text'] = _(u"Slettet tilmelding")
        breadcrumbs.append({
            'text': _(u'Svar på ledig plads')
        })
        return breadcrumbs


class MultiProductVisitPromptView(BreadcrumbMixin, DetailView):
    model = Product
    template_name = "visit/multi_prompt.html"

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(product):
        return ProductDetailView.build_breadcrumbs(product) + [
            {
                'url': reverse('product-book-notime', args=[product.id]),
                'text': _(u'Vælg bestillingstype')
            }
        ]


class MultiProductVisitTempDateView(BreadcrumbMixin, HasBackButtonMixin,
                                    ModelFormMixin, ProcessFormView):
    form_class = MultiProductVisitTempDateForm
    model = MultiProductVisitTemp
    template_name = "visit/multi_date.html"

    def get_form_kwargs(self):
        kwargs = super(MultiProductVisitTempDateView, self).get_form_kwargs()
        if 'base' in self.request.GET:
            kwargs['initial'] = {'baseproduct': Product.objects.get(
                id=self.request.GET['base']
            )}
        return kwargs

    def get_success_url(self):
        if 'next' in self.request.GET:
            return self.request.GET['next']
        return reverse('mpv-edit-products', args=[self.object.id])


class MultiProductVisitTempCreateView(MultiProductVisitTempDateView,
                                      CreateView):
    def form_valid(self, form):
        response = super(MultiProductVisitTempCreateView, self).\
            form_valid(form)
        if 'base' in self.request.GET:
            try:
                self.object.baseproduct = Product.objects.get(
                    id=self.request.GET['base']
                )
                self.object.save()
            except:
                pass
        return response

    def get_breadcrumb_args(self):
        try:
            return [Product.objects.get(id=self.request.GET['base'])]
        except:
            return []

    @staticmethod
    def build_breadcrumbs(product=None):
        breadcrumbs = ProductDetailView.build_breadcrumbs(product) \
            if product is not None else []
        breadcrumbs.append({
            'url': reverse('mpv-create'),
            'text': _(u'Vælg dato')
        })
        return breadcrumbs


class MultiProductVisitTempUpdateView(MultiProductVisitTempDateView,
                                      UpdateView):

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(mpv):
        return ProductDetailView.build_breadcrumbs(mpv.baseproduct) + [
            {
                'url': reverse('mpv-edit-date', args=[mpv.id]),
                'text': _(u'Vælg dato')
            }
        ]


class MultiProductVisitTempProductsView(BreadcrumbMixin, UpdateView):

    form_class = MultiProductVisitTempProductsForm
    model = MultiProductVisitTemp
    template_name = "visit/multi_products.html"
    _available_products = None
    products_key = 'products'

    def get_form(self):
        form = super(MultiProductVisitTempProductsView, self).get_form()
        form.fields[self.products_key].choices = [
            (product.id, product.title)
            for product in self.available_products
        ]
        form.initial[self.products_key] = [
            product for product in self.object.products_ordered
            if product in self.available_products
        ]
        return form

    def get_context_data(self, **kwargs):
        context = {}
        context['available_products'] = {
            product.id: product
            for product in self.available_products
        }
        context.update(kwargs)
        return super(MultiProductVisitTempProductsView, self).get_context_data(
            **context
        )

    @property
    def available_products(self):
        if self._available_products is None:
            filter = {
                'state': Product.ACTIVE,
                'time_mode': Product.TIME_MODE_GUEST_SUGGESTED,
            }
            institution_level = self.object.baseproduct.institution_level
            if institution_level != Subject.SUBJECT_TYPE_BOTH:
                filter['institution_level'] = institution_level
            self._available_products = [
                product
                for product in Product.objects.filter(**filter)
                if product.is_bookable(self.object.date)
            ]
        return self._available_products

    def get_success_url(self):
        if 'next' in self.request.GET:
            return self.request.GET['next']
        return reverse('mpv-confirm', args=[self.object.id])

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(mpv):
        return ProductDetailView.build_breadcrumbs(mpv.baseproduct) + [
            {
                'url': reverse('mpv-edit-products', args=[mpv.id]),
                'text': _(u'Vælg tilbud')
            }
        ]


class MultiProductVisitTempConfirmView(BreadcrumbMixin, DetailView):
    model = MultiProductVisitTemp
    template_name = "visit/multi_confirm.html"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        mpv = self.object.create_mpv()
        # self.object.delete()
        return redirect(
            reverse('visit-booking-create', args=[mpv.id]) +
            "?tmp=%d" % self.object.id
        )

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(mpv):
        return ProductDetailView.build_breadcrumbs(mpv.baseproduct) + [
            {
                'url': reverse('mpv-confirm', args=[mpv.id]),
                'text': _(u'Bekræft')
            }
        ]
