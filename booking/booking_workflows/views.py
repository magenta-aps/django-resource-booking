# -*- coding: utf-8 -*-

from django.shortcuts import redirect
from django.views.defaults import bad_request
from django.views.generic import UpdateView
from booking.booking_workflows.forms import ChangeBookingStatusForm
from booking.booking_workflows.forms import ChangeBookingTeachersForm
from booking.booking_workflows.forms import ChangeBookingHostsForm
from booking.booking_workflows.forms import ChangeBookingRoomsForm
from booking.models import Booking, KUEmailMessage, EmailTemplate


class UpdateWithCancelView(UpdateView):
    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            self.object = self.get_object()
            return redirect(self.get_success_url())
        else:
            return super(UpdateWithCancelView, self).post(
                request, *args, **kwargs
            )


class ChangeBookingStatusView(UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingStatusForm
    template_name = "booking/workflow/change_status.html"


class ChangeBookingTeachersView(UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingTeachersForm
    template_name = "booking/workflow/change_teachers.html"


class ChangeBookingHostsView(UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingHostsForm
    template_name = "booking/workflow/change_hosts.html"

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            booking = Booking.objects.get(pk=pk)
        else:
            return bad_request(request)
        KUEmailMessage.send_email(
            EmailTemplate.HOSTS_CHANGED,
            {
                'booking': booking,
                'visit': booking.visit,
                'booker': booking.booker
            },
            list(booking.visit.contact_persons.all()),
            booking.visit.unit
        )

        return super(ChangeBookingHostsView, self).post(
            request=request,
            *args,
            **kwargs
        )


class ChangeBookingRoomsView(UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingRoomsForm
    template_name = "booking/workflow/change_rooms.html"

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is not None:
            booking = Booking.objects.get(pk=pk)
        else:
            return bad_request(request)
        KUEmailMessage.send_email(
            EmailTemplate.ROOMS_CHANGED,
            {
                'booking': booking,
                'visit': booking.visit,
                'booker': booking.booker
            },
            list(booking.visit.contact_persons.all()),
            booking.visit.unit
        )

        return super(ChangeBookingRoomsView, self).post(
            request=request,
            *args,
            **kwargs
        )
