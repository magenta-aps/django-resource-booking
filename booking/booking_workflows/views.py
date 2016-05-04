# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView, FormView, DetailView
from booking.booking_workflows.forms import ChangeVisitOccurrenceStatusForm
from booking.booking_workflows.forms import VisitOccurrenceAutosendFormSet
from booking.booking_workflows.forms import ChangeVisitOccurrenceTeachersForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceHostsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceRoomsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceCommentsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceEvalForm
from booking.booking_workflows.forms import VisitOccurrenceAddLogEntryForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceStartTimeForm
from booking.models import VisitOccurrence
from booking.models import EmailTemplate
from booking.models import LOGACTION_MANUAL_ENTRY
from booking.models import log_action
from booking.views import AutologgerMixin


class UpdateWithCancelView(UpdateView):
    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            self.object = self.get_object()
            return redirect(self.get_success_url())
        else:
            return super(UpdateWithCancelView, self).post(
                request, *args, **kwargs
            )

    view_title = _(u'opdater')

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {
                'url': reverse('visit-occ-search'),
                'text': _(u'Søg i besøg')
            },
            {
                'url': reverse('visit-occ-view', args=[self.object.pk]),
                'text': _(u'Besøg #%s') % self.object.pk
            },
            {'text': self.view_title},
        ]
        context.update(kwargs)
        return super(UpdateWithCancelView, self).get_context_data(**context)


class ChangeVisitOccurrenceStartTimeView(AutologgerMixin,
                                         UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStartTimeForm
    template_name = "booking/workflow/change_starttime.html"
    view_title = _(u'Redigér tidspunkt')


class ChangeVisitOccurrenceStatusView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStatusForm
    template_name = "booking/workflow/change_status.html"
    view_title = _(u'Redigér status')

    def form_valid(self, form):
        response = super(ChangeVisitOccurrenceStatusView, self).form_valid(
            form
        )
        status = form.cleaned_data['workflow_status']
        if status == VisitOccurrence.WORKFLOW_STATUS_PLANNED:
            # Booking is planned
            self.object.autosend(EmailTemplate.NOTIFY_ALL__BOOKING_COMPLETE)
        if status == VisitOccurrence.WORKFLOW_STATUS_CANCELLED:
            # Booking is cancelled
            self.object.autosend(EmailTemplate.NOTIFY_ALL__BOOKING_CANCELED)
        return response


class ChangeVisitOccurrenceTeachersView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceTeachersForm
    template_name = "booking/workflow/change_teachers.html"
    view_title = _(u'Redigér undervisere')


class ChangeVisitOccurrenceHostsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceHostsForm
    template_name = "booking/workflow/change_hosts.html"
    view_title = _(u'Redigér værter')

    # When the status or host list changes, autosend emails
    def form_valid(self, form):
        old = self.get_object()
        response = super(ChangeVisitOccurrenceHostsView, self).form_valid(form)
        if form.cleaned_data['host_status'] == VisitOccurrence.STATUS_OK:
            new_hosts = self.object.hosts.all()
            if old.host_status != VisitOccurrence.STATUS_OK:
                # Status changed from not-ok to ok, notify all hosts
                recipients = new_hosts
            else:
                # Status was also ok before, send message to hosts
                # that weren't there before
                recipients = [
                    host
                    for host in new_hosts
                    if host not in old.hosts.all()
                ]
            if len(recipients) > 0:
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplate.occurrence_added_host_key,
                    recipients,
                    True
                )
        return response


class ChangeVisitOccurrenceRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceRoomsForm
    template_name = "booking/workflow/change_rooms.html"
    view_title = _(u'Redigér lokaler')


class ChangeVisitOccurrenceCommentsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceCommentsForm
    template_name = "booking/workflow/change_comments.html"
    view_title = _(u'Redigér kommentarer')


class ChangeVisitOccurrenceEvalView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceEvalForm
    template_name = "booking/workflow/change_eval_link.html"
    view_title = _(u'Redigér evalueringslink')


class VisitOccurrenceAddLogEntryView(FormView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAddLogEntryForm
    template_name = "booking/workflow/add_logentry.html"
    object = None
    view_title = _(u'Tilføj log-post')

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.model.objects.get(pk=kwargs['pk'])
        except:
            raise Http404("VisitOccurrence not found")

        return super(VisitOccurrenceAddLogEntryView, self).dispatch(
            request, *args, **kwargs
        )

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            return redirect(self.get_success_url())
        else:
            return super(VisitOccurrenceAddLogEntryView, self).post(
                request, *args, **kwargs
            )

    def get_context_data(self, **kwargs):
        return super(VisitOccurrenceAddLogEntryView, self).get_context_data(
            object=self.object,
            **kwargs
        )

    def form_valid(self, form):
        log_action(
            self.request.user,
            self.object,
            LOGACTION_MANUAL_ENTRY,
            form.cleaned_data['new_comment']
        )
        return super(VisitOccurrenceAddLogEntryView, self).form_valid(form)

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])


class ChangeVisitOccurrenceAutosendView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAutosendFormSet
    template_name = "booking/workflow/change_autosend.html"
    view_title = _(u'Redigér automatiske emails')

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = {}
        context['inherited'] = {
            item.template_key:
            {
                'template_key': item.template_key,
                'enabled': item.enabled,
                'days': item.days
            }
            for item in self.object.visit.visitautosend_set.all()
        }
        context['template_keys'] = list(set(
            template.key
            for template in EmailTemplate.get_templates(self.object.visit.unit)
        ))
        context['unit'] = self.object.visit.unit
        context['autosend_enable_days'] = EmailTemplate.enable_days
        context.update(kwargs)
        return super(ChangeVisitOccurrenceAutosendView, self).\
            get_context_data(**context)


class BecomeSomethingView(AutologgerMixin, DetailView):
    model = VisitOccurrence
    errors = None
    m2m_attribute = None

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

    def needs_more(self):
        raise NotImplementedError

    def is_right_role(self):
        raise NotImplementedError

    def is_valid(self):
        if self.errors is None:
            self.errors = []
            # Are we the right role?
            if not self.is_right_role():
                self.errors.append(self.ERROR_WRONG_ROLE)

            # Do the event need more of the given role?
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
        if request.POST.get("cancel"):
            return redirect(self.get_success_url())
        elif request.POST.get("confirm"):
            if self.is_valid():
                # Add user to the specified m2m relation
                getattr(self.object, self.m2m_attribute).add(request.user)
                self._log_changes()

        return self.get(request, *args, **kwargs)

    def render_with_error(self, error, request, *args, **kwargs):
        self.errors.append(error)
        return self.get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])


class BecomeTeacherView(BecomeSomethingView):
    m2m_attribute = "teachers"
    template_name = "booking/workflow/become_teacher.html"

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
