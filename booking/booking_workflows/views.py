# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.views.defaults import bad_request
from django.views.generic import UpdateView, FormView

from booking.booking_workflows.forms import ChangeBookingStatusForm
from booking.booking_workflows.forms import ChangeBookingTeachersForm
from booking.booking_workflows.forms import ChangeBookingHostsForm
from booking.booking_workflows.forms import ChangeBookingRoomsForm
from booking.booking_workflows.forms import ChangeBookingCommentsForm
from booking.booking_workflows.forms import BookingAddLogEntryForm
from booking.models import Booking, KUEmailMessage, EmailTemplate, \
    LOGACTION_MAIL_SENT
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


class ChangeBookingStatusView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingStatusForm
    template_name = "booking/workflow/change_status.html"


class ChangeBookingTeachersView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingTeachersForm
    template_name = "booking/workflow/change_teachers.html"


class ChangeBookingHostsView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingHostsForm
    template_name = "booking/workflow/change_hosts.html"

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            booking = Booking.objects.get(pk=pk)
        else:
            return bad_request(request)
        KUEmailMessage.send_email(  # Todo: check these templates!
            EmailTemplate.NOTIFY_HOST__ASSOCIATED,
            {
                'booking': booking,
                'visit': booking.visit,
                'booker': booking.booker,
                'user': request.user,
                'action_flag': LOGACTION_MAIL_SENT,
                'message': unicode(EmailTemplate.key_choices[
                    EmailTemplate.NOTIFY_HOST__ASSOCIATED
                ][1]),
            },
            list(booking.visit.contact_persons.all()),
            booking.visit.unit
        )

        return super(ChangeBookingHostsView, self).post(
            request=request,
            *args,
            **kwargs
        )


class ChangeBookingRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingRoomsForm
    template_name = "booking/workflow/change_rooms.html"

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            booking = Booking.objects.get(pk=pk)
        else:
            return bad_request(request)
        KUEmailMessage.send_email(  # Todo: check these templates!
            EmailTemplate.NOTIFY_HOST__REQ_ROOM,
            {
                'booking': booking,
                'visit': booking.visit,
                'booker': booking.booker,
                'user': request.user,
                'action_flag': LOGACTION_MAIL_SENT,
                'message': unicode(EmailTemplate.key_choices[
                    EmailTemplate.NOTIFY_HOST__REQ_ROOM
                ][1]),
            },
            list(booking.visit.contact_persons.all()),
            booking.visit.unit
        )

        return super(ChangeBookingRoomsView, self).post(
            request=request,
            *args,
            **kwargs
        )


class ChangeBookingCommentsView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingCommentsForm
    template_name = "booking/workflow/change_comments.html"


class BookingAddLogEntryView(FormView):
    model = Booking
    form_class = BookingAddLogEntryForm
    template_name = "booking/workflow/add_logentry.html"
    booking = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.booking = self.model.objects.get(pk=kwargs['pk'])
        except:
            raise Http404("Booking not found")

        return super(BookingAddLogEntryView, self).dispatch(
            request, *args, **kwargs
        )

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            self.object = self.get_object()
            return redirect(self.get_success_url())
        else:
            return super(BookingAddLogEntryView, self).post(
                request, *args, **kwargs
            )

    def get_context_data(self, **kwargs):
        return super(BookingAddLogEntryView, self).get_context_data(
            booking=self.booking,
            **kwargs
        )

    def form_valid(self, form):
        log_action(
            self.request.user,
            self.booking,
            LOGACTION_MANUAL_ENTRY,
            form.cleaned_data['new_comment']
        )
        return super(BookingAddLogEntryView, self).form_valid(form)

    def get_success_url(self):
        return reverse('booking-view', args=[self.booking.pk])
