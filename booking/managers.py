from datetime import time, timedelta
from django.utils import timezone

from django.db import models
from django.db.models import Q, Max
from django.contrib.contenttypes.models import ContentType


class VisitQuerySet(models.QuerySet):

    @staticmethod
    def prefetch(query, **extra_related):
        return query.select_related(
            "multiproductvisit",
            "eventtime__product",
            *extra_related.get('to_one', [])
        ).prefetch_related(
            "multi_master",
            *extra_related.get('to_many', [])
        )

    def p(self):
        return VisitQuerySet.prefetch(self)

    def active_qs(self):
        return VisitQuerySet.prefetch(self.exclude(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_CANCELLED,
                self.model.WORKFLOW_STATUS_REJECTED,
            ]
        ))

    def being_planned(self, **kwargs):
        return VisitQuerySet.prefetch(self.filter(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_BEING_PLANNED,
                self.model.WORKFLOW_STATUS_AUTOASSIGN_FAILED,
                self.model.WORKFLOW_STATUS_REJECTED,
            ],
            **kwargs
        ))

    def planned_queryset(self, **kwargs):
        return VisitQuerySet.prefetch(self.filter(
            workflow_status__in=[
                self.model.WORKFLOW_STATUS_PLANNED,
                self.model.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
                self.model.WORKFLOW_STATUS_CONFIRMED,
                self.model.WORKFLOW_STATUS_REMINDED,
            ]
        ).filter(**kwargs))

    def unit_filter(self, unit_qs, **kwargs):
        return VisitQuerySet.prefetch(self.filter(
            Q(eventtime__product__organizationalunit__in=unit_qs) | Q(
                **{
                    "multiproductvisit__subvisit__is_multi_sub": True,
                    "multiproductvisit__subvisit__eventtime__"
                    "product__organizationalunit__in": unit_qs,
                }
            ),
            **kwargs
        ))

    def with_product_types(self, product_types=None, **kwargs):
        if product_types is None:
            return self
        return (
            VisitQuerySet.prefetch(
                self.filter(
                    Q(
                        multiproductvisit__isnull=True,
                        eventtime__product__type__in=product_types,
                    )
                    | Q(
                        multiproductvisit__isnull=False,
                        multiproductvisit__subvisit__eventtime__product__type__in=product_types,
                        multiproductvisit__subvisit__is_multi_sub=True,
                    )
                ),
                **kwargs
            )
        ).distinct()

    def get_latest_created(self):
        return VisitQuerySet.prefetch(
            self.order_by("-statistics__created_time")
        )

    def get_latest_updated(self):
        return VisitQuerySet.prefetch(
            self.order_by("-statistics__updated_time")
        )

    def get_latest_displayed(self):
        return VisitQuerySet.prefetch(
            self.order_by("-statistics__visited_time")
        )

    def get_latest_booked(self, **kwargs):
        return VisitQuerySet.prefetch(
            self.filter(bookings__isnull=False, **kwargs).order_by(
                "-bookings__statistics__created_time"
            )
        )

    def get_todays_visits(self):
        return self.get_occurring_on_date(timezone.now())

    def get_occurring_at_time(self, time, **kwargs):
        # Return the visits that take place exactly at this time
        # Meaning they begin before the queried time and end after the time
        return VisitQuerySet.prefetch(self.filter(
            eventtime__start__lte=time,
            eventtime__end__gt=time,
            is_multi_sub=False,
            **kwargs
        ))

    def get_occurring_on_date(self, datetime):
        # Convert datetime object to date-only for current timezone
        date = timezone.localtime(datetime).date()

        # A visit happens on a date if it starts before the
        # end of the day and ends after the beginning of the day
        min_date = datetime.combine(date, time.min)
        max_date = datetime.combine(date, time.max)

        return VisitQuerySet.prefetch(self.filter(
            eventtime__start__lte=max_date, is_multi_sub=False
        ).filter(
            Q(eventtime__end__gte=min_date) |
            (Q(eventtime__end__isnull=True) &
                Q(eventtime__start__gt=min_date))
        ))

    def get_recently_held(self, time=None, **kwargs):
        if not time:
            time = timezone.now()

        return (
            VisitQuerySet.prefetch(
                self.filter(
                    workflow_status__in=[
                        self.model.WORKFLOW_STATUS_EXECUTED,
                        self.model.WORKFLOW_STATUS_EVALUATED,
                    ],
                    eventtime__start__isnull=False,
                    is_multi_sub=False,
                    **kwargs
                ).filter(
                    Q(eventtime__end__lt=time) | (
                        Q(eventtime__end__isnull=True) &
                        Q(eventtime__start__lt=time + timedelta(hours=12))
                    )
                ).order_by("-eventtime__end")
            )
        )


