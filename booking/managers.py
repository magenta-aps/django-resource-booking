from datetime import time, timedelta
from django.utils import timezone

from django.db import models
from django.db.models import Q


class VisitQuerySet(models.QuerySet):
    def active_qs(self):
        return self.exclude(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_CANCELLED,
                self.model.WORKFLOW_STATUS_REJECTED,
            ]
        )

    def being_planned(self, **kwargs):
        return self.filter(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_BEING_PLANNED,
                self.model.WORKFLOW_STATUS_AUTOASSIGN_FAILED,
                self.model.WORKFLOW_STATUS_REJECTED,
            ],
            **kwargs
        )

    def planned_queryset(self, **kwargs):
        return self.filter(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_PLANNED,
                self.model.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
                self.model.WORKFLOW_STATUS_CONFIRMED,
                self.model.WORKFLOW_STATUS_REMINDED,
            ]
        ).filter(**kwargs)

    def unit_filter(self, unit_qs, **kwargs):
        return self.filter(
            Q(eventtime__product__organizationalunit__in=unit_qs) | Q(**{
                "multiproductvisit__subvisit__is_multi_sub": True,
                "multiproductvisit__subvisit__eventtime__"
                "product__organizationalunit__in": unit_qs,
            }),
            **kwargs
        )

    def with_product_types(self, product_types=None, **kwargs):
        if product_types is None:
            return self
        return (
            self.filter(
                multiproductvisit__isnull=True,
                eventtime__product__type__in=product_types,
            ) | self.filter(
                multiproductvisit__isnull=False,
                multiproductvisit__subvisit__in=self.model.objects.filter(
                    eventtime__product__type__in=product_types,
                    is_multi_sub=True,
                ),
                **kwargs
            )
        ).distinct()

    def get_latest_created(self):
        return self.order_by("-statistics__created_time")

    def get_latest_updated(self):
        return self.order_by("-statistics__updated_time")

    def get_latest_displayed(self):
        return self.order_by("-statistics__visited_time")

    def get_latest_booked(self, **kwargs):
        return self.filter(bookings__isnull=False, **kwargs).order_by(
            "-bookings__statistics__created_time"
        )

    def get_todays_visits(self):
        return self.get_occurring_on_date(timezone.now())

    def get_occurring_at_time(self, time, **kwargs):
        # Return the visits that take place exactly at this time
        # Meaning they begin before the queried time and end after the time
        return self.filter(
            eventtime__start__lte=time,
            eventtime__end__gt=time,
            is_multi_sub=False,
            **kwargs
        )

    def get_occurring_on_date(self, datetime):
        # Convert datetime object to date-only for current timezone
        date = timezone.localtime(datetime).date()

        # A visit happens on a date if it starts before the
        # end of the day and ends after the beginning of the day
        min_date = datetime.combine(date, time.min)
        max_date = datetime.combine(date, time.max)

        return self.filter(
            eventtime__start__lte=max_date, is_multi_sub=False
        ).filter(
            Q(eventtime__end__gte=min_date) | (
                Q(eventtime__end__isnull=True) & Q(
                    eventtime__start__gt=min_date)
            )
        )

    def get_recently_held(self, time=None, **kwargs):
        if not time:
            time = timezone.now()

        return (
            self.filter(
                workflow_status__in=[
                    self.model.WORKFLOW_STATUS_EXECUTED,
                    self.model.WORKFLOW_STATUS_EVALUATED,
                ],
                eventtime__start__isnull=False,
                is_multi_sub=False,
                **kwargs
            )
            .filter(
                Q(eventtime__end__lt=time) | (
                    Q(eventtime__end__isnull=True) & Q(
                        eventtime__start__lt=time + timedelta(hours=12))
                )
            )
            .order_by("-eventtime__end")
        )
