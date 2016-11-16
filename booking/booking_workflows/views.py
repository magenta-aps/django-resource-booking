# -*- coding: utf-8 -*-

from django.db.models.expressions import OrderBy
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import formats, timezone
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView, FormView
from booking.booking_workflows.forms import ChangeVisitStatusForm, \
    BecomeSomethingForm
from booking.booking_workflows.forms import VisitAutosendFormSet
from booking.booking_workflows.forms import ChangeVisitResponsibleForm
from booking.booking_workflows.forms import ChangeVisitTeachersForm
from booking.booking_workflows.forms import ChangeVisitHostsForm
from booking.booking_workflows.forms import ChangeVisitRoomsForm
from booking.booking_workflows.forms import ChangeVisitCommentsForm
from booking.booking_workflows.forms import ChangeVisitEvalForm
from booking.booking_workflows.forms import VisitAddLogEntryForm
from booking.booking_workflows.forms import VisitAddCommentForm
from booking.booking_workflows.forms import ResetVisitChangesForm
from booking.models import Visit
from booking.models import EmailTemplate, EmailTemplateType
from booking.models import EventTime
from booking.models import Locality
from booking.models import LOGACTION_MANUAL_ENTRY
from booking.models import log_action
from booking.models import Room
from booking.models import MultiProductVisit
from booking.views import AutologgerMixin
from booking.views import RoleRequiredMixin, EditorRequriedMixin
from booking.views import VisitDetailView
from django.views.generic.base import ContextMixin
from profile.models import TEACHER, HOST, EDIT_ROLES
from itertools import chain

import booking.models


class VisitBreadcrumbMixin(ContextMixin):
    view_title = _(u'opdater')

    def get_breadcrumb_args(self):
        return [self.object]

    def get_context_data(self, **kwargs):
        breadcrumbs = VisitDetailView.build_breadcrumbs(
            *self.get_breadcrumb_args()
        )
        breadcrumbs.append({'text': self.view_title})
        context = {
            'breadcrumbs': breadcrumbs
        }
        context.update(kwargs)
        return super(VisitBreadcrumbMixin, self).\
            get_context_data(**context)


class UpdateWithCancelView(VisitBreadcrumbMixin, EditorRequriedMixin,
                           UpdateView):
    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            self.object = self.get_object()
            return redirect(self.get_success_url())
        else:
            return super(UpdateWithCancelView, self).post(
                request, *args, **kwargs
            )


class ChangeVisitStartTimeView(AutologgerMixin,
                               UpdateWithCancelView):
    model = EventTime
    template_name = "booking/workflow/change_starttime.html"
    view_title = _(u'Redigér tidspunkt')

    fields = ('has_specific_time', 'start', 'end', 'notes')

    def get_object(self, queryset=None):
        return self.model.objects.filter(visit=self.kwargs['visit_pk']).first()

    def get_form(self, form_class=None):
        form = super(ChangeVisitStartTimeView, self).get_form(
            form_class=form_class
        )
        form.fields['has_specific_time'].coerce = lambda x: x == 'True'

        return form

    def get_context_data(self, **kwargs):
        return super(ChangeVisitStartTimeView, self).get_context_data(
            product=self.object.product,
            use_product_duration=self.object.duration_matches_product,
            **kwargs
        )

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.visit.pk])

    def get_breadcrumb_args(self):
        return [self.object.visit]


class ChangeVisitStatusView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitStatusForm
    template_name = "booking/workflow/change_status.html"
    view_title = _(u'Skift status')

    def form_valid(self, form):
        response = super(ChangeVisitStatusView, self).form_valid(
            form
        )
        status = form.cleaned_data['workflow_status']
        if status == Visit.WORKFLOW_STATUS_PLANNED:
            # Booking is planned
            self.object.autosend(
                EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE
            )
        if status == Visit.WORKFLOW_STATUS_CANCELLED:
            # Booking is cancelled
            self.object.autosend(
                EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED
            )
        return response


class ChangeVisitResponsibleView(AutologgerMixin, UpdateWithCancelView):
    model = MultiProductVisit
    form_class = ChangeVisitResponsibleForm
    template_name = "booking/workflow/change_responsible.html"
    view_title = _(u'Redigér besøgsansvarlig')


