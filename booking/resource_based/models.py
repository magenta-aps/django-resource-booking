# encoding: utf-8
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.deletion import SET_NULL
from django.contrib.auth import models as auth_models
from django.core.urlresolvers import reverse
from django.utils import formats
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from recurrence.fields import RecurrenceField
from booking.mixins import AvailabilityUpdaterMixin
from booking.models import Room, Visit, EmailTemplateType
from profile.constants import TEACHER, HOST, NONE

import datetime
import math
import re
import sys


class EventTime(models.Model):

    class Meta:
        verbose_name = _(u"tidspunkt")
        verbose_name_plural = _(u"tidspunkter")
        ordering = ['start', 'end']

    product = models.ForeignKey(
        "Product",
        null=True
    )

    visit = models.OneToOneField(
        "Visit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # Whether the time is publicly bookable
    bookable = models.BooleanField(
        default=True,
        verbose_name=_(u'Kan bookes')
    )

    RESOURCE_STATUS_AVAILABLE = 1
    RESOURCE_STATUS_BLOCKED = 2
    RESOURCE_STATUS_ASSIGNED = 3

    resource_status_choices = (
        (RESOURCE_STATUS_AVAILABLE, _(u"Ressourcer ledige")),
        (RESOURCE_STATUS_BLOCKED, _(u"Blokeret af manglende ressourcer")),
        (RESOURCE_STATUS_ASSIGNED, _(u"Ressourcer tildelt")),
    )
    resource_status_classes = {
        RESOURCE_STATUS_AVAILABLE: 'primary',
        RESOURCE_STATUS_BLOCKED: 'danger',
        RESOURCE_STATUS_ASSIGNED: 'success'
    }
    short_resource_status_map = {
        RESOURCE_STATUS_AVAILABLE: _('Ledige'),
        RESOURCE_STATUS_BLOCKED: _('Blokeret'),
        RESOURCE_STATUS_ASSIGNED: _('Tildelt')
    }

    NONBLOCKED_RESOURCE_STATES = [
        x[0] for x in resource_status_choices
        if x[0] != RESOURCE_STATUS_BLOCKED
    ]

    resource_status = models.IntegerField(
        choices=resource_status_choices,
        default=RESOURCE_STATUS_AVAILABLE,
        verbose_name=_(u"Ressource-status"),
    )

    start = models.DateTimeField(
        verbose_name=_(u"Starttidspunkt"),
        blank=True,
        null=True
    )
    end = models.DateTimeField(
        verbose_name=_(u"Sluttidspunkt"),
        blank=True,
        null=True
    )
    has_specific_time = models.BooleanField(
        default=True,
        verbose_name=_(u"Angivelse af tidspunkt"),
        choices=(
            (True, _(u"Både dato og tidspunkt")),
            (False, _(u"Kun dato")),
        ),
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Interne kommentarer')
    )

    has_notified_start = models.BooleanField(
        default=False
    )

    has_notified_end = models.BooleanField(
        default=False
    )

    def set_calculated_end_time(self):
        # Don't calculate if already set
        if self.end is None:
            return

        # Can not calculate end unless we have a start and a product
        if self.start is None or self.product is None:
            return

        duration = self.product.duration_in_minutes or 0

        if duration > 0:
            self.end = self.start + datetime.timedelta(minutes=duration)

    def calculated_has_specific_time(self):
        # If start time is not defined assume that it should be set with a
        # a timestamp
        if self.start is None:
            return True

        # We need to check for midnight in current timezone
        tz_start = self.start.astimezone(timezone.get_current_timezone())

        # No specific time if  start time is set to midnight and end time is
        # 24 hours later.
        return not (tz_start.hour == 0 and
                    tz_start.minute == 0 and
                    self.duration_in_minutes == 24 * 60)

    def make_visit(self, **kwargs):
        if not self.product:
            raise Exception("Can not create a visit without a product")

        if self.visit is not None:
            raise Exception(
                "Trying to create a visit for eventtime which already has one"
            )

        visit_model = EventTime.visit.field.related_model

        # Flag newly created visits as needing attention
        if "needs_attention_since" not in kwargs:
            kwargs['needs_attention_since'] = timezone.now()

        visit = visit_model(**kwargs)

        # If the product specifies no rooms are needed, set this on the
        # visit.
        if not self.product.rooms_needed:
            visit.room_status = visit_model.STATUS_NOT_NEEDED

        visit.save()

        # Copy rooms from product to the visit
        if self.product.rooms.exists():
            for x in self.product.rooms.all():
                visit.rooms.add(x)

        visit.ensure_statistics()

        self.visit = visit
        self.save()
        visit.create_inheriting_autosends()
        visit.resources_updated()

        return visit

    def update_availability(self):
        fully_assigned = True

        result = None

        if self.product is not None:
            for req in self.product.resourcerequirement_set.all():
                if hasattr(self, 'visit') and self.visit is not None:
                    assigned = self.visit.visitresource.filter(
                        resource_requirement=req
                    ).count()
                else:
                    assigned = 0

                if req.required_amount == assigned:
                    continue
                else:
                    fully_assigned = False

                if self.start and self.end and \
                        not req.has_free_resources_between(
                            self.start,
                            self.end,
                            req.required_amount - assigned
                        ):
                    result = EventTime.RESOURCE_STATUS_BLOCKED
                    break

        if result is None:
            if fully_assigned:
                result = EventTime.RESOURCE_STATUS_ASSIGNED
            else:
                result = EventTime.RESOURCE_STATUS_AVAILABLE

        if self.resource_status != result:
            self.resource_status = result
            self.save()

    @property
    def resource_status_class(self):
        return EventTime.resource_status_classes[self.resource_status]

    @property
    def short_resource_status(self):
        return EventTime.short_resource_status_map[self.resource_status]

    @property
    def resource_status_marker(self):
        if self.visit:
            link = reverse('visit-view', args=[self.visit.pk])
        else:
            link = reverse('resourcerequirement-list', args=[self.product.pk])

        return '<a href="%s" class="btn btn-%s btn-xs">%s</a>' % (
            link,
            self.resource_status_class,
            self.short_resource_status
        )

    @property
    def naive_start(self):
        if self.start:
            return timezone.make_naive(self.start)
        else:
            return self.start

    @property
    def naive_end(self):
        if self.end:
            return timezone.make_naive(self.end)
        else:
            return self.end

    @property
    def l10n_start(self):
        if self.start:
            return unicode(
                formats.date_format(self.naive_start, "SHORT_DATETIME_FORMAT")
            )
        else:
            return ''

    @property
    def l10n_end(self):
        if self.end:
            return unicode(
                formats.date_format(self.naive_end, "SHORT_DATETIME_FORMAT")
            )
        else:
            return ''

    @property
    def l10n_end_time(self):
        if self.end:
            return unicode(formats.time_format(self.naive_end))
        else:
            return ''

    @property
    def duration_in_minutes(self):
        if self.end:
            return math.floor((self.end - self.start).total_seconds() / 60)
        else:
            return 0

    @property
    def available_seats(self):
        if self.visit:
            return self.visit.available_seats
        elif self.product:
            max = self.product.maximum_number_of_visitors
            if max is None:  # No limit set
                return sys.maxint
            return max
        else:
            return 0

    @property
    def waiting_list_capacity(self):
        if self.visit:
            return self.visit.waiting_list_capacity
        elif self.product:
            fixed = self.product.fixed_waiting_list_capacity
            if fixed is not None:
                return fixed
            else:
                return self.product.waiting_list_length
        else:
            return 0

    @property
    def can_be_deleted(self):
        return not self.visit

    date_re = re.compile("^(\d{2}).(\d{2}).(\d{4})$")
    date_with_times_re = re.compile(
        "^(\d{2}).(\d{2}).(\d{4})\s+(\d{2}):(\d{2})\s+-\s+(\d{2}):(\d{2})$"
    )
    dates_re = re.compile(
        "^" +
        "(\d{2}).(\d{2}).(\d{4})" +
        "\s+-\s+" +
        "(\d{2}).(\d{2}).(\d{4})" +
        "$"
    )
    dates_with_times_re = re.compile(
        "^" +
        "(\d{2}).(\d{2}).(\d{4})\s+(\d{2}):(\d{2})" +
        "\s+-\s+" +
        "(\d{2}).(\d{2}).(\d{4})\s+(\d{2}):(\d{2})" +
        "$"
    )

    @staticmethod
    # Parses the human readable interval that is used on web pages.
    def parse_human_readable_interval(interval_str):

        match = EventTime.date_re.search(interval_str)
        if match is not None:
            dt = timezone.datetime(
                year=int(match.group(3)),
                month=int(match.group(2)),
                day=int(match.group(1))
            )
            return(
                timezone.make_aware(dt),
                timezone.make_aware(dt + datetime.timedelta(days=1)),
            )

        match = EventTime.date_with_times_re.search(interval_str)
        if match is not None:
            dt = timezone.datetime(
                year=int(match.group(3)),
                month=int(match.group(2)),
                day=int(match.group(1)),
            )
            return(
                timezone.make_aware(dt + datetime.timedelta(
                    hours=int(match.group(4)),
                    minutes=int(match.group(5))
                )),
                timezone.make_aware(dt + datetime.timedelta(
                    hours=int(match.group(6)),
                    minutes=int(match.group(7))
                ))
            )

        match = EventTime.dates_re.search(interval_str)
        if match is not None:
            return(
                timezone.make_aware(timezone.datetime(
                    year=int(match.group(3)),
                    month=int(match.group(2)),
                    day=int(match.group(1)),
                )),
                timezone.make_aware(timezone.datetime(
                    year=int(match.group(6)),
                    month=int(match.group(5)),
                    day=int(match.group(4)),
                ) + datetime.timedelta(days=1))
            )

        match = EventTime.dates_with_times_re.search(interval_str)
        if match is not None:
            return(
                timezone.make_aware(timezone.datetime(
                    year=int(match.group(3)),
                    month=int(match.group(2)),
                    day=int(match.group(1)),
                    hour=int(match.group(4)),
                    minute=int(match.group(5))
                )),
                timezone.make_aware(timezone.datetime(
                    year=int(match.group(8)),
                    month=int(match.group(7)),
                    day=int(match.group(6)),
                    hour=int(match.group(9)),
                    minute=int(match.group(10))
                ))
            )

        return None

    @property
    def duration_matches_product(self):
        return (self.duration_in_minutes > 0 and
                self.product is not None and
                self.product.duration_in_minutes == self.duration_in_minutes)

    @classmethod
    def migrate_from_visits(cls):
        visit_model = cls.visit.field.related_model

        # Skip if the neccessary date fields are no longer present on the
        # Visit model
        try:
            visit_model._meta.get_field_by_name("deprecated_start_datetime")
            visit_model._meta.get_field_by_name("deprecated_end_datetime")
        except:
            return

        qs = visit_model.objects.filter(
            eventtime__isnull=True,
            deprecated_product__isnull=False
        )

        for x in qs.order_by("deprecated_start_datetime",
                             "deprecated_end_datetime"):
            obj = cls(
                product=x.deprecated_product,
                visit=x,
                start=x.deprecated_start_datetime,
                notes=_(u'Migreret fra Visit')
            )

            if x.deprecated_end_datetime:
                obj.end = x.deprecated_end_datetime
            else:
                # Try to calculate the end time
                obj.set_calculated_end_time()

            obj.has_specific_time = obj.calculated_has_specific_time()
            obj.save()

    @property
    def expired(self):
        return self.start and self.start < timezone.now()

    @property
    def visit_link(self):
        if self.visit:
            return reverse('visit-view', args=[self.visit.pk])
        else:
            return reverse('time-view', args=[self.product.pk, self.pk])

    @property
    def interval_display(self):
        if self.end:
            diff_dates = self.naive_start.date() != self.naive_end.date()
            if self.has_specific_time:
                if diff_dates:
                    return " - ".join([self.l10n_start, self.l10n_end])
                else:
                    return " - ".join([self.l10n_start, self.l10n_end_time])
            else:
                if diff_dates:
                    return " - ".join([
                        formats.date_format(
                            self.naive_start, "SHORT_DATE_FORMAT"
                        ),
                        formats.date_format(
                            self.naive_end - datetime.timedelta(days=1),
                            "SHORT_DATE_FORMAT"
                        ),
                    ])
                else:
                    return formats.date_format(
                        self.naive_start, "SHORT_DATE_FORMAT"
                    ),
        else:
            if self.start:
                if self.has_specific_time:
                    return self.l10n_start
                else:
                    return formats.date_format(
                        self.naive_start, "SHORT_DATE_FORMAT"
                    ),
            else:
                return unicode(_(u"<Intet tidspunkt angivet>"))

    def __unicode__(self):
        parts = [_(u"Tidspunkt:")]
        if self.product:
            parts.append(self.product.title)
        if self.visit:
            parts.append(_(u"(Besøg: %s)") % self.visit.pk)
        parts.append(self.interval_display)

        return " ".join([unicode(x) for x in parts])

    def on_start(self):
        self.has_notified_start = True
        if self.visit:
            self.visit.on_starttime()
        self.save()

    def on_end(self):
        self.has_notified_end = True
        if self.visit:
            self.visit.on_endtime()
        self.save()


class Calendar(AvailabilityUpdaterMixin, models.Model):

    def available_list(self, from_dt, to_dt):
        for x in self.calendarevent_set.filter(
            availability=CalendarEvent.AVAILABLE
        ).order_by("start", "end"):
            for y in x.between(from_dt, to_dt):
                yield y

    def unavailable_list(self, from_dt, to_dt):
        for x in self.calendarevent_set.filter(
            availability=CalendarEvent.NOT_AVAILABLE
        ).order_by("start", "end"):
            for y in x.between(from_dt, to_dt):
                yield y

        # Not available on times when we are booked as a resource
        if hasattr(self, 'resource'):
            for x in self.resource.occupied_eventtimes(from_dt, to_dt):
                if not x.start or not x.end:
                    continue
                yield CalendarEventInstance(
                    x.start,
                    x.end,
                    available=False,
                    source=x.visit
                )
            if hasattr(self.resource, 'user'):
                profile = self.resource.user.userprofile
                for x in profile.assigned_to_visits.all():
                    if not x.eventtime.start or not x.eventtime.end:
                        continue
                    if x.eventtime.start < to_dt and x.eventtime.end > from_dt:
                        yield CalendarEventInstance(
                            x.eventtime.start,
                            x.eventtime.end,
                            available=False,
                            source=x
                        )

        if hasattr(self, 'product'):
            for x in self.product.occupied_eventtimes(from_dt, to_dt):
                if not x.start or not x.end:
                    continue
                yield CalendarEventInstance(
                    x.start,
                    x.end,
                    available=False,
                    source=x.visit
                )

    def is_available_between(self, from_dt, to_dt, exclude_sources=set([])):
        # Check if availability rules match
        available_match = False

        for x in self.available_list(from_dt, to_dt):
            if x.source in exclude_sources:
                continue

            if x.start <= from_dt and x.end >= to_dt:
                available_match = True
                break

        if not available_match:
            return False

        # Any blocking source that is not in exclude_sources means the
        # resource is not available.
        for x in self.unavailable_list(from_dt, to_dt):
            if x.source in exclude_sources:
                continue

            return False

        return True

    def has_available_time(self, from_dt, to_dt, minutes):
        needed = datetime.timedelta(minutes=minutes)

        unavailables = sorted([
            x for x in self.unavailable_list(from_dt, to_dt)
        ], key=lambda x: x.start)

        for available in self.available_list(from_dt, to_dt):
            # The first available start is whatever is later of the start
            # of the available interval and from_dt.
            avail_start_time = max(available.start, from_dt)
            avail_end_time = min(available.end, to_dt)

            # For each unavailable marker, check if the interval between
            # the last available start and the start of the unavailable period
            # is enough. If it is not, move the last available start to the
            # end of the unavailable interval, if that is later.
            for unavailable in unavailables:
                next_unavailable = min(unavailable.start, avail_end_time)
                if next_unavailable - avail_start_time >= needed:
                    return True
                else:
                    avail_start_time = max(unavailable.end, avail_start_time)

            # Last possible end is whatever comes first of the available
            # interval's end and to_dt. Compare this to the last available
            # start time to see if we have enough time after the last
            # unavailable marking.
            if avail_end_time - avail_start_time >= needed:
                return True

        return False

    @property
    def affected_eventtimes(self):
        if hasattr(self, 'resource'):
            return self.resource.affected_eventtimes
        else:
            return EventTime.objects.none()


class CalendarEventInstance(object):
    start = None
    end = None
    available = False
    source = None

    EMS_IN_DAY = 12
    SECONDS_IN_DAY = 24 * 60 * 60
    SECONDS_PER_EM = SECONDS_IN_DAY / EMS_IN_DAY

    def __init__(self, start, end, available=False, source=None):
        if not timezone.is_aware(start):
            start = timezone.make_aware(start)

        if not timezone.is_aware(end):
            end = timezone.make_aware(end)

        self.start = start
        self.end = end
        self.available = available
        self.source = source

    def day_marker(self, date):
        day_start = timezone.make_aware(
            datetime.datetime.combine(date, datetime.time())
        )
        day_end = day_start + datetime.timedelta(days=1)

        obj = {
            'event': self,
            'start': max(self.start, day_start),
            'end': min(self.end, day_end),
        }

        if obj['end'] == day_end:
            obj['time_interval'] = "%s - 24:00" % (
                str(obj['start'].astimezone(
                    timezone.get_current_timezone()
                ).time())[:5]
            )
        else:
            obj['time_interval'] = "%s - %s" % (
                str(obj['start'].astimezone(
                    timezone.get_current_timezone()
                ).time())[:5],
                str(obj['end'].astimezone(
                    timezone.get_current_timezone()
                ).time())[:5]
            )

        if self.available:
            obj['available_class'] = 'available'
        else:
            obj['available_class'] = 'unavailable'

        # Calculate offset from top of day in 5 minute intervals
        top_offset_seconds = (obj['start'] - day_start).total_seconds()
        obj['top_offset'] = '%.2f' % (
            top_offset_seconds / CalendarEventInstance.SECONDS_PER_EM
        )
        marker_duration = (obj['end'] - obj['start']).total_seconds()
        obj['height'] = '%.2f' % (
            marker_duration / CalendarEventInstance.SECONDS_PER_EM
        )

        return obj


class CalendarEvent(AvailabilityUpdaterMixin, models.Model):

    title = models.CharField(
        max_length=60,
        blank=False,
        verbose_name=_(u'Titel')
    )

    calendar = models.ForeignKey(
        Calendar,
        null=False,
        blank=False,
        verbose_name=_('Kalender')

    )

    AVAILABLE = 0
    NOT_AVAILABLE = 1

    availability_choices = (
        (AVAILABLE, _(u"Tilgængelig")),
        (NOT_AVAILABLE, _(u"Utilgængelig")),
    )
    availability = models.IntegerField(
        choices=availability_choices,
        verbose_name=_(u'Tilgængelighed'),
        default=AVAILABLE,
        blank=False,
    )
    start = models.DateTimeField(
        verbose_name=_(u"Starttidspunkt")
    )
    end = models.DateTimeField(
        verbose_name=_(u"Sluttidspunkt"),
        blank=True
    )
    recurrences = RecurrenceField(
        verbose_name=_(u"Gentagelser"),
        null=True,
        blank=True,
    )

    @property
    def has_recurrences(self):
        return self.recurrences and (
            len(self.recurrences.rrules) > 0 or
            len(self.recurrences.rdates) > 0
        )

    def between(self, from_dt, to_dt):
        duration = self.end - self.start
        recurrences = self.recurrences

        if self.has_recurrences:
            if not timezone.is_naive(from_dt):
                from_dt = timezone.make_naive(from_dt)
            if not timezone.is_naive(to_dt):
                to_dt = timezone.make_naive(to_dt)

            naive_start = timezone.make_naive(self.start)

            recurrences.dtstart = naive_start

            # Since we only find start time we have to extend the search
            # area with the duration in both directions.
            search_start = from_dt - duration
            search_end = to_dt + duration

            for x in recurrences.between(search_start, search_end, inc=True):
                starttime = timezone.datetime.combine(
                    x.date(), naive_start.time()
                )
                endtime = starttime + duration

                if endtime > from_dt and starttime < to_dt:
                    yield CalendarEventInstance(
                        timezone.make_aware(starttime),
                        timezone.make_aware(endtime),
                        available=(
                            self.availability == CalendarEvent.AVAILABLE
                        ),
                        source=self
                    )
        else:
            if self.end > from_dt and self.start < to_dt:
                yield CalendarEventInstance(
                    self.start,
                    self.end,
                    available=(self.availability == CalendarEvent.AVAILABLE),
                    source=self
                )

    @property
    def naive_start(self):
        if self.start:
            return timezone.make_naive(self.start)
        else:
            return self.start

    @property
    def naive_end(self):
        if self.end:
            return timezone.make_naive(self.end)
        else:
            return self.end

    @property
    def l10n_start(self):
        if self.start:
            return unicode(
                formats.date_format(self.naive_start, "SHORT_DATETIME_FORMAT")
            )
        else:
            return ''

    @property
    def l10n_end(self):
        if self.end:
            return unicode(
                formats.date_format(self.naive_end, "SHORT_DATETIME_FORMAT")
            )
        else:
            return ''

    @property
    def l10n_end_time(self):
        if self.end:
            return unicode(formats.time_format(self.naive_end))
        else:
            return ''

    @property
    def interval_display(self):
        if self.end:
            if self.naive_start.date() != self.naive_end.date():
                return " - ".join([self.l10n_start, self.l10n_end])
            else:
                return " - ".join([self.l10n_start, self.l10n_end_time])
        else:
            if self.start:
                return unicode(
                    formats.date_format(self.naive_start, "SHORT_DATE_FORMAT")
                )
            else:
                return unicode(_(u"<Intet tidspunkt angivet>"))

    @property
    def affected_eventtimes(self):
        if self.calendar:
            return self.calendar.affected_eventtimes
        else:
            return EventTime.objects.none()

    @property
    def calendar_event_link(self):
        if hasattr(self.calendar, 'resource'):
            return reverse('calendar-event-edit', args=[
                self.calendar.resource.pk,
                self.pk
            ])
        else:
            return reverse('product-calendar-event-edit', args=[
                self.calendar.product.pk,
                self.pk
            ])

    @property
    def calender_event_title(self):
        return self.title

    @staticmethod
    def get_events(availability, start=None, end=None):
        if availability in [
            CalendarEvent.AVAILABLE, CalendarEvent.NOT_AVAILABLE
        ]:
            qs = CalendarEvent.objects.filter(
                availability=availability
            )
            if start is not None:
                qs = qs.filter(end__gte=start)
            if end is not None:
                qs = qs.filter(start__lte=end)
            return qs
        return CalendarEvent.objects.none()

    def __unicode__(self):
        return ", ".join(unicode(x) for x in [
            self.title,
            "%s %s%s" % (
                self.get_availability_display().lower(),
                self.interval_display,
                _(" (med gentagelser)") if self.has_recurrences else ""
            ),

        ] if x)


class ResourceType(models.Model):
    RESOURCE_TYPE_ITEM = 1
    RESOURCE_TYPE_VEHICLE = 2
    RESOURCE_TYPE_TEACHER = 3
    RESOURCE_TYPE_ROOM = 4
    RESOURCE_TYPE_HOST = 5

    def __init__(self, *args, **kwargs):
        super(ResourceType, self).__init__(*args, **kwargs)
        if self.id == ResourceType.RESOURCE_TYPE_ITEM:
            self.resource_class = ItemResource
        elif self.id == ResourceType.RESOURCE_TYPE_VEHICLE:
            self.resource_class = VehicleResource
        elif self.id == ResourceType.RESOURCE_TYPE_TEACHER:
            self.resource_class = TeacherResource
        elif self.id == ResourceType.RESOURCE_TYPE_ROOM:
            self.resource_class = RoomResource
        elif self.id == ResourceType.RESOURCE_TYPE_HOST:
            self.resource_class = HostResource
        else:
            self.resource_class = CustomResource

    name = models.CharField(
        max_length=30
    )
    plural = models.CharField(
        max_length=30,
        default=""
    )

    @staticmethod
    def create_defaults():
        for (id, name, plural) in [
            (ResourceType.RESOURCE_TYPE_ITEM, u"Materiale", u"Materialer"),
            (ResourceType.RESOURCE_TYPE_VEHICLE,
             u"Transportmiddel", u"Transportmidler"),
            (ResourceType.RESOURCE_TYPE_TEACHER,
             u"Underviser", u"Undervisere"),
            (ResourceType.RESOURCE_TYPE_ROOM, u"Lokale", u"Lokaler"),
            (ResourceType.RESOURCE_TYPE_HOST, u"Vært", u"Værter")
        ]:
            try:
                item = ResourceType.objects.get(id=id)
                item.name = name
                item.plural = plural
                item.save()
            except ResourceType.DoesNotExist:
                item = ResourceType(id=id, name=name, plural=plural)
                item.save()
                print "Created new ResourceType %d=%s" % (id, name)

    def __unicode__(self):
        return self.name


class Resource(AvailabilityUpdaterMixin, models.Model):
    resource_type = models.ForeignKey(
        ResourceType,
        verbose_name=_(u'Type')
    )
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    calendar = models.OneToOneField(
        Calendar,
        blank=True,
        null=True,
        verbose_name=_(u"Ressourcens kalender"),
        on_delete=models.SET_NULL
    )

    def get_name(self):
        return "Resource"

    def can_delete(self):
        return True

    def occupied_eventtimes(self, dt_from=None, dt_to=None):
        qs = EventTime.objects.filter(
            visit__resources=self
        ).exclude(
            visit__workflow_status=Visit.WORKFLOW_STATUS_CANCELLED
        )
        if dt_from:
            qs = qs.filter(end__gt=dt_from)
        if dt_to:
            qs = qs.filter(start__lt=dt_to)

        return qs

    def is_available_between(self, from_dt, to_dt, exclude_sources=set()):
        if self.calendar:
            return self.calendar.is_available_between(
                from_dt, to_dt, exclude_sources
            )

        qs = self.occupied_eventtimes(from_dt, to_dt)

        visit_exclude_sources = set([
            x for x in exclude_sources if type(x) is Visit
        ])
        if len(visit_exclude_sources) > 0:
            qs = qs.exclude(visit__in=visit_exclude_sources)

        return not qs.exists()

    @classmethod
    def subclasses(cls):
        subs = set()
        for subclass in cls.__subclasses__():
            subs.add(subclass)
            subs.update(subclass.subclasses())
        return subs

    @classmethod
    def get_subclass_instance(cls, pk):
        for typeclass in cls.subclasses():
            if not typeclass._meta.abstract:
                try:
                    return typeclass.objects.get(id=pk)
                except typeclass.DoesNotExist:
                    pass
        raise Resource.DoesNotExist

    @classmethod
    def create_subclass_instance(cls, type):
        if not isinstance(type, ResourceType):
            type = ResourceType.objects.get(id=type)
        cls = type.resource_class
        return cls()

    def __unicode__(self):
        return "%s (%s)" % (
            unicode(self.get_name()),
            unicode(self.resource_type)
        )

    @property
    def subclass_instance(self):
        return Resource.get_subclass_instance(self.pk)

    def group_preview(self, maxchars=50):
        display_groups = []
        chars = 0
        for group in self.resourcepool_set.all():
            display_groups.append({'name': group.name, 'group': group})
            chars += len(group.name)
            if maxchars is not None and chars >= maxchars:
                break
        if maxchars is not None and \
                len(display_groups) > 0 and \
                chars > maxchars:
            lastgroup = display_groups[-1]
            lastgroup['name'] = lastgroup['name'][0:(maxchars - chars)] + "..."
        return display_groups

    def occupied_by(self, start_time, end_time):
        visits = []
        for visitresource in self.visitresource.filter(
            visit__eventtime__start__lte=end_time,
            visit__eventtime__end__gte=start_time
        ):
            visits.append(visitresource.visit)
        return visits

    def available_for_visit(self, visit):
        return self.is_available_between(
            visit.eventtime.start,
            visit.eventtime.end,
            exclude_sources=set([visit])
        )

    def make_calendar(self):
        if not self.calendar:
            cal = Calendar()
            cal.save()
            self.calendar = cal
            self.save()

    @property
    def affected_eventtimes(self):
        if self.pk:
            return EventTime.objects.filter(
                product__resourcerequirement__resource_pool__resources=self
            )
        else:
            return EventTime.objects.none()

    def save(self, *args, **kwargs):
        is_creating = self.pk is None

        super(Resource, self).save(*args, **kwargs)

        # Auto-create a calendar along with the resource
        if is_creating:
            self.make_calendar()


class UserResource(Resource):
    class Meta:
        abstract = True

    role = NONE
    resource_type_id = 0

    user = models.ForeignKey(
        auth_models.User,
        verbose_name=_(u"Underviser")
    )

    def __init__(self, *args, **kwargs):
        super(UserResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=self.__class__.resource_type_id
        )

    def get_name(self):
        return unicode(self.user.get_full_name())

    def can_delete(self):
        return False

    @classmethod
    def create_missing(cls):
        known_users = list([
            userresource.user.id
            for userresource in cls.objects.filter(
                user__userprofile__user_role__role=cls.role
            )
        ])
        print "We already have resources for %d users" % len(known_users)
        missing_users = auth_models.User.objects.filter(
            userprofile__user_role__role=cls.role
        ).exclude(
            pk__in=known_users
        )
        print "We are missing resources for %d users" % len(missing_users)
        if len(missing_users) > 0:
            created = 0
            skipped = 0
            for user in missing_users:
                try:
                    profile = user.userprofile
                    if profile.organizationalunit is not None:
                        user_resource = cls(
                            user=user,
                            organizationalunit=profile.organizationalunit
                        )
                        user_resource.save()
                        created += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print e
            print "Created %d %s objects" % (created, cls.__name__)
            if skipped > 0:
                print "Skipped creating resources for %d objects " \
                      "that had no unit" % skipped

    @classmethod
    def create(cls, user, unit=None):
        if user.userprofile.get_role() == cls.role:
            if unit is None:
                unit = user.userprofile.organizationalunit
            user_resource = cls(
                user=user,
                organizationalunit=unit
            )
            user_resource.save()


class TeacherResource(UserResource):
    role = TEACHER
    resource_type_id = ResourceType.RESOURCE_TYPE_TEACHER


class HostResource(UserResource):
    role = HOST
    resource_type_id = ResourceType.RESOURCE_TYPE_HOST


class RoomResource(Resource):
    # TODO: Begræns ud fra enhed
    room = models.ForeignKey(
        "Room",
        verbose_name=_(u"Lokale")
    )

    def __init__(self, *args, **kwargs):
        super(RoomResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_ROOM
        )

    def get_name(self):
        return self.room.name

    def can_delete(self):
        return False

    @staticmethod
    def create_missing():
        known_rooms = list([
            roomresource.room.id
            for roomresource in RoomResource.objects.all()
        ])
        missing_rooms = Room.objects.exclude(id__in=known_rooms)
        for room in missing_rooms:
            try:
                RoomResource.create(room)
            except:
                pass

    @staticmethod
    def create(room, unit=None):
        if unit is None:
            unit = room.locality.organizationalunit
        room_resource = RoomResource(room=room, organizationalunit=unit)
        room_resource.save()


class NamedResource(Resource):
    class Meta:
        abstract = True
    name = models.CharField(
        max_length=1024,
        verbose_name=_(u'Navn')
    )

    def get_name(self):
        return self.name


class ItemResource(NamedResource):
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True,
        verbose_name=_(u'Lokalitet')
    )

    def __init__(self, *args, **kwargs):
        super(ItemResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_ITEM
        )


