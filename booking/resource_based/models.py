# encoding: utf-8
from django.db import models
from django.contrib.auth import models as auth_models
from django.utils import formats
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from recurrence.fields import RecurrenceField

import math


class EventTime(models.Model):
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
        return math.floor((self.end - self.start).total_seconds() / 60)

    @property
    def can_be_deleted(self):
        return not self.visit

    def __unicode__(self):
        if self.has_specific_time:
            if self.start.date() != self.end.date():
                return " - ".join([self.l10n_start, self.l10n_end])
            else:
                return " - ".join([self.l10n_start, self.l10n_end_time])
        else:
            return unicode(
                formats.date_format(self.naive_start, "SHORT_DATE_FORMAT")
            )


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
