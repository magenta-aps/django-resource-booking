# encoding: utf-8
import datetime

from booking.resource_based.models import EventTime
from django.utils import timezone
from django.views.generic import CreateView
from django.views.generic import TemplateView


class CalendarView(TemplateView):
    template_name = 'calendar.html'

    def get_context_data(self, **kwargs):

        input_month = self.request.GET.get("month")
        if input_month and len(input_month) == 6:
            start_year = int(input_month[:4])
            start_month = int(input_month[4:])
        else:
            now = timezone.now()
            start_year = now.year
            start_month = now.month

        first_of_the_month = datetime.date(start_year, start_month, 1)

        start_date = first_of_the_month

        # Make start date the monday before the first in the month
        if start_date.isoweekday() != 1:
            start_date = start_date - datetime.timedelta(
                days=start_date.isoweekday() - 1
            )

        # Make end date in next month
        end_date = first_of_the_month + datetime.timedelta(31)
        # And subtract the number of days within that month so we get last
        # day of current month
        end_date = end_date - datetime.timedelta(days=end_date.day)
        # And then add days to get the next sunday
        if end_date.isoweekday() != 7:
            end_date = end_date + datetime.timedelta(
                days=7 - end_date.isoweekday()
            )

        current_date = start_date
        week = []
        weeks = []
        while current_date <= end_date:
            week.append({
                'date': current_date,
                'events': []
            })
            if len(week) == 7:
                weeks.append(week)
                week = []
            current_date = current_date + datetime.timedelta(days=1)

        return super(CalendarView, self).get_context_data(
            month=first_of_the_month,
            next_month=first_of_the_month + datetime.timedelta(days=31),
            prev_month=first_of_the_month - datetime.timedelta(days=1),
            calendar_weeks=weeks,
            **kwargs
        )


class CreateEventTimeView(CreateView):
    model = EventTime
    fields = []