class ChangeVisitTeachersView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitTeachersForm
    template_name = "booking/workflow/change_teachers.html"
    view_title = _(u'Redigér undervisere')

    def get_context_data(self, **kwargs):
        context = {}
        context['comments'] = {
            user.id: [
                {
                    'text': comment.text,
                    'time': formats.date_format(
                        timezone.localtime(comment.time),
                        "DATETIME_FORMAT"
                    )
                }
                for comment in self.object.get_comments(user).all()
            ]
            for user in self.get_form().base_fields['teachers'].queryset.all()
        }
        context['can_send_emails'] = self.object.autosend_enabled(
            EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED
        )
        context['email_template_name'] = EmailTemplateType.get_name(
            EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED
        )
        context.update(kwargs)
        return super(ChangeVisitTeachersView, self).\
            get_context_data(**context)

    # When the status or teacher list changes, autosend emails
    def form_valid(self, form):
        old = self.get_object()
        old_teachers = set([x for x in old.teachers.all()])

        response = super(
            ChangeVisitTeachersView, self
        ).form_valid(form)

        if form.cleaned_data.get('send_emails', False):
            new_teachers = self.object.teachers.all()
            recipients = [
                teacher
                for teacher in new_teachers
                if teacher not in old_teachers
            ]
            if len(recipients) > 0:
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED,
                    recipients,
                    True
                )

        return response


class ChangeVisitHostsView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitHostsForm
    template_name = "booking/workflow/change_hosts.html"
    view_title = _(u'Redigér værter')

    def get_context_data(self, **kwargs):
        context = {}
        context['comments'] = {
            user.id: [
                {
                    'text': comment.text,
                    'time': formats.date_format(
                        timezone.localtime(comment.time),
                        "DATETIME_FORMAT"
                    )
                }
                for comment in self.object.get_comments(user).all()
                ]
            for user in self.get_form().base_fields['hosts'].queryset.all()
            }
        context['can_send_emails'] = self.object.autosend_enabled(
            EmailTemplateType.NOTIFY_HOST__ASSOCIATED
        )
        context['email_template_name'] = EmailTemplateType.get_name(
            EmailTemplateType.NOTIFY_HOST__ASSOCIATED
        )
        context.update(kwargs)
        return super(ChangeVisitHostsView, self).\
            get_context_data(**context)

    # When the status or host list changes, autosend emails
    def form_valid(self, form):
        old = self.get_object()
        old_hosts = set([x for x in old.hosts.all()])

        response = super(ChangeVisitHostsView, self).form_valid(form)

        if form.cleaned_data.get('send_emails', False):
            new_hosts = self.object.hosts.all()
            recipients = [
                host
                for host in new_hosts
                if host not in old_hosts
            ]
            if len(recipients) > 0:
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplateType.NOTIFY_HOST__ASSOCIATED,
                    recipients,
                    True
                )

        return response


class ChangeVisitRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitRoomsForm
    template_name = "booking/workflow/change_rooms.html"
    view_title = _(u'Redigér lokaler')

    def get_context_data(self, **kwargs):
        context = {}
        context.update(kwargs)

        context['allrooms'] = [
            {
                'id': x.pk,
                'locality_id': x.locality.pk if x.locality else None,
                'name': x.name_with_locality
            }
            for x in Room.objects.all()
        ]

        context['rooms'] = self.object.rooms.all()

        locality = self.object.product.locality
        unit = self.object.product.organizationalunit

        context['locality_choices'] = [(None, "---------")] + \
            [
                (x.id, x.name_and_address,
                 locality is not None and x.id == locality.id)
                for x in Locality.objects.order_by(
                    # Sort stuff where unit is null last
                    OrderBy(
                        Q(organizationalunit__isnull=False),
                        descending=True
                    ),
                    # Sort localities belong to current unit first
                    OrderBy(Q(organizationalunit=unit), descending=True),
                    # Lastly, sort by name
                    "name"
                )
            ]

        return super(
            ChangeVisitRoomsView, self
        ).get_context_data(**context)

    def form_valid(self, form):
        self.object = form.save()

        self.save_rooms()
        result = super(ChangeVisitRoomsView, self).form_valid(form)
        return result

    def save_rooms(self):
        # This code is more or less the same as EditProductView.save_rooms()
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


class ChangeVisitCommentsView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitCommentsForm
    template_name = "booking/workflow/change_comments.html"
    view_title = _(u'Redigér kommentarer')


class ChangeVisitEvalView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = ChangeVisitEvalForm
    template_name = "booking/workflow/change_eval_link.html"
    view_title = _(u'Redigér evalueringslink')


