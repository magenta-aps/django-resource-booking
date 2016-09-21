# encoding: utf-8
from django.db import models
from django.contrib.auth import models as auth_models
from django.core.urlresolvers import reverse
from django.utils import formats
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from recurrence.fields import RecurrenceField

import datetime
import math


class EventTime(models.Model):

    class Meta:
        verbose_name = _(u"tidspunkt")
        verbose_name_plural = _(u"tidspunkter")
        ordering = ['-start', '-end']

    product = models.ForeignKey("Product")
    visit = models.ForeignKey(
        "Visit",
        null=True,
        blank=True
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

    def set_calculated_end_time(self):
        # Don't calculate if already set
        if self.end is None:
            return

        # Can not calculate end unless we have a start and a product
        if self.start is None or self.product is None:
            return

        duraction = self.product.duration_in_minutes or 0

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

    def make_visit(self, bookable=False, **kwargs):
        if not self.product:
            raise Exception("Can not create a visit without a product")

        if self.visit is not None:
            raise Exception(
                "Trying to create a visit for eventtime which already has one"
            )

        visit_model = EventTime.visit.field.related_model

        visit = visit_model(
            bookable=bookable,
            **kwargs
        )

        # If the product specifies no rooms are needed, set this on the
        # visit.
        if not self.product.rooms_needed:
            visit.room_status = Visit.STATUS_NOT_NEEDED

        visit.save()

        # Copy rooms from product to the visit
        if self.product.rooms.exists():
            for x in self.product.rooms.all():
                visit.rooms.add(x)

        visit.create_inheriting_autosends()
        visit.ensure_statistics()

        self.visit = visit
        self.save()

        return visit

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
    def can_be_deleted(self):
        return not self.visit

    @staticmethod
    # Parses the human readable interval that is used on web pages.
    def parse_human_readable_interval(interval_str):
        parts = interval_str.split(" ", 1)

        dateparts = parts[0].split(".")
        start = timezone.datetime(
            year=int(dateparts[2]),
            month=int(dateparts[1]),
            day=int(dateparts[0]),
            hour=0,
            minute=0
        )
        end = timezone.datetime(
            year=int(dateparts[2]),
            month=int(dateparts[1]),
            day=int(dateparts[0]),
            hour=0,
            minute=0
        )
        if len(parts) > 1:
            timeparts = parts[1].split(" - ")

            starttimes = timeparts[0].split(":")
            start = start + datetime.timedelta(
                hours=int(starttimes[0]),
                minutes=int(starttimes[1])
            )

            if len(timeparts) > 1:
                endtimes = timeparts[1].split(":")
                end = end + datetime.timedelta(
                    hours=int(endtimes[0]),
                    minutes=int(endtimes[1])
                )
        else:
            end = end + datetime.timedelta(days=1)

        return (timezone.make_aware(start), timezone.make_aware(end))

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

        qs = visit_model.objects.filter(eventtime__isnull=True)

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

            has_specific_time = obj.calculated_has_specific_time()

            print obj
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
        if self.end and self.has_specific_time:
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

    def __unicode__(self):
        parts = [_(u"Tidspunkt:")]
        if self.product:
            parts.append(self.product.title)
        if self.visit:
            parts.append(_(u"(Besøg: %s)") % self.visit.pk)
        parts.append(self.interval_display)

        return " ".join([unicode(x) for x in parts])


class Calendar(models.Model):
    available_list = RecurrenceField(
        verbose_name=_(u"Tilgængelige tider")
    )
    unavailable_list = RecurrenceField(
        verbose_name=_(u"Utilgængelige tider")
    )


class ResourceType(models.Model):
    RESOURCE_TYPE_ITEM = 1
    RESOURCE_TYPE_VEHICLE = 2
    RESOURCE_TYPE_TEACHER = 3
    RESOURCE_TYPE_ROOM = 4

    default_resource_names = {
        RESOURCE_TYPE_ITEM: _(u"Materiale"),
        RESOURCE_TYPE_VEHICLE: _(u"Transportmiddel"),
        RESOURCE_TYPE_TEACHER: _(u"Underviser"),
        RESOURCE_TYPE_ROOM: _(u"Lokale"),
    }

    name = models.CharField(
        max_length=30
    )

    @classmethod
    def create_defaults(cls):
        raise NotImplementedError()


class Resource(models.Model):
    resource_type = models.ForeignKey(ResourceType)
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    calendar = models.ForeignKey(
        Calendar,
        blank=True,
        null=True,
        verbose_name=_(u"Ressourcens kalender")
    )


class TeacherResource(Resource):
    # TODO: Begræns til brugertype og enhed
    user = models.ForeignKey(
        auth_models.User,
        verbose_name=_(u"Underviser")
    )

    def __init__(self, *args, **kwargs):
        super(TeacherResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.RESOURCE_TYPE_TEACHER


class RoomResource(Resource):
    # TODO: Begræns ud fra enhed
    room = models.ForeignKey(
        "Room",
        verbose_name=_(u"Lokale")
    )

    def __init__(self, *args, **kwargs):
        super(RoomResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.RESOURCE_TYPE_ROOM


class ItemResource(Resource):
    name = models.CharField(
        max_length=1024
    )
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super(ItemResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.RESOURCE_TYPE_ITEM


class VehicleResource(Resource):
    name = models.CharField(
        max_length=1024
    )
    locality = models.ForeignKey(
        "Locality",
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super(ItemResource, self).__init__(*args, **kwargs)
        self.resource_type = ResourceType.RESOURCE_TYPE_VEHICLE


class ResourcePool(models.Model):
    resource_type = models.ForeignKey(ResourceType)
    name = models.CharField(
        max_length=1024
    )
    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        verbose_name=_(u"Ressourcens enhed")
    )
    # TODO: Begrænse på enhed, resource_type
    resources = models.ManyToManyField(
        Resource,
        verbose_name=_(u"Ressourcer")
    )


class ResourceRequirement(models.Model):
    product = models.ForeignKey("Product")
    resource_pool = models.ForeignKey(
        ResourcePool,
        verbose_name=_(u"Ressourcepulje")
    )
    required_amount = models.IntegerField(
        verbose_name=_(u"Påkrævet antal")
    )