class VehicleResource(NamedResource):
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True,
        verbose_name=_(u'Lokalitet')
    )

    def __init__(self, *args, **kwargs):
        super(VehicleResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.objects.get(
            id=ResourceType.RESOURCE_TYPE_VEHICLE
        )


class CustomResource(NamedResource):
    pass


class ResourcePool(AvailabilityUpdaterMixin, models.Model):
    resource_type = models.ForeignKey(ResourceType)
    name = models.CharField(
        max_length=1024,
        verbose_name=_(u'Navn')
    )
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    # TODO: Begrænse på enhed, resource_type
    resources = models.ManyToManyField(
        Resource,
        verbose_name=_(u"Ressourcer"),
        blank=True
    )

    def can_delete(self):
        return True

    def __unicode__(self):
        return "%s (%s)" % (self.name, _("Gruppe af %s") % self.resource_type)

    @property
    def specific_resources(self):
        return [
            resource.subclass_instance
            for resource in self.resources.all()
        ]

    def available_resources_between(self, from_dt, to_dt):
        for x in self.resources.all():
            if x.is_available_between(from_dt, to_dt):
                yield x

    @property
    def affected_eventtimes(self):
        if self.pk:
            res = self.resources.all()
            return EventTime.objects.filter(
                product__resourcerequirement__resource_pool__resources=res
            )
        else:
            return EventTime.objects.none()


class ResourceRequirement(AvailabilityUpdaterMixin, models.Model):
    product = models.ForeignKey("Product")
    resource_pool = models.ForeignKey(
        ResourcePool,
        verbose_name=_(u"Ressourcegruppe"),
        null=True,
        blank=False,
        on_delete=SET_NULL
    )
    required_amount = models.IntegerField(
        verbose_name=_(u"Påkrævet antal"),
        validators=[MinValueValidator(1)]
    )

    # For avoiding an IntegrityError when deleting Requirements:
    # A pre_delete signal will set this flag, and Visit.autoassign_resources()
    # will then ignore this requirement. If we don't do this, the requirement
    # slated for deletion can cause a new VisitResource to be created in
    # Visit.autoassign_resources(), referencing the deleted requirement.
    being_deleted = models.BooleanField(
        default=False
    )

    def can_delete(self):
        return True

    def can_be_fullfilled_between(self, from_dt, to_dt):
        return self.has_free_resources_between(
            from_dt, to_dt, self.required_amount
        )

    def has_free_resources_between(self, from_dt, to_dt, amount=1):
        if self.resource_pool is None:
            return False
        if amount <= 0:
            return True

        count = 0

        for x in self.resource_pool.available_resources_between(
            from_dt, to_dt
        ):
            count = count + 1
            if count >= amount:
                return True

        return False

    def is_fullfilled_for(self, visit):
        if self.resource_pool is None:
            return False
        return VisitResource.objects.filter(
            visit=visit,
            resource_requirement=self
        ).count() >= self.required_amount

    @property
    def affected_eventtimes(self):
        if self.pk and self.resource_pool:
            res = self.resource_pool.resources.all()
            return EventTime.objects.filter(
                product__resourcerequirement__resource_pool__resources=res
            )
        else:
            return EventTime.objects.none()


class VisitResource(AvailabilityUpdaterMixin, models.Model):
    visit = models.ForeignKey(
        "Visit",
        verbose_name=_(u"Besøg"),
        related_name='visitresource'
    )
    resource = models.ForeignKey(
        Resource,
        verbose_name=_(u"Ressource"),
        related_name='visitresource'
    )
    resource_requirement = models.ForeignKey(
        ResourceRequirement,
        verbose_name=_(u"Ressourcebehov"),
        related_name='visitresource'
    )

    def save(self, *args, **kwargs):
        new = self.pk is None
        super(VisitResource, self).save(*args, **kwargs)
        if new:
            resourcetype = self.resource.resource_type.id
            if resourcetype == ResourceType.RESOURCE_TYPE_TEACHER:
                self.visit.autosend(
                    EmailTemplateType.notify_teacher__associated,
                    [self.resource.teacherresource.user],
                    True
                )
            if resourcetype == ResourceType.RESOURCE_TYPE_HOST:
                self.visit.autosend(
                    EmailTemplateType.notify_host__associated,
                    [self.resource.hostresource.user],
                    True
                )

    @property
    def affected_eventtimes(self):
        if self.resource_requirement:
            return self.resource_requirement.affected_eventtimes
        else:
            return EventTime.objects.none()