class VisitAddLogEntryView(VisitBreadcrumbMixin, FormView):
    model = Visit
    form_class = VisitAddLogEntryForm
    template_name = "booking/workflow/add_logentry.html"
    object = None
    view_title = _(u'Tilføj log-post')

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.model.objects.get(pk=kwargs['pk'])
        except:
            raise Http404("Visit not found")

        return super(VisitAddLogEntryView, self).dispatch(
            request, *args, **kwargs
        )

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            return redirect(self.get_success_url())
        else:
            return super(VisitAddLogEntryView, self).post(
                request, *args, **kwargs
            )

    def get_context_data(self, **kwargs):
        context = {'object': self.object}
        context.update(kwargs)
        return super(VisitAddLogEntryView, self).get_context_data(**context)

    def form_valid(self, form):
        log_action(
            self.request.user,
            self.object,
            LOGACTION_MANUAL_ENTRY,
            form.cleaned_data['new_comment']
        )
        return super(VisitAddLogEntryView, self).form_valid(form)

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.pk])


class VisitAddCommentView(VisitAddLogEntryView):
    model = Visit
    form_class = VisitAddCommentForm
    template_name = "booking/workflow/add_comment.html"
    object = None
    view_title = _(u'Tilføj kommentar')

    def form_valid(self, form):
        self.object.add_comment(
            self.request.user,
            form.cleaned_data['new_comment']
        )
        return super(VisitAddLogEntryView, self).form_valid(form)


class ChangeVisitAutosendView(AutologgerMixin, UpdateWithCancelView):
    model = Visit
    form_class = VisitAutosendFormSet
    template_name = "booking/workflow/change_autosend.html"
    view_title = _(u'Redigér automatiske emails')

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = {}

        context['inherited'] = {
            item.template_key:
            {
                'template_key': item.template_key,
                'enabled': item.enabled,
                'days': item.days
            }
            for item in chain.from_iterable(
                product.productautosend_set.all()
                for product in self.object.real.products
            )
        }
        context['template_keys'] = list(set(
            template.key
            for template in chain.from_iterable(
                EmailTemplate.get_templates(product.organizationalunit)
                for product in self.object.real.products
            )
        ))
        if hasattr(self.object, 'product') and self.object.product is not None:
            context['organizationalunit'] = \
                self.object.product.organizationalunit
        context['autosend_enable_days'] = EmailTemplateType.get_keys(
            enable_days=True
        )
        context.update(kwargs)
        return super(ChangeVisitAutosendView, self).\
            get_context_data(**context)