class BookingQuerySet(models.QuerySet):

    @staticmethod
    def prefetch(query):
        return query.select_related(
            "booker",
            "visit",
        )

    def p(self):
        return BookingQuerySet.prefetch(self)

    def get_latest_created(self):
        return self.order_by("-statistics__created_time")

    def get_latest_updated(self):
        return self.order_by("-statistics__updated_time")

    def get_latest_displayed(self):
        return self.order_by("-statistics__visited_time")


class ProductQuerySet(models.QuerySet):
    def filter_public_bookable(self):
        from booking.models import EventTime, Visit

        nonblocked = EventTime.NONBLOCKED_RESOURCE_STATES
        resource_controlled = [
            self.model.TIME_MODE_RESOURCE_CONTROLLED,
            self.model.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN,
        ]
        return self.filter(
            Q(time_mode=self.model.TIME_MODE_GUEST_SUGGESTED) | Q(
                # Only stuff that can be booked
                eventtime__bookable=True,
                # In the future
                eventtime__start__gt=timezone.now(),
                # Only include stuff with bookable states
                eventtime__visit__workflow_status__in=Visit.BOOKABLE_STATES,
            ) & Q(
                # Either not resource controlled
                (~Q(time_mode__in=resource_controlled)) |
                # Or resource-controlled with nonblocked eventtimes
                Q(
                    time_mode__in=resource_controlled,
                    eventtime__resource_status__in=nonblocked,
                )
            )
        ).filter(state=self.model.ACTIVE)

    def get_latest_created(self, user=None):
        qs = self.filter(statistics__isnull=False)

        if user and not user.is_authenticated():
            qs = qs.filter_public_bookable() \
                .distinct("pk", "statistics__created_time").only('pk')

        return qs.order_by("-statistics__created_time", "pk")

    def get_latest_updated(self, user=None):
        qs = self.filter(statistics__isnull=False)

        if user and not user.is_authenticated():
            qs = qs.filter_public_bookable() \
                .distinct("pk", "statistics__updated_time").only('pk')

        return qs.order_by("-statistics__updated_time", "pk")

    def get_latest_displayed(self, user=None):
        qs = self.filter(statistics__isnull=False)

        if user and not user.is_authenticated():
            qs = qs.filter_public_bookable() \
                .distinct("pk", "statistics__updated_time").only('pk')

        return qs.order_by("-statistics__visited_time", "pk")

    def get_latest_booked(self, user=None):
        qs = self.filter(
            eventtime__visit__bookings__statistics__created_time__isnull=False
        )

        if user and not user.is_authenticated():
            qs = qs.filter_public_bookable().distinct().only("pk")

        return qs.annotate(
            latest_booking=Max(
                "eventtime__visit__bookings__statistics__created_time"
            )
        ).order_by("-latest_booking", "pk")


class SchoolQuerySet(models.QuerySet):
    def search(self, query, type=None):
        qs = self.filter(name__icontains=query)
        if type is not None:
            try:
                type = int(type)
                if type in [id for id, title in self.model.type_choices]:
                    qs = qs.filter(type=type)
            except ValueError:
                pass
        return qs


class KUEmailMessageQuerySet(models.QuerySet):
    def get_by_instance(self, instance):
        return self.filter(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
        )


class SurveyXactEvaluationGuestQuerySet(models.QuerySet):
    def filter_visit(self, visit):
        return self.filter(guest__booking__visit=visit)

    def filter_status(self, status):
        return self.filter(status=status)
