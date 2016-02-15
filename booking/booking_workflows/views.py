# -*- coding: utf-8 -*-

from django.shortcuts import redirect
from django.views.generic import UpdateView
from booking.booking_workflows.forms import ChangeBookingStatusForm
from booking.booking_workflows.forms import ChangeBookingTeachersForm
from booking.booking_workflows.forms import ChangeBookingHostsForm
from booking.booking_workflows.forms import ChangeBookingRoomsForm
from booking.models import Booking
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


class ChangeBookingRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = Booking
    form_class = ChangeBookingRoomsForm
    template_name = "booking/workflow/change_rooms.html"