class BecomeSomethingView(AutologgerMixin, VisitBreadcrumbMixin,
                          RoleRequiredMixin, FormView):
    model = Visit
    errors = None
    m2m_attribute = None
    view_title = _(u'Tilmeld rolle')
    roles = [HOST, TEACHER] + list(EDIT_ROLES)
    form_class = BecomeSomethingForm
    notify_mail_template_key = None
    object = None

    ERROR_NONE_NEEDED = _(
        u"Det valgte besøg har ikke behov for flere personer i den " +
        u"givne rolle"
    )
    ERROR_WRONG_ROLE = _(
        u"Du har ikke den rette rolle til at bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede blevet tildelt den givne rolle"
    )

    def get_form(self, *args, **kwargs):
        form = super(BecomeSomethingView, self).get_form(*args, **kwargs)
        rr = form.fields['resourcerequirements']
        if self.get_object().product.is_resource_controlled:
            rr.queryset = self.matching_requirements()
            rr.label_from_instance = lambda x: x.resource_pool.name
            if self.request.method == "GET":
                rr.initial = [x[0] for x in rr.choices]
        else:
            rr.queryset = booking.models.ResourceRequirement.objects.none()
        return form

    def needs_more(self):
        raise NotImplementedError

    def is_right_role(self):
        raise NotImplementedError

    def get_object(self, queryset=None):
        if not self.object:
            self.object = self.model.objects.get(pk=self.kwargs.get("pk"))

            # Store state for autologger
            self._old_state = self._as_state(self.object)

        return self.object

    def matching_requirements(self):
        user = self.request.user
        resource = user.userprofile.get_resource()
        if resource:
            visit = self.get_object()
            return booking.models.ResourceRequirement.objects.filter(
                product__eventtime__visit=visit,
                resource_pool__resources=resource,
            ).exclude(
                visitresource__resource=resource,
                visitresource__visit=visit
            )
        else:
            return booking.models.ResourceRequirements.objects.none()

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        context = {}
        context['object'] = obj
        context.update(kwargs)
        return super(BecomeSomethingView, self).get_context_data(**context)

    def is_valid(self):
        if self.errors is None:
            self.errors = []

            # Are we the right role?
            if not self.is_right_role():
                self.errors.append(self.ERROR_WRONG_ROLE)

            # Do the event need more of the given role?
            if self.object.product.is_resource_controlled:
                if self.matching_requirements().count() == 0:
                    self.errors.append(self.ERROR_NONE_NEEDED)
            else:
                if not self.needs_more():
                    self.errors.append(self.ERROR_NONE_NEEDED)

                # Is the current user already registered?
                qs = getattr(self.object, self.m2m_attribute).filter(
                    pk=self.request.user.pk
                )
                if qs.exists():
                    self.errors.append(self.ERROR_ALREADY_REGISTERED)

        return len(self.errors) == 0

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if self.is_valid():

            # Process the form to get cleaned_data, but ignore any error.
            form.is_valid()

            if 'comment' in form.cleaned_data:
                comment = form.cleaned_data['comment']
                if comment:
                    self.object.add_comment(
                        request.user,
                        comment
                    )

            if request.POST.get("cancel"):
                if isinstance(self, DeclineHostView):
                    self.object.hosts_rejected.add(request.user)
                if isinstance(self, DeclineTeacherView):
                    self.object.teachers_rejected.add(request.user)
                self.object.save()

            elif request.POST.get("confirm"):
                if self.object.product.is_resource_controlled:
                    resource = self.request.user.userprofile.get_resource()
                    for x in form.cleaned_data['resourcerequirements']:
                        vr = booking.models.VisitResource(
                            visit=self.object,
                            resource=resource,
                            resource_requirement=x
                        )
                        vr.save()
                else:
                    # Add user to the specified m2m relation
                    getattr(self.object, self.m2m_attribute).add(request.user)

                # Notify the user about the association
                if self.notify_mail_template_key:
                    self.object.autosend(
                        self.notify_mail_template_key,
                        [request.user],
                        True
                    )

            self._log_changes()

        return self.get(request, *args, **kwargs)

    def render_with_error(self, error, request, *args, **kwargs):
        self.errors.append(error)
        return self.get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.pk])


class BecomeTeacherView(BecomeSomethingView):
    m2m_attribute = "teachers"
    template_name = "booking/workflow/become_teacher.html"
    view_title = _(u'Tilmeld som underviser')
    notify_mail_template_key = EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere undervisere")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen underviser for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede underviser på besøget"
    )

    def needs_more(self):
        return self.object.needs_teachers

    def is_right_role(self):
        return self.request.user.userprofile.is_teacher


class DeclineTeacherView(BecomeSomethingView):
    m2m_attribute = "teachers"
    template_name = "booking/workflow/decline_teacher.html"
    view_title = _(u'Tilmeld som underviser')
    notify_mail_template_key = EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere undervisere")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen underviser for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede underviser på besøget"
    )

    def needs_more(self):
        return self.object.needs_teachers

    def is_right_role(self):
        return self.request.user.userprofile.is_teacher


class BecomeHostView(BecomeSomethingView):
    m2m_attribute = "hosts"
    template_name = "booking/workflow/become_host.html"
    view_title = _(u'Tilmeld som vært')
    notify_mail_template_key = EmailTemplateType.NOTIFY_HOST__ASSOCIATED

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere værter")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen vært for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede vært på besøget"
    )

    def needs_more(self):
        return self.object.needs_hosts

    def is_right_role(self):
        return self.request.user.userprofile.is_host


class DeclineHostView(BecomeSomethingView):
    m2m_attribute = "hosts"
    template_name = "booking/workflow/decline_host.html"
    view_title = _(u'Tilmeld som vært')
    notify_mail_template_key = EmailTemplateType.NOTIFY_HOST__ASSOCIATED

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere værter")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen vært for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede vært på besøget"
    )

    def needs_more(self):
        return self.object.needs_hosts

    def is_right_role(self):
        return self.request.user.userprofile.is_host


class ResetVisitChangesView(UpdateWithCancelView):
    model = Visit
    form_class = ResetVisitChangesForm
    template_name = "booking/workflow/change_changes_marker.html"
    view_title = _(u'Nulstil markør for nylige ændringer')

    def form_valid(self, form):
        self.object = form.save()
        self.object.last_workflow_update = timezone.now()
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
