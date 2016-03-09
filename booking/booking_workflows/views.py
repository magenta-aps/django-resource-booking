# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import UpdateView, FormView
from booking.booking_workflows.forms import ChangeVisitOccurrenceStatusForm, \
    VisitOccurrenceAutosendFormSet
from booking.booking_workflows.forms import ChangeVisitOccurrenceTeachersForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceHostsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceRoomsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceCommentsForm
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


class ChangeVisitOccurrenceStartTimeView(AutologgerMixin,
                                         UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStartTimeForm
    template_name = "booking/workflow/change_starttime.html"


class ChangeVisitOccurrenceStatusView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStatusForm
    template_name = "booking/workflow/change_status.html"

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


class ChangeVisitOccurrenceHostsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceHostsForm
    template_name = "booking/workflow/change_hosts.html"

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
            if len(recipients):
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplate.NOTIFY_HOST__ASSOCIATED,
                    recipients,
                    True
                )
        return response


class ChangeVisitOccurrenceRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceRoomsForm
    template_name = "booking/workflow/change_rooms.html"


class ChangeVisitOccurrenceCommentsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceCommentsForm
    template_name = "booking/workflow/change_comments.html"


class VisitOccurrenceAddLogEntryView(FormView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAddLogEntryForm
    template_name = "booking/workflow/add_logentry.html"
    object = None

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
        context.update(kwargs)
        return super(ChangeVisitOccurrenceAutosendView, self).\
            get_context_data(**context)
