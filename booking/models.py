# encoding: utf-8
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import Count
from django.db.models import F
from django.db.models import Max
from django.db.models import Sum
from django.db.models import Q
from django.db.models.base import ModelBase
from django.db.models.functions import Coalesce
from django.utils import six
from django.template.context import make_context
from django.utils import timezone
from django.utils.crypto import get_random_string
from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import formats
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as __
from django.template.base import Template, VariableNode

from booking.mixins import AvailabilityUpdaterMixin
from booking.utils import ClassProperty, full_email, CustomStorage, html2text
from booking.utils import get_related_content_types, INFINITY, merge_dicts
from booking.utils import flatten

from resource_booking import settings

from datetime import timedelta, datetime, date, time


from profile.constants import TEACHER, HOST
from profile.constants import COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR

import math
import uuid
import random
import sys

BLANK_LABEL = '---------'
BLANK_OPTION = (None, BLANK_LABEL,)

LOGACTION_CREATE = ADDITION
LOGACTION_CHANGE = CHANGE
LOGACTION_DELETE = DELETION
# If we need to add additional values make sure they do not conflict with
# system defined ones by adding 128 to the value.
LOGACTION_MAIL_SENT = 128 + 1
LOGACTION_CUSTOM2 = 128 + 2
LOGACTION_MANUAL_ENTRY = 128 + 64 + 1

LOGACTION_DISPLAY_MAP = {
    LOGACTION_CREATE: _(u'Oprettet'),
    LOGACTION_CHANGE: _(u'Ændret'),
    LOGACTION_DELETE: _(u'Slettet'),
    LOGACTION_MAIL_SENT: _(u'Mail sendt'),
    LOGACTION_MANUAL_ENTRY: _(u'Log-post tilføjet manuelt')
}


def log_action(user, obj, action_flag, change_message=''):
    if user and hasattr(user, "pk") and user.pk:
        user_id = user.pk
    else:
        # Late import due to mutual import conflicts
        from profile.models import get_public_web_user  # noqa
        pw_user = get_public_web_user()
        user_id = pw_user.pk

    content_type_id = None
    object_id = None
    object_repr = ""
    if obj:
        ctype = ContentType.objects.get_for_model(obj)
        content_type_id = ctype.pk
        try:
            object_id = obj.pk
        except:
            pass
        try:
            object_repr = unicode(obj)
        except:
            pass

    LogEntry.objects.log_action(
        user_id,
        content_type_id,
        object_id,
        object_repr,
        action_flag,
        change_message
    )


class RoomResponsible(models.Model):
    class Meta:
        verbose_name = _(u'Lokaleanvarlig')
        verbose_name_plural = _(u'Lokaleanvarlige')

    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=14, null=True, blank=True)

    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        blank=True,
        null=True
    )

    allow_null_unit_editing = True

    def admin_delete_button(self):
        return '<a href="%s" class="deletelink">%s</a>' % (
            reverse(
                'admin:booking_roomresponsible_delete',
                args=[self.pk]
            ),
            _(u"Delete"),
        )
    admin_delete_button.allow_tags = True
    admin_delete_button.short_description = _(u"Delete")

    def __unicode__(self):
        return self.name

    def get_name(self):
        return self.name

    def get_full_name(self):
        return self.get_name()

    def get_email(self):
        return self.email

    def get_full_email(self):
        return full_email(self.email, self.name)


# Units (faculties, institutes etc)
class OrganizationalUnitType(models.Model):
    """A type of organization, e.g. 'faculty' """

    class Meta:
        verbose_name = _(u"enhedstype")
        verbose_name_plural = _(u"Enhedstyper")

    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


class OrganizationalUnit(models.Model):
    """A generic organizational unit, such as a faculty or an institute"""

    class Meta:
        verbose_name = _(u"enhed")
        verbose_name_plural = _(u"enheder")
        ordering = ['name']

    name = models.CharField(max_length=100)
    type = models.ForeignKey(OrganizationalUnitType)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    contact = models.ForeignKey(
        User, null=True, blank=True,
        verbose_name=_(u'Kontaktperson'),
        related_name="contactperson_for_units",
        on_delete=models.SET_NULL,
    )
    url = models.URLField(
        verbose_name=u'Hjemmeside',
        null=True,
        blank=True
    )
    autoassign_resources_enabled = models.BooleanField(
        verbose_name=_(u'Automatisk ressourcetildeling mulig'),
        default=False
    )

    def belongs_to(self, unit):
        if self == unit:
            return True
        elif self.parent is None:
            return False
        else:
            return self.parent.belongs_to(unit)

    def get_descendants(self):
        """Return all units at a lower level"""
        offspring = OrganizationalUnit.objects.filter(parent=self)
        all_children = OrganizationalUnit.objects.none()
        for u in offspring:
            all_children = all_children | u.get_descendants()
        return all_children | OrganizationalUnit.objects.filter(pk=self.pk)

    def get_faculty_queryset(self):
        u = self

        # Go through parent relations until we hit a "fakultet"
        while u and u.type and u.type.name != "Fakultet":
            u = u.parent

        if u:
            return OrganizationalUnit.objects.filter(Q(pk=u.pk) | Q(parent=u))
        else:
            return OrganizationalUnit.objects.none()

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.type.name)

    def get_users(self, role=None):
        if role is not None:
            profiles = self.userprofile_set.filter(user_role__role=role).all()
        else:
            profiles = self.userprofile_set.all()
        return [profile.user for profile in profiles]

    def get_hosts(self):
        return self.get_users(HOST)

    def get_teachers(self):
        return self.get_users(TEACHER)

    def get_editors(self):

        # Try using all available coordinators
        res = self.get_users(COORDINATOR)
        if len(res) > 0:
            return res

        # If no coordinators was found use faculty editors
        res = User.objects.filter(
            userprofile__organizationalunit=self.get_faculty_queryset(),
            userprofile__user_role__role=FACULTY_EDITOR
        )
        if len(res) > 0:
            return [x for x in res]

        # Fall back to all administrators (globally)
        res = User.objects.filter(
            userprofile__user_role__role=ADMINISTRATOR
        )
        return [x for x in res]

    def get_recipients(self, template_type):
        recipients = []

        if template_type.send_to_unit_hosts:
            recipients.extend(self.get_hosts())

        if template_type.send_to_unit_teachers:
            recipients.extend(self.get_teachers())

        if template_type.send_to_editors:
            recipients.extend(self.get_editors())

        return recipients

    def get_reply_recipients(self, template_type):
        if template_type.reply_to_unit_responsible:
            return [self.contact]
        return []

    @classmethod
    def root_unit_id(cls):
        unit = cls.objects.filter(
            type__name=u"Københavns Universitet"
        ).first()
        if unit:
            return unit.pk
        else:
            return ""


# Master data related to bookable resources start here
class Subject(models.Model):
    """A relevant subject from primary or secondary education."""

    class Meta:
        verbose_name = _(u"fag")
        verbose_name_plural = _(u"fag")
        ordering = ["name"]

    SUBJECT_TYPE_GYMNASIE = 2**0
    SUBJECT_TYPE_GRUNDSKOLE = 2**1
    # NEXT_VALUE = 2**2

    SUBJECT_TYPE_BOTH = SUBJECT_TYPE_GYMNASIE | SUBJECT_TYPE_GRUNDSKOLE

    type_choices = (
        (SUBJECT_TYPE_GYMNASIE, _(u'Gymnasie')),
        (SUBJECT_TYPE_GRUNDSKOLE, _(u'Grundskole')),
        (SUBJECT_TYPE_BOTH, _(u'Både gymnasie og grundskole')),
    )

    name = models.CharField(max_length=256)
    subject_type = models.IntegerField(
        choices=type_choices,
        verbose_name=u'Skoleniveau',
        default=SUBJECT_TYPE_GYMNASIE,
        blank=False,
    )
    description = models.TextField(blank=True)

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.get_subject_type_display())

    @classmethod
    def gymnasiefag_qs(cls):
        return Subject.objects.filter(
            subject_type__in=[
                cls.SUBJECT_TYPE_GYMNASIE, cls.SUBJECT_TYPE_BOTH
            ]
        )

    @classmethod
    def grundskolefag_qs(cls):
        return Subject.objects.filter(
            subject_type__in=[
                cls.SUBJECT_TYPE_GRUNDSKOLE, cls.SUBJECT_TYPE_BOTH
            ]
        )


class Link(models.Model):
    """"An URL and relevant metadata."""
    url = models.URLField()
    name = models.CharField(max_length=256)
    # Note: "description" is intended as automatic text when linking in web
    # pages.
    description = models.CharField(max_length=256, blank=True)

    def __unicode__(self):
        return self.name


class Tag(models.Model):
    """Tag class, just name and description fields."""
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class Topic(models.Model):
    """Tag class, just name and description fields."""

    class Meta:
        verbose_name = _(u"emne")
        verbose_name_plural = _(u"emner")

    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class StudyMaterial(models.Model):
    """Material for the students to study before visiting."""

    class Meta:
        verbose_name = _(u'undervisningsmateriale')
        verbose_name_plural = _(u'undervisningsmaterialer')

    URL = 0
    ATTACHMENT = 1
    study_material_choices = (
        (URL, _(u"URL")),
        (ATTACHMENT, _(u"Vedhæftet fil"))
    )
    type = models.IntegerField(choices=study_material_choices, default=URL)
    url = models.URLField(null=True, blank=True)
    file = models.FileField(upload_to='material', null=True,
                            blank=True, storage=CustomStorage())
    product = models.ForeignKey('Product', null=True,
                                on_delete=models.CASCADE,)

    def __unicode__(self):
        s = u"{0}: {1}".format(
            u'URL' if self.type == self.URL else _(u"Vedhæftet fil"),
            self.url if self.type == self.URL else self.file
        )
        return s


class Locality(models.Model):
    """A locality where a visit may take place."""

    class Meta:
        verbose_name = _(u'lokalitet')
        verbose_name_plural = _(u'lokaliteter')
        ordering = ["name"]

    name = models.CharField(max_length=256, verbose_name=_(u'Navn'))
    description = models.TextField(blank=True, verbose_name=_(u'Beskrivelse'))
    address_line = models.CharField(max_length=256, verbose_name=_(u'Adresse'))
    zip_city = models.CharField(
        max_length=256, verbose_name=_(u'Postnummer og by')
    )
    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        verbose_name=_(u'Enhed'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    def __unicode__(self):
        return self.name

    @property
    def name_and_address(self):
        return "%s (%s)" % (
            unicode(self.name),
            ", ".join([
                unicode(x) for x in [self.address_line, self.zip_city] if x
            ])
        )

    @property
    def full_address(self):
        return " ".join([
            unicode(x)
            for x in (self.name, self.address_line, self.zip_city)
            if x
        ])

    @property
    def route_url(self):
        # return "http://www.findvej.dk/?daddress=%s&dzip=%s" % \
        return "https://maps.google.dk/maps/dir//%s,%s" % \
               (self.address_line, self.zip_city)

    @property
    def location_url(self):
        # return "http://www.findvej.dk/%s,%s" % \
        return "https://maps.google.dk/maps/place/%s,%s" % \
               (self.address_line, self.zip_city)


class EmailTemplateTypeMeta(ModelBase):
    # Hack to allow lookups on EmailTemplateType.<lowercase keyname>
    def __getattr__(self, name):
        if name[0:2] != '__':
            upper = name.upper()
            if name != upper and hasattr(self, upper):
                value = getattr(self, name.upper())
                if type(value) == int:
                    try:
                        return self.objects.get(key=value)
                    except:
                        pass


class EmailTemplateType(
    six.with_metaclass(EmailTemplateTypeMeta, models.Model)
):

    NOTIFY_GUEST__BOOKING_CREATED = 1  # ticket 13806
    NOTIFY_EDITORS__BOOKING_CREATED = 2  # ticket 13807
    NOTIFY_HOST__REQ_TEACHER_VOLUNTEER = 3  # ticket 13808
    NOTIFY_HOST__REQ_HOST_VOLUNTEER = 4  # ticket 13809
    NOTIFY_HOST__ASSOCIATED = 5  # ticket 13810
    NOTIFY_HOST__REQ_ROOM = 6  # ticket 13811
    NOTIFY_GUEST__GENERAL_MSG = 7  # ticket 13812
    NOTIFY_ALL__BOOKING_COMPLETE = 8  # ticket 13813
    NOTIFY_ALL__BOOKING_CANCELED = 9  # ticket 13814
    NOTITY_ALL__BOOKING_REMINDER = 10  # ticket 13815
    NOTIFY_HOST__HOSTROLE_IDLE = 11  # ticket 13805
    SYSTEM__BASICMAIL_ENVELOPE = 12
    SYSTEM__EMAIL_REPLY = 13
    SYSTEM__USER_CREATED = 14
    NOTIFY_GUEST_REMINDER = 15  # Ticket 15510
    NOTIFY_GUEST__SPOT_OPEN = 16  # Ticket 13804
    NOTIFY_GUEST__SPOT_ACCEPTED = 17  # Ticket 13804
    NOTIFY_GUEST__SPOT_REJECTED = 18  # Ticket 13804
    NOTIFY_EDITORS__SPOT_REJECTED = 19  # Ticket 13804
    NOTIFY_GUEST__BOOKING_CREATED_WAITING = 20  # ticket 13804
    NOTIFY_TEACHER__ASSOCIATED = 21  # Ticket 15701
    NOTIFY_ALL_EVALUATION = 22  # Ticket 15701
    NOTIFY_GUEST__BOOKING_CREATED_UNTIMED = 23  # Ticket 16914
    NOTIFY_GUEST__EVALUATION_FIRST = 24  # Ticket 13819
    NOTIFY_GUEST__EVALUATION_SECOND = 25  # Ticket 13819

    @staticmethod
    def get(template_key):
        if type(template_key) == int:
            return EmailTemplateType.objects.get(key=template_key)
        elif isinstance(template_key, EmailTemplateType):
            return template_key
        elif isinstance(template_key, EmailTemplate):
            return template_key.type

    @staticmethod
    def get_name(template_key):
        return EmailTemplateType.get(template_key).name

    key = models.IntegerField(
        verbose_name=u'Type',
        default=1
    )

    name_da = models.CharField(
        verbose_name=u'Navn',
        max_length=1024,
        null=True
    )

    ordering = models.IntegerField(
        verbose_name=u'Sortering',
        default=0
    )

    @property
    def name(self):
        return self.name_da

    def __unicode__(self):
        return self.name

    # Template available for manual sending from visits
    manual_sending_visit_enabled = models.BooleanField(default=False)

    # Template available for manual sending from mpv bookings
    manual_sending_mpv_enabled = models.BooleanField(default=False)

    # Template available for manual sending from mpv bookings
    manual_sending_mpv_sub_enabled = models.BooleanField(default=False)

    # Template will be autosent to editors for the given unit
    manual_sending_booking_enabled = models.BooleanField(default=False)

    # Template will be autosent to editors for the given unit
    manual_sending_booking_mpv_enabled = models.BooleanField(default=False)

    # Template will be autosent to editors for the given unit
    send_to_editors = models.BooleanField(default=False)

    # Template will be autosent to visit.tilbudsansvarlig
    send_to_contactperson = models.BooleanField(default=False)

    # Template will be autosent to booker
    send_to_booker = models.BooleanField(default=False)

    # Template will be autosent to all hosts in the unit
    send_to_unit_hosts = models.BooleanField(default=False)

    # Template will be autosent to all teachers in the unit
    send_to_unit_teachers = models.BooleanField(default=False)

    # Template will be sent to potential hosts
    send_to_potential_hosts = models.BooleanField(default=False)

    # Template will be sent to potential teachers
    send_to_potential_teachers = models.BooleanField(default=False)

    # Template will be autosent to hosts in the visit
    send_to_visit_hosts = models.BooleanField(default=False)

    # Template will be autosent to teachers in the visit
    send_to_visit_teachers = models.BooleanField(default=False)

    # Template will be autosent to hosts when they are added to a visit
    send_to_visit_added_host = models.BooleanField(default=False)

    # Template will be autosent to teachers when they are added to a visit
    send_to_visit_added_teacher = models.BooleanField(default=False)

    # Does the "days" field make sense?
    enable_days = models.BooleanField(default=False)

    # Does the {{ booking }} variable make sense
    enable_booking = models.BooleanField(default=False)

    avoid_already_assigned = models.BooleanField(default=False)

    is_default = models.BooleanField(default=False)

    enable_autosend = models.BooleanField(default=False)

    form_show = models.BooleanField(default=False)

    @property
    def reply_to_product_responsible(self):
        for x in [
            self.send_to_visit_hosts, self.send_to_visit_teachers,
            self.send_to_booker, self.send_to_potential_hosts,
            self.send_to_potential_teachers, self.send_to_visit_added_host,
            self.send_to_visit_added_teacher, self.send_to_unit_hosts,
            self.send_to_unit_teachers
        ]:
            if x:
                return True
        return False

    @property
    def reply_to_unit_responsible(self):
        return False

    @staticmethod
    def set_default(key, **kwargs):
        try:
            template_type = EmailTemplateType.objects.get(key=key)
        except EmailTemplateType.DoesNotExist:
            template_type = EmailTemplateType(key=key)
        for attr in template_type._meta.fields:
            if attr.name in kwargs:
                setattr(template_type, attr.name, kwargs[attr.name])
            elif isinstance(attr, models.BooleanField):
                setattr(template_type, attr.name, False)
        #    if hasattr(template_type, arg):
        #        setattr(template_type, arg)
        template_type.save()
        return template_type

    @staticmethod
    def set_defaults():
        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            name_da=u'Besked til gæst ved tilmelding (med fast tid)',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=1
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED,
            name_da=u'Besked til gæst ved tilmelding (besøg uden fast tid)',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=2
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_WAITING,
            name_da=u'Besked til gæster der har tilmeldt sig venteliste',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=3
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__GENERAL_MSG,
            name_da=u'Generel besked til gæst(er)',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=4
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_OPEN,
            name_da=u'Mail til gæst fra venteliste, '
                    u'der får tilbudt plads på besøget',
            manual_sending_visit_enabled=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=5
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_ACCEPTED,
            name_da=u'Besked til gæst ved accept af plads (fra venteliste)',
            send_to_booker=True,
            enable_booking=True,
            enable_autosend=True,
            is_default=True,
            form_show=False,
            ordering=6
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_REJECTED,
            name_da=u'Besked til gæst ved afvisning af plads (fra venteliste)',
            send_to_booker=True,
            enable_booking=True,
            enable_autosend=False,
            form_show=False,
            ordering=7
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST_REMINDER,
            name_da=u'Reminder til gæst',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            enable_autosend=True,
            form_show=True,
            ordering=8
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED,
            name_da=u'Besked til koordinator, når gæst har tilmeldt sig besøg',
            send_to_contactperson=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=9
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_EDITORS__SPOT_REJECTED,
            name_da=u'Besked til koordinatorer ved afvisning '
                    u'af plads (fra venteliste)',
            send_to_contactperson=True,
            enable_booking=True,
            enable_autosend=True,
            is_default=True,
            form_show=False,
            ordering=10
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER,
            name_da=u'Besked til vært, når en gæst har lavet en tilmelding',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_sub_enabled=True,
            send_to_potential_hosts=True,
            enable_booking=True,
            avoid_already_assigned=True,
            enable_autosend=True,
            form_show=True,
            ordering=11
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER,
            name_da=u'Besked til underviser, når en gæst '
                    u'har lavet en tilmelding',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_sub_enabled=True,
            send_to_potential_teachers=True,
            enable_booking=True,
            avoid_already_assigned=True,
            enable_autosend=True,
            form_show=True,
            ordering=12
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__ASSOCIATED,
            name_da=u'Bekræftelsesmail til vært',
            manual_sending_visit_enabled=True,
            send_to_visit_added_host=True,
            enable_autosend=True,
            form_show=True,
            ordering=13
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED,
            name_da=u'Bekræftelsesmail til underviser',
            manual_sending_visit_enabled=True,
            send_to_visit_added_teacher=True,
            enable_autosend=True,
            form_show=True,
            ordering=14
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE,
            name_da=u'Notifikation til koordinatorer om '
                    u'ledig værtsrolle på besøg',
            send_to_editors=True,
            enable_days=True,
            enable_autosend=True,
            form_show=True,
            ordering=15
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__REQ_ROOM,
            name_da=u'Besked til lokaleansvarlig',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_sub_enabled=True,
            enable_autosend=True,
            form_show=True,
            ordering=16
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED,
            name_da=u'Besked til alle ved aflysning',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_contactperson=True,
            send_to_booker=True,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=17
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE,
            name_da=u'Besked om færdigplanlagt besøg til alle involverede',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=18
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER,
            name_da=u'Reminder om besøg til alle involverede',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_contactperson=True,
            send_to_booker=True,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_days=True,
            enable_autosend=True,
            form_show=True,
            ordering=19
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_ALL_EVALUATION,
            name_da=u'Besked til alle om evaluering',
            manual_sending_visit_enabled=True,
            enable_autosend=True,
            form_show=True,
            ordering=20
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE,
            name_da=u'Besked til tilbudsansvarlig',
            enable_autosend=False,
            form_show=False,
            ordering=21
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__EMAIL_REPLY,
            name_da=u'Svar på e-mail fra systemet',
            enable_autosend=False,
            form_show=False,
            ordering=22
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__USER_CREATED,
            name_da=u'Besked til bruger ved brugeroprettelse',
            form_show=False,
            ordering=23
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST,
            name_da=u'Besked til bruger angående evaluering (første besked)',
            form_show=True,
            send_to_booker=True,
            enable_autosend=True,
            enable_booking=True,
            is_default=True,
            ordering=24
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND,
            name_da=u'Besked til bruger angående evaluering (anden besked)',
            form_show=True,
            send_to_booker=True,
            enable_autosend=True,
            enable_booking=True,
            enable_days=True,
            is_default=True,
            ordering=25
        )

    @staticmethod
    def get_keys(**kwargs):
        return [
            template_type.key
            for template_type in EmailTemplateType.objects.filter(**kwargs)
        ]

    @staticmethod
    def get_choices(**kwargs):
        types = EmailTemplateType.objects.filter(**kwargs)
        return [
            (type.id, type.name) for type in types
        ]

    @staticmethod
    def editor_keys():
        return EmailTemplateType.get_keys(send_to_editors=True)

    @staticmethod
    def contact_person_keys():
        return EmailTemplateType.get_keys(send_to_contactperson=True)

    @staticmethod
    def booker_keys():
        return EmailTemplateType.get_keys(send_to_booker=True)

    @staticmethod
    def unit_hosts_keys():
        return EmailTemplateType.get_keys(send_to_unit_hosts=True)

    @staticmethod
    def unit_teachers_keys():
        return EmailTemplateType.get_keys(send_to_unit_teachers=True)

    @staticmethod
    def visit_hosts_keys():
        return EmailTemplateType.get_keys(send_to_visit_hosts=True)

    @staticmethod
    def visit_teachers_keys():
        return EmailTemplateType.get_keys(send_to_visit_teachers=True)

    @staticmethod
    def visit_added_host_keys():
        return EmailTemplateType.get_keys(send_to_visit_added_host=True)

    @staticmethod
    def visit_added_teacher_keys():
        return EmailTemplateType.get_keys(send_to_visit_added_teacher=True)

    @staticmethod
    def add_defaults_to_all():
        for product in Product.objects.all():
            for template_type in EmailTemplateType.objects.filter(
                enable_autosend=True
            ):
                qs = product.productautosend_set.filter(
                    template_type=template_type
                )
                if qs.count() == 0:
                    print "    create autosend type %d for product %d" % \
                          (template_type.key, product.id)
                    autosend = ProductAutosend(
                        template_key=template_type.key,
                        template_type=template_type,
                        product=product,
                        enabled=template_type.is_default
                    )
                    autosend.save()
                elif qs.count() > 1:
                    print "    removing extraneous autosend %d " \
                          "for product %d" % (template_type.key, product.id)
                    for extra in qs[1:]:
                        extra.delete()

        for visit in Visit.objects.all():
            if not visit.is_multiproductvisit:
                for template_type in EmailTemplateType.objects.filter(
                    enable_autosend=True
                ):
                    qs = visit.visitautosend_set.filter(
                        template_type=template_type
                    )
                    if qs.count() == 0:
                        print "    creating autosend type %d for visit %d" % \
                              (template_type.key, visit.id)
                        visitautosend = VisitAutosend(
                            visit=visit,
                            inherit=True,
                            template_key=template_type.key,
                            template_type=template_type,
                            days=None,
                            enabled=False
                        )
                        visitautosend.save()
                    elif qs.count() > 1:
                        print "    removing extraneous autosend %d " \
                              "for visit %d" % (template_type.key, visit.id)
                    for extra in qs[1:]:
                        extra.delete()

    @staticmethod
    def migrate():
        EmailTemplateType.set_defaults()
        EmailTemplate.migrate()
        Autosend.migrate()
        KUEmailMessage.migrate()


class EmailTemplate(models.Model):

    key = models.IntegerField(
        verbose_name=u'Type',
        default=1
    )

    type = models.ForeignKey(
        EmailTemplateType,
        null=True
    )

    subject = models.CharField(
        max_length=65584,
        verbose_name=u'Emne'
    )

    body = models.CharField(
        max_length=65584,
        verbose_name=u'Tekst'
    )

    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        verbose_name=u'Enhed',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    @property
    def name(self):
        return self.type.name

    def expand_subject(self, context, keep_placeholders=False):
        return self._expand(self.subject, context, keep_placeholders)

    def expand_body(self, context, keep_placeholders=False, encapsulate=False):
        body = self._expand(self.body, context, keep_placeholders)
        if encapsulate \
                and not body.startswith(("<html", "<HTML", "<!DOCTYPE")):
            body = "<!DOCTYPE html><html><head></head>" \
                   "<body>%s</body>" \
                   "</html>" % body
        return body

    default_includes = [
        "{% load booking_tags %}",
        "{% load i18n %}"
    ]

    @staticmethod
    def get_template_object(template_text):
        # Add default includes and encapsulate in danish
        return Template(
            "\n".join(EmailTemplate.default_includes) +
            "{% language 'da' %}\n" +
            unicode(template_text) +
            "{% endlanguage %}\n"
        )

    @staticmethod
    def _expand(text, context, keep_placeholders=False):
        template = EmailTemplate.get_template_object(text)

        if isinstance(context, dict):
            context = make_context(context)

        # This setting will affect the global template engine, so we have to
        # reset it below.
        if keep_placeholders:
            template.engine.string_if_invalid = "{{ %s }}"

        try:
            rendered = template.render(context)
        finally:
            # Reset string_if_invalid
            if keep_placeholders:
                template.engine.string_if_invalid = ''

        return rendered

    @staticmethod
    def get_template(template_type, unit, include_overridden=False):
        if type(template_type) == int:
            template_type = EmailTemplateType.get(template_type)
        templates = []
        while unit is not None and (include_overridden or len(templates) == 0):
            try:
                template = EmailTemplate.objects.filter(
                    type=template_type,
                    organizationalunit=unit
                ).first()
                if template is not None:
                    templates.append(template)
            except:
                pass
            unit = unit.parent
        if include_overridden or len(templates) == 0:
            try:
                template = EmailTemplate.objects.filter(
                    type=template_type,
                    organizationalunit__isnull=True
                ).first()
                if template is not None:
                    templates.append(template)
            except:
                pass
        if include_overridden:
            return templates
        else:
            return templates[0] if len(templates) > 0 else None

    @staticmethod
    def get_templates(unit, include_inherited=True):
        if unit is None:
            templates = EmailTemplate.objects.filter(
                organizationalunit__isnull=True
            ).all()
        else:
            templates = list(EmailTemplate.objects.filter(
                organizationalunit=unit
            ).all())
        if include_inherited and unit is not None and unit.parent != unit:
            templates.extend(EmailTemplate.get_templates(unit.parent, True))
        return templates

    def get_template_variables(self):
        variables = []
        for item in [self.subject, self.body]:
            text = item.replace("%20", " ")
            template = EmailTemplate.get_template_object(text)
            for node in template:
                if isinstance(node, VariableNode):
                    variables.append(unicode(node.filter_expression))
        return variables

    @staticmethod
    def migrate():
        for emailtemplate in EmailTemplate.objects.all():
            emailtemplate.type = EmailTemplateType.get(
                emailtemplate.key
            )
            emailtemplate.save()


class ObjectStatistics(models.Model):

    created_time = models.DateTimeField(
        blank=False,
        auto_now_add=True
    )
    updated_time = models.DateTimeField(
        blank=False,
        auto_now_add=True
    )
    visited_time = models.DateTimeField(
        blank=True,
        null=True,
    )
    display_counter = models.IntegerField(
        default=0
    )

    def on_display(self):
        self.display_counter += 1
        self.visited_time = timezone.now()
        self.save()

    def on_update(self):
        self.updated_time = timezone.now()
        self.save()


class ProductGymnasieFag(models.Model):
    class Meta:
        verbose_name = _(u"gymnasiefagtilknytning")
        verbose_name_plural = _(u"gymnasiefagtilknytninger")
        ordering = ["subject__name"]

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    product = models.ForeignKey("Product", blank=False, null=False)
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GYMNASIE,
                Subject.SUBJECT_TYPE_BOTH
            ]
        }
    )

    level = models.ManyToManyField('GymnasieLevel')

    @classmethod
    def create_from_submitvalue(cls, product, value):
        f = ProductGymnasieFag(product=product)

        values = value.split(",")

        # First element in value list is pk of subject
        f.subject = Subject.objects.get(pk=values.pop(0))

        f.save()

        # Rest of value list is pks for subject levels
        for x in values:
            l = GymnasieLevel.objects.get(pk=x)
            f.level.add(l)

        return f

    def __unicode__(self):
        return u"%s (for '%s')" % (self.display_value(), self.product.title)

    def ordered_levels(self):
        return [x for x in self.level.all().order_by('level')]

    @classmethod
    def display(cls, subject, levels):
        levels = [unicode(x) for x in levels]

        nr_levels = len(levels)
        if nr_levels == 1:
            levels_desc = levels[0]
        elif nr_levels == 2:
            levels_desc = u'%s eller %s' % (levels[0], levels[1])
        elif nr_levels > 2:
            last = levels.pop()
            levels_desc = u'%s eller %s' % (", ".join(levels), last)

        if levels_desc:
            return u'%s på %s niveau' % (
                unicode(subject.name), levels_desc
            )
        else:
            return unicode(subject.name)

    def display_value(self):
        return ProductGymnasieFag.display(
            self.subject, self.ordered_levels()
        )

    def as_submitvalue(self):
        res = unicode(self.subject.pk)
        levels = ",".join([unicode(x.pk) for x in self.ordered_levels()])

        if levels:
            res = ",".join([res, levels])

        return res


class ProductGrundskoleFag(models.Model):
    class Meta:
        verbose_name = _(u"grundskolefagtilknytning")
        verbose_name_plural = _(u"grundskolefagtilknytninger")
        ordering = ["subject__name"]

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    product = models.ForeignKey("Product", blank=False, null=False)
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GRUNDSKOLE,
                Subject.SUBJECT_TYPE_BOTH
            ]
        }
    )

    # TODO: We should validate that min <= max here.
    class_level_min = models.IntegerField(choices=class_level_choices,
                                          default=0,
                                          verbose_name=_(u'Klassetrin fra'))
    class_level_max = models.IntegerField(choices=class_level_choices,
                                          default=10,
                                          verbose_name=_(u'Klassetrin til'))

    @classmethod
    def create_from_submitvalue(cls, product, value):
        f = ProductGrundskoleFag(product=product)

        values = value.split(",")

        # First element in value list is pk of subject
        f.subject = Subject.objects.get(pk=values.pop(0))

        f.class_level_min = values.pop(0) or 0
        f.class_level_max = values.pop(0) or 0

        f.save()

        return f

    def __unicode__(self):
        return u"%s (for '%s')" % (self.display_value(), self.product.title)

    @classmethod
    def display(cls, subject, clevel_min, clevel_max):
        class_range = []
        if clevel_min is not None:
            class_range.append(clevel_min)
            if clevel_max != clevel_min:
                class_range.append(clevel_max)
        else:
            if clevel_max:
                class_range.append(clevel_max)

        if len(class_range) > 0:
            return u'%s på klassetrin %s' % (
                subject.name,
                "-".join([unicode(x) for x in class_range])
            )
        else:
            return unicode(subject.name)

    def display_value(self):
        return ProductGrundskoleFag.display(
            self.subject, self.class_level_min, self.class_level_max
        )

    def as_submitvalue(self):
        return ",".join([
            unicode(self.subject.pk),
            unicode(self.class_level_min or 0),
            unicode(self.class_level_max or 0)
        ])


class GymnasieLevel(models.Model):

    class Meta:
        verbose_name = _(u'Gymnasieniveau')
        verbose_name_plural = _(u'Gymnasieniveauer')
        ordering = ['level']

    # Level choices - A, B or C
    A = 0
    B = 1
    C = 2

    level_choices = (
        (A, u'A'), (B, u'B'), (C, u'C')
    )

    level = models.IntegerField(choices=level_choices,
                                verbose_name=_(u"Gymnasieniveau"),
                                blank=True,
                                null=True)

    @classmethod
    def create_defaults(cls):
        for val, desc in GymnasieLevel.level_choices:
            try:
                GymnasieLevel.objects.filter(level=val)[0]
            except IndexError:
                o = GymnasieLevel(level=val)
                o.save()

    def __unicode__(self):
        return self.get_level_display()


class GrundskoleLevel(models.Model):

    class Meta:
        verbose_name = _(u'Grundskoleniveau')
        verbose_name_plural = _(u'Grundskoleniveauer')
        ordering = ['level']

    f0 = 0
    f1 = 1
    f2 = 2
    f3 = 3
    f4 = 4
    f5 = 5
    f6 = 6
    f7 = 7
    f8 = 8
    f9 = 9
    f10 = 10

    level_choices = (
        (f0, _(u'0. klasse')),
        (f1, _(u'1. klasse')),
        (f2, _(u'2. klasse')),
        (f3, _(u'3. klasse')),
        (f4, _(u'4. klasse')),
        (f5, _(u'5. klasse')),
        (f6, _(u'6. klasse')),
        (f7, _(u'7. klasse')),
        (f8, _(u'8. klasse')),
        (f9, _(u'9. klasse')),
        (f10, _(u'10. klasse')),
    )

    level = models.IntegerField(choices=level_choices,
                                verbose_name=_(u"Grundskoleniveau"),
                                blank=True,
                                null=True)

    @classmethod
    def create_defaults(cls):
        for val, desc in GrundskoleLevel.level_choices:
            try:
                GrundskoleLevel.objects.filter(level=val)[0]
            except IndexError:
                o = GrundskoleLevel(level=val)
                o.save()

    def __unicode__(self):
        return self.get_level_display()


class Product(AvailabilityUpdaterMixin, models.Model):
    """A bookable Product of any kind."""

    class Meta:
        verbose_name = _("tilbud")
        verbose_name_plural = _("tilbud")

    # Product type.
    STUDENT_FOR_A_DAY = 0
    GROUP_VISIT = 1
    _UNUSED = 2
    STUDY_PROJECT = 3
    OTHER_OFFERS = 4
    STUDY_MATERIAL = 5
    TEACHER_EVENT = 6
    OPEN_HOUSE = 7
    ASSIGNMENT_HELP = 8
    STUDIEPRAKTIK = 9

    resource_type_choices = (
        (STUDENT_FOR_A_DAY, _(u"Studerende for en dag")),
        (STUDIEPRAKTIK, _(u"Studiepraktik")),
        (OPEN_HOUSE, _(u"Åbent hus")),
        (TEACHER_EVENT, _(u"Lærerarrangement")),
        (GROUP_VISIT, _(u"Besøg med klassen")),
        (STUDY_PROJECT, _(u"Studieretningsprojekt")),
        (ASSIGNMENT_HELP, _(u"Lektiehjælp")),
        (OTHER_OFFERS,  _(u"Andre tilbud")),
        (STUDY_MATERIAL, _(u"Undervisningsmateriale"))
    )

    # Institution choice - primary or secondary school.
    PRIMARY = 0
    SECONDARY = 1

    institution_choices = Subject.type_choices

    # Level choices - A, B or C
    A = 0
    B = 1
    C = 2

    level_choices = (
        (A, u'A'), (B, u'B'), (C, u'C')
    )

    # Product state - created, active and discontinued.
    CREATED = 0
    ACTIVE = 1
    DISCONTINUED = 2

    state_choices = (
        BLANK_OPTION,
        (CREATED, _(u"Under udarbejdelse")),
        (ACTIVE, _(u"Offentlig")),
        (DISCONTINUED, _(u"Skjult"))
    )

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    type = models.IntegerField(choices=resource_type_choices,
                               default=STUDY_MATERIAL)
    state = models.IntegerField(choices=state_choices,
                                verbose_name=_(u"Status"), blank=False)
    title = models.CharField(
        max_length=60,
        blank=False,
        verbose_name=_(u'Titel')
    )
    teaser = models.TextField(
        max_length=210,
        blank=False,
        verbose_name=_(u'Teaser')
    )
    description = models.TextField(
        blank=False,
        verbose_name=_(u'Beskrivelse')
    )
    mouseover_description = models.CharField(
        max_length=512, blank=True, verbose_name=_(u'Mouseover-tekst')
    )
    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        null=True,
        blank=False,
        verbose_name=_('Enhed'),
        on_delete=models.SET_NULL,
    )
    links = models.ManyToManyField(Link, blank=True, verbose_name=_('Links'))

    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY,
                                            blank=False)

    locality = models.ForeignKey(
        Locality,
        verbose_name=_(u'Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    rooms = models.ManyToManyField(
        'Room',
        verbose_name=_(u'Lokaler'),
        blank=True
    )

    TIME_MODE_NONE = 1
    TIME_MODE_RESOURCE_CONTROLLED = 2
    TIME_MODE_SPECIFIC = 3
    TIME_MODE_GUEST_SUGGESTED = 4
    TIME_MODE_NO_BOOKING = 5
    TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN = 6

    time_mode_choice_map = {
        STUDENT_FOR_A_DAY: set((
            TIME_MODE_SPECIFIC,
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
        )),
        STUDIEPRAKTIK: set((
            TIME_MODE_SPECIFIC,
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
        )),
        OPEN_HOUSE: set((
            TIME_MODE_NO_BOOKING,
        )),
        TEACHER_EVENT: set((
            TIME_MODE_SPECIFIC,
        )),
        GROUP_VISIT: set((
            TIME_MODE_SPECIFIC,
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
        )),
        STUDY_PROJECT: set((
            TIME_MODE_SPECIFIC,
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
        )),
        ASSIGNMENT_HELP: set((
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
        )),
        OTHER_OFFERS: set((
            TIME_MODE_SPECIFIC,
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
        )),
        STUDY_MATERIAL: set((
            TIME_MODE_NONE,
        )),
    }

    time_mode_choices = (
        (TIME_MODE_NONE,
         _(u"Tilbuddet har ingen tidspunkter og ingen tilmelding")),
        (TIME_MODE_RESOURCE_CONTROLLED,
         _(u"Tilbuddets tidspunkter styres af ressourcer")),
        (TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN,
         _(u"Tilbuddets tidspunkter styres af ressourcer,"
           u" med automatisk tildeling")),
        (TIME_MODE_SPECIFIC,
         _(u"Tilbuddet har faste tidspunkter")),
        (TIME_MODE_NO_BOOKING,
         _(u"Tilbuddet har faste tidspunkter, men er uden tilmelding")),
        (TIME_MODE_GUEST_SUGGESTED,
         _(u"Gæster foreslår mulige tidspunkter")),
    )

    # Note: Default here is a type that can not be selected in the dropdown.
    # This is to get that default on products that does not have a form field
    # for time_mode. Products that does a have a form field will have to
    # choose a specific time mode.
    time_mode = models.IntegerField(
        verbose_name=_(u"Håndtering af tidspunkter"),
        choices=time_mode_choices,
        default=TIME_MODE_NONE,
    )

    tilbudsansvarlig = models.ForeignKey(
        User,
        verbose_name=_(u'Tilbudsansvarlig'),
        related_name='tilbudsansvarlig_for_set',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    roomresponsible = models.ManyToManyField(
        RoomResponsible,
        verbose_name=_(u'Lokaleansvarlige'),
        related_name='ansvarlig_for_besoeg_set',
        blank=True,
    )

    potentielle_undervisere = models.ManyToManyField(
        User,
        verbose_name=_(u'Potentielle undervisere'),
        related_name='potentiel_underviser_for_set',
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
    )

    potentielle_vaerter = models.ManyToManyField(
        User,
        verbose_name=_(u'Potentielle værter'),
        related_name='potentiel_vaert_for_set',
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
    )

    preparation_time = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_(u'Forberedelsestid')
    )

    price = models.DecimalField(
        default=0,
        null=True,
        blank=True,
        max_digits=10,
        decimal_places=2,
        verbose_name=_(u'Pris')
    )

    gymnasiefag = models.ManyToManyField(
        Subject, blank=True,
        verbose_name=_(u'Gymnasiefag'),
        through='ProductGymnasieFag',
        related_name='gymnasie_resources'
    )

    grundskolefag = models.ManyToManyField(
        Subject, blank=True,
        verbose_name=_(u'Grundskolefag'),
        through='ProductGrundskoleFag',
        related_name='grundskole_resources'
    )

    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_(u'Tags'))
    topics = models.ManyToManyField(
        Topic, blank=True, verbose_name=_(u'Emner')
    )

    # Comment field for internal use in backend.
    comment = models.TextField(blank=True, verbose_name=_(u'Kommentar'))

    created_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        verbose_name=_(u"Oprettet af"),
        related_name='created_visits_set',
        on_delete=models.SET_NULL
    )

    # ts_vector field for fulltext search
    search_index = VectorField()

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Tekst-værdier til fritekstsøgning'),
        editable=False
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True,
        on_delete=models.SET_NULL,
    )

    calendar = models.OneToOneField(
        'Calendar',
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    objects = SearchManager(
        fields=(
            'title',
            'teaser',
            'description',
            'mouseover_description',
            'extra_search_text'
        ),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    applicable_types = [
        STUDENT_FOR_A_DAY, GROUP_VISIT,
        TEACHER_EVENT, OTHER_OFFERS, STUDY_MATERIAL,
        OPEN_HOUSE, ASSIGNMENT_HELP, STUDIEPRAKTIK,
        STUDY_PROJECT
    ]

    bookable_types = [
        STUDENT_FOR_A_DAY, GROUP_VISIT,
        TEACHER_EVENT, STUDY_PROJECT
    ]

    askable_types = [
        STUDENT_FOR_A_DAY, GROUP_VISIT,
        TEACHER_EVENT, OTHER_OFFERS,
        OPEN_HOUSE, ASSIGNMENT_HELP, STUDIEPRAKTIK,
        STUDY_PROJECT
    ]

    @ClassProperty
    def type_choices(self):
        return (x for x in
                Product.resource_type_choices
                if x[0] in Product.applicable_types)

    rooms_needed = models.BooleanField(
        default=True,
        verbose_name=_(u"Tilbuddet kræver brug af et eller flere lokaler")
    )

    duration_choices = []
    for hour in range(0, 12, 1):
        for minute in range(0, 60, 15):
            value = "%.2d:%.2d" % (hour, minute)
            duration_choices.append((value, value),)

    duration = models.CharField(
        max_length=8,
        verbose_name=_(u'Varighed'),
        blank=True,
        null=True,
        choices=duration_choices
    )

    do_send_evaluation = models.BooleanField(
        verbose_name=_(u"Udsend evaluering"),
        default=False
    )
    is_group_visit = models.BooleanField(
        default=True,
        verbose_name=_(u'Gruppebesøg')
    )
    # Min/max number of visitors - only relevant for group visits.
    minimum_number_of_visitors = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Mindste antal deltagere')
    )
    maximum_number_of_visitors = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Højeste antal deltagere')
    )

    # Waiting lists
    do_create_waiting_list = models.BooleanField(
        default=False,
        verbose_name=_(u'Ventelister')
    )
    waiting_list_length = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Antal pladser')
    )
    waiting_list_deadline_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Lukning af venteliste (dage inden besøg)')
    )
    waiting_list_deadline_hours = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Lukning af venteliste (timer inden besøg)')
    )

    do_show_countdown = models.BooleanField(
        default=False,
        verbose_name=_(u'Vis nedtælling')
    )

    tour_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_(u'Mulighed for rundvisning')
    )

    catering_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_(u'Mulighed for forplejning')
    )

    presentation_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_(u'Mulighed for oplæg om uddannelse')
    )

    custom_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_(u'Andet')
    )

    custom_name = models.CharField(
        blank=True,
        null=True,
        verbose_name=_(u'Navn for tilpasset mulighed'),
        max_length=50
    )

    NEEDED_NUMBER_NONE = 0
    NEEDED_NUMBER_MORE_THAN_TEN = -10

    needed_number_choices = [
        BLANK_OPTION,
        (NEEDED_NUMBER_NONE, _(u'Ingen'))
    ] + [
        (x, unicode(x)) for x in range(1, 11)
    ] + [
        (NEEDED_NUMBER_MORE_THAN_TEN, _(u'Mere end 10'))
    ]

    needed_hosts = models.IntegerField(
        default=0,
        verbose_name=_(u'Nødvendigt antal værter'),
        choices=needed_number_choices,
        blank=False
    )

    needed_teachers = models.IntegerField(
        default=0,
        verbose_name=_(u'Nødvendigt antal undervisere'),
        choices=needed_number_choices,
        blank=False
    )

    def available_time_modes(self, unit=None):
        if self.type is None:
            return Product.time_mode_choices

        available_set = Product.time_mode_choice_map.get(self.type)
        if Product.TIME_MODE_RESOURCE_CONTROLLED in available_set \
                and unit is not None and unit.autoassign_resources_enabled:
            available_set.add(Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN)

        return tuple(
            x for x in Product.time_mode_choices if x[0] in available_set
        )

    @property
    def total_required_hosts(self):
        if self.is_resource_controlled:
            return self.resourcerequirement_set.filter(
                resource_pool__resource_type=ResourceType.RESOURCE_TYPE_HOST
            ).aggregate(
                total_required=Sum('required_amount')
            )['total_required'] or 0
        else:
            return int(self.needed_hosts)

    @property
    def total_required_teachers(self):
        if self.is_resource_controlled:
            return self.resourcerequirement_set.filter(
                resource_pool__resource_type=ResourceType.RESOURCE_TYPE_TEACHER
            ).aggregate(
                total_required=Sum('required_amount')
            )['total_required'] or 0
        else:
            return int(self.needed_teachers)

    @property
    def total_required_rooms(self):
        if self.is_resource_controlled:
            return self.resourcerequirement_set.filter(
                resource_pool__resource_type=ResourceType.RESOURCE_TYPE_ROOM
            ).aggregate(
                total_required=Sum('required_amount')
            )['total_required'] or 0
        else:
            return 1

    @property
    def bookable_times(self):
        qs = self.eventtime_set.filter(
            Q(bookable=True) &
            (
                Q(visit__isnull=True) |
                Q(visit__workflow_status__in=Visit.BOOKABLE_STATES)
            ) &
            (~Q(resource_status=EventTime.RESOURCE_STATUS_BLOCKED))
        )
        if self.maximum_number_of_visitors is not None:
            max = (self.maximum_number_of_visitors +
                   (self.waiting_list_length or 0))
            qs = qs.annotate(
                attendees=Coalesce(
                    Sum('visit__bookings__booker__attendee_count'),
                    0
                )
            ).filter(
                Q(visit__isnull=True) |
                Q(attendees__lt=max)
            )
        return qs

    @property
    def future_times(self):
        return self.eventtime_set.filter(start__gte=timezone.now())

    @property
    def future_bookable_times(self):
        return self.bookable_times.filter(start__gte=timezone.now())

    @property
    # QuerySet that finds all EventTimes that will be affected by a change
    # in ressource assignment for this product.
    # Finds:
    #  - All potential ressources that can be assigned to this product
    #  - All ResourcePools that make use of these resources
    #  - All EventTimes for products that has requirements that uses these
    #    ResourcePools.
    def affected_eventtimes(self):
        potential_resources = Resource.objects.filter(
            resourcepool__resourcerequirement__product=self
        )
        resource_pools = ResourcePool.objects.filter(
            resources=potential_resources
        )
        return EventTime.objects.filter(
            product__resourcerequirement__resource_pool=resource_pools
        )

    def update_availability(self):
        for x in self.affected_eventtimes:
            x.update_availability()

    def get_dates_display(self):
        dates = [x.interval_display for x in self.eventtime_set.all()]
        if len(dates) > 0:
            return ", ".join(dates)
        else:
            return "-"

    def num_of_participants_display(self):
        if self.minimum_number_of_visitors and self.maximum_number_of_visitors:
            return "%d - %d" % (
                self.minimum_number_of_visitors,
                self.maximum_number_of_visitors
            )
        elif self.maximum_number_of_visitors:
            return _(u"Max. %(visitors)d") % \
                {'visitors': self.maximum_number_of_visitors}
        elif self.minimum_number_of_visitors:
            return _(u"Min. %(visitors)d") % \
                {'visitors': self.minimum_number_of_visitors}
        else:
            return None

    def get_absolute_url(self):
        return reverse('product-view', args=[self.pk])

    def get_autosends(self, include_disabled=False):
        if include_disabled:
            return self.productautosend_set.all()
        else:
            return self.productautosend_set.filter(enabled=True)

    def get_autosend(self, template_type):
        if type(template_type) == int:
            template_type = EmailTemplateType.get(template_type)
        try:
            item = self.productautosend_set.filter(
                template_type=template_type, enabled=True)[0]
            return item
        except:
            return None

    def autosend_enabled(self, template_type):
        return self.get_autosend(template_type) is not None

    # This is used from booking.signals.update_search_indexes
    def update_searchindex(self):
        if not self.pk:
            return False

        old_value = self.extra_search_text or ""
        new_value = self.generate_extra_search_text() or ""

        if old_value != new_value:
            self.extra_search_text = new_value
            self.save()
            return True
        else:
            return False

    def generate_extra_search_text(self):
        texts = []

        # Display-value for type
        texts.append(self.get_type_display() or "")

        # Unit name
        if self.organizationalunit:
            texts.append(self.organizationalunit.name)

            # Unit's parent name
            if self.organizationalunit.parent:
                texts.append(self.organizationalunit.parent.name)

        # Url, name and description of all links
        for l in self.links.all():
            if l.url:
                texts.append(l.url)
            if l.name:
                texts.append(l.name)
            if l.description:
                texts.append(l.description)

        # Display-value for institution_level
        texts.append(self.get_institution_level_display() or "")

        # All subjects
        for x in self.all_subjects():
            texts.append(x.display_value())

        # Name of all tags
        for t in self.tags.all():
            texts.append(t.name)

        # Name of all topocs
        for t in self.topics.all():
            texts.append(t.name)

        return "\n".join(texts)

    def as_searchtext(self):
        return " ".join([unicode(x) for x in [
            self.pk,
            self.title,
            self.teaser,
            self.description,
            self.mouseover_description,
            self.extra_search_text
        ] if x])

    def all_subjects(self):
        return (
            [x for x in self.productgymnasiefag_set.all()] +
            [x for x in self.productgrundskolefag_set.all()]
        )

    def display_locality(self):
        try:
            return self.locality
        except Product.DoesNotExist:
            pass
        return "-"

    def get_url(self):
        return settings.PUBLIC_URL + self.get_absolute_url()

    def url(self):
        return self.get_url()

    def get_visits(self):
        return Visit.objects.filter(eventtime__product=self)

    def first_visit(self):
        return self.get_visits().first()

    def get_state_class(self):
        if self.state == self.CREATED:
            return 'info'
        elif self.state == self.ACTIVE:
            return 'primary'
        else:
            return 'default'

    @property
    def potential_hosts(self):
        if self.is_resource_controlled:
            p = self
            return User.objects.filter(
                hostresource__resourcepool__resourcerequirement__product=p
            )
        else:
            return self.potentielle_vaerter.all()

    @property
    def potential_teachers(self):
        if self.is_resource_controlled:
            p = self
            return User.objects.filter(
                teacherresource__resourcepool__resourcerequirement__product=p
            )
        else:
            return self.potentielle_undervisere.all()

    def get_recipients(self, template_type):
        recipients = self.organizationalunit.get_recipients(template_type)

        if template_type.send_to_potential_hosts:
            recipients.extend(self.potential_hosts.all())

        if template_type.send_to_potential_teachers:
            recipients.extend(self.potential_teachers.all())

        if template_type.send_to_contactperson:
            contacts = []
            if self.inquire_user:
                contacts.append(self.inquire_user)
            recipients.extend(contacts)

        return recipients

    def get_reply_recipients(self, template_type):
        recipients = self.organizationalunit.get_reply_recipients(
            template_type
        )
        if template_type.reply_to_product_responsible:
            recipients.extend(self.get_responsible_persons())
        return recipients

    # Returns best guess for who is responsible for visits for this product.
    def get_responsible_persons(self):
        if self.tilbudsansvarlig:
            return [self.tilbudsansvarlig]

        if self.created_by:
            return [self.created_by]

        return self.organizationalunit.get_editors()

    def get_view_url(self):
        return reverse('product-view', args=[self.pk])

    def add_room_by_name(self, name):
        room = Room.objects.filter(
            name=name,
            locality=self.locality
        ).first()

        if room is None:
            room = Room(
                name=name,
                locality=self.locality
            )
            room.save()

        self.rooms.add(room)

        return room

    def can_be_held_between(self, from_dt, to_dt):
        for x in self.resourcepool_set.all():
            if not x.can_be_fullfilled_between(from_dt, to_dt):
                return False

        return True

    @staticmethod
    def get_latest_created(user=None):
        qs = Product.objects.filter(statistics__isnull=False).\
            order_by('-statistics__created_time')

        if user and not user.is_authenticated():
            return Product.filter_public_bookable(qs).distinct()
        else:
            return qs

    @staticmethod
    def get_latest_updated(user=None):
        qs = Product.objects.filter(statistics__isnull=False).\
            order_by('-statistics__updated_time')

        if user and not user.is_authenticated():
            return Product.filter_public_bookable(qs).distinct()
        else:
            return qs

    @staticmethod
    def get_latest_displayed(user=None):
        qs = Product.objects.filter(statistics__isnull=False).\
            order_by('-statistics__visited_time')

        if user and not user.is_authenticated():
            return Product.filter_public_bookable(qs).distinct()
        else:
            return qs

    @classmethod
    def filter_public_bookable(cls, queryset):
        nonblocked = EventTime.NONBLOCKED_RESOURCE_STATES
        resource_controlled = [
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN
        ]
        return queryset.filter(
            Q(time_mode=cls.TIME_MODE_GUEST_SUGGESTED) |
            Q(
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
                    eventtime__resource_status__in=nonblocked
                )
            )
        ).filter(state=cls.ACTIVE)

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()

    @property
    def is_type_bookable(self):
        return self.type in self.bookable_types

    @property
    def has_bookable_visits(self):
        if self.time_mode == Product.TIME_MODE_GUEST_SUGGESTED:
            return True
        if self.time_mode in (
            Product.TIME_MODE_NONE,
            Product.TIME_MODE_NO_BOOKING
        ):
            return False

        # Time controlled products are only bookable if there's a valid
        # bookable time in the future, and that time isn't fully booked
        # if len(self.future_bookable_times) > 0:
        #     return True
        for eventtime in self.future_bookable_times:
            if eventtime.visit is None:
                return True
            if eventtime.visit.is_bookable:
                return True

        return False

    @property
    def has_waitinglist_visit_spots(self):
        for t in self.future_times:
            if t.visit and t.visit.can_join_waitinglist:
                return True
        return False

    @property
    def fixed_waiting_list_capacity(self):
        if not self.do_create_waiting_list:
            return 0
        if self.waiting_list_length is None:
            return INFINITY
        elif self.waiting_list_length <= 0:
            return 0
        else:
            return None

    def is_bookable(self, start_time=None, end_time=None):

        if not(
            self.is_type_bookable and
            self.state == Product.ACTIVE and
            self.has_bookable_visits
        ):
            return False

        # Special case for calendar-controlled products where guest suggests
        # a date
        if self.time_mode == Product.TIME_MODE_GUEST_SUGGESTED:
            # If no time was specified, we assume there is some time where
            # the product is available:
            if start_time is None:
                return True

            # If start_time is a date and there is no end_date assume
            # midnight-to-midnight on the given date in the current timezone.
            if end_time is None and isinstance(start_time, date):
                # Start time is midnight
                start_time = timezone.make_aware(
                    datetime.combine(start_time, time())
                )
                end_time = start_time + timedelta(hours=24)

            # Check if we has an available time in our calendar within the
            # specified interval.
            return self.has_available_calendar_time(start_time, end_time)

        return True

    @property
    def is_resource_controlled(self):
        return self.time_mode in [
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN
        ]

    @property
    def is_guest_time_suggested(self):
        return self.time_mode == Product.TIME_MODE_GUEST_SUGGESTED

    @property
    def is_time_controlled(self):
        return self.time_mode != Product.TIME_MODE_NONE

    @property
    def are_resources_autoassigned(self):
        return self.time_mode == \
               Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN

    def has_time_management(self):
        return self.time_mode not in (
            Product.TIME_MODE_NONE,
            Product.TIME_MODE_GUEST_SUGGESTED
        )

    @property
    def can_join_waitinglist(self):
        return self.is_type_bookable and \
            self.state == Product.ACTIVE and \
            self.has_waitinglist_visit_spots

    @property
    def inquire_user(self):
        return self.tilbudsansvarlig or self.created_by

    @property
    def can_inquire(self):
        return self.type in Product.askable_types and self.inquire_user

    @property
    def duration_as_timedelta(self):
        if self.duration is not None and ':' in self.duration:
            (hours, minutes) = self.duration.split(":")
            return timedelta(
                hours=int(hours),
                minutes=int(minutes)
            )

    @property
    def duration_display(self):
        if not self.duration:
            return ""
        (hours, minutes) = self.duration.split(":")
        try:
            hours = int(hours)
            minutes = int(minutes)
            parts = []
            if hours == 1:
                parts.append(_(u"1 time"))
            elif hours > 1:
                parts.append(_(u"%s timer") % hours)
            if minutes == 1:
                parts.append(_(u"1 minut"))
            else:
                parts.append(_(u"%s minutter") % minutes)

            return _(u" og ").join([unicode(x) for x in parts])
        except Exception as e:
            print e
            return ""

    @staticmethod
    def get_latest_booked(user=None):
        qs = Product.objects.filter(
            eventtime__visit__bookings__statistics__created_time__isnull=False
        ).annotate(latest_booking=Max(
            'eventtime__visit__bookings__statistics__created_time'
        )).order_by("-latest_booking")

        if user and not user.is_authenticated():
            return Product.filter_public_bookable(qs).distinct()
        else:
            return qs

    @property
    def room_responsible_users(self):
        return self.roomresponsible.all()

    @property
    def uses_time_management(self):
        return self.time_mode is not None and self.time_mode in (
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN,
            Product.TIME_MODE_SPECIFIC,
        )

    @property
    def duration_in_minutes(self):
        result = 0
        if self.duration:
            parts = self.duration.split(":")
            try:
                result = int(parts[0]) * 60 + int(parts[1])
            except:
                pass
        return result

    @property
    def latest_starttime(self):
        mins = 60 * 24 - self.duration_in_minutes
        return u'%.2d:%.2d' % (math.floor(mins / 60), mins % 60)

    def get_duration_display(self):
        mins = self.duration_in_minutes
        if mins > 0:
            hours = math.floor(mins / 60)
            mins = mins % 60
            if(hours == 1):
                return _(u"1 time og %(minutes)d minutter") % {'minutes': mins}
            else:
                return _(u"%(hours)d timer og %(minutes)d minutter") % {
                    'hours': hours, 'minutes': mins
                }
        else:
            return ""

    def make_calendar(self):
        if not self.calendar:
            cal = Calendar()
            cal.save()
            self.calendar = cal
            self.save()

    def has_available_calendar_time(self, from_dt, to_dt):
        if self.calendar:
            minutes = self.duration_in_minutes
            # Fall back to one hour if no duration is specified
            if minutes == 0:
                minutes = 60
            return self.calendar.has_available_time(
                from_dt, to_dt, minutes
            )
        else:
            return True

    def occupied_eventtimes(self, dt_from=None, dt_to=None):
        qs = self.eventtime_set.filter(
            visit__isnull=False,
            start__isnull=False,
            end__isnull=False,
        ).exclude(
            visit__workflow_status=Visit.WORKFLOW_STATUS_CANCELLED
        )
        if dt_from:
            qs = qs.filter(end__gt=dt_from)
        if dt_to:
            qs = qs.filter(start__lt=dt_to)

        return qs

    def booked_eventtimes(self, dt_from=None, dt_to=None):
        return self.occupied_eventtimes(dt_from, dt_to).filter(
            visit__bookings__isnull=False
        ).distinct()

    @classmethod
    # Migrate from old system where guest-suggest-time products was determined
    # by them not having any visits
    def migrate_time_mode(cls):
        for x in cls.objects.filter(time_mode=cls.TIME_MODE_NONE):
            if x.visit_set.filter(deprecated_bookable=True).count() > 0:
                x.time_mode = cls.TIME_MODE_SPECIFIC
            else:
                x.time_mode = cls.TIME_MODE_GUEST_SUGGESTED

            print u"%s => %s" % (x, x.get_time_mode_display())
            x.save()

        # EventTimes with TIME_MODE_GUEST_SUGGESTED should not be bookable:
        EventTime.objects.filter(
            bookable=True,
            product__time_mode=cls.TIME_MODE_GUEST_SUGGESTED
        ).update(bookable=False)

    def __unicode__(self):
        return _(u"Tilbud #%(pk)s - %(title)s") % \
            {'pk': self.pk, 'title': self.title}


class Visit(AvailabilityUpdaterMixin, models.Model):

    class Meta:
        verbose_name = _(u"besøg")
        verbose_name_plural = _(u"besøg")
        ordering = ['id']

    objects = SearchManager(
        fields=('extra_search_text'),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    deprecated_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    deprecated_start_datetime = models.DateTimeField(
        verbose_name=_(u'Starttidspunkt'),
        null=True,
        blank=True
    )

    deprecated_end_datetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Whether the visit is publicly bookable
    deprecated_bookable = models.BooleanField(
        default=False,
        verbose_name=_(u'Kan bookes')
    )

    desired_time = models.CharField(
        null=True,
        blank=True,
        max_length=2000,
        verbose_name=u'Ønsket tidspunkt'
    )

    override_duration = models.CharField(
        max_length=8,
        verbose_name=_(u'Varighed'),
        blank=True,
        null=True,
    )

    override_locality = models.ForeignKey(
        Locality,
        verbose_name=_(u'Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    rooms = models.ManyToManyField(
        'Room',
        verbose_name=_(u'Lokaler'),
        blank=True
    )

    persons_needed_choices = (
        (None, _(u"Brug værdi fra tilbud")),
    ) + tuple((x, x) for x in range(1, 10))

    override_needed_hosts = models.IntegerField(
        verbose_name=_(u"Antal nødvendige værter"),
        choices=persons_needed_choices,
        blank=True,
        null=True
    )

    hosts = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
        related_name="hosted_visits",
        verbose_name=_(u'Tilknyttede værter')
    )

    hosts_rejected = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
        related_name='rejected_hosted_visits',
        verbose_name=_(u'Værter, som har afslået')
    )

    override_needed_teachers = models.IntegerField(
        verbose_name=_(u"Antal nødvendige undervisere"),
        choices=persons_needed_choices,
        blank=True,
        null=True
    )

    teachers = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
        related_name="taught_visits",
        verbose_name=_(u'Tilknyttede undervisere')
    )

    teachers_rejected = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
        related_name='rejected_taught_visits',
        verbose_name=_(u'Undervisere, som har afslået')
    )

    STATUS_NOT_NEEDED = 0
    STATUS_ASSIGNED = 1
    STATUS_NOT_ASSIGNED = 2

    room_status_choices = (
        (STATUS_NOT_NEEDED, _(u'Tildeling af lokaler ikke påkrævet')),
        (STATUS_NOT_ASSIGNED, _(u'Afventer tildeling/bekræftelse')),
        (STATUS_ASSIGNED, _(u'Tildelt/bekræftet'))
    )

    room_status = models.IntegerField(
        choices=room_status_choices,
        default=STATUS_NOT_ASSIGNED,
        verbose_name=_(u'Status for tildeling af lokaler')
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True,
        on_delete=models.SET_NULL,
    )

    resources = models.ManyToManyField(
        "Resource",
        through="VisitResource",
        blank=True,
        verbose_name=_(u'Besøgets ressourcer')
    )

    WORKFLOW_STATUS_BEING_PLANNED = 0
    WORKFLOW_STATUS_REJECTED = 1
    WORKFLOW_STATUS_PLANNED = 2
    WORKFLOW_STATUS_CONFIRMED = 3
    WORKFLOW_STATUS_REMINDED = 4
    WORKFLOW_STATUS_EXECUTED = 5
    WORKFLOW_STATUS_EVALUATED = 6
    WORKFLOW_STATUS_CANCELLED = 7
    WORKFLOW_STATUS_NOSHOW = 8
    WORKFLOW_STATUS_PLANNED_NO_BOOKING = 9
    WORKFLOW_STATUS_AUTOASSIGN_FAILED = 10

    BEING_PLANNED_STATUS_TEXT = u'Under planlægning'
    PLANNED_STATUS_TEXT = u'Planlagt (ressourcer tildelt)'
    PLANNED_NOBOOKING_TEXT = u'Planlagt og lukket for booking'

    status_to_class_map = {
        WORKFLOW_STATUS_BEING_PLANNED: 'danger',
        WORKFLOW_STATUS_REJECTED: 'danger',
        WORKFLOW_STATUS_PLANNED: 'success',
        WORKFLOW_STATUS_CONFIRMED: 'success',
        WORKFLOW_STATUS_REMINDED: 'success',
        WORKFLOW_STATUS_EXECUTED: 'success',
        WORKFLOW_STATUS_EVALUATED: 'success',
        WORKFLOW_STATUS_CANCELLED: 'success',
        WORKFLOW_STATUS_NOSHOW: 'success',
        WORKFLOW_STATUS_PLANNED_NO_BOOKING: 'success',
        WORKFLOW_STATUS_AUTOASSIGN_FAILED: 'danger',
    }

    BOOKABLE_STATES = set([
        WORKFLOW_STATUS_BEING_PLANNED,
        WORKFLOW_STATUS_PLANNED,
        WORKFLOW_STATUS_AUTOASSIGN_FAILED
    ])

    workflow_status_choices = (
        (WORKFLOW_STATUS_BEING_PLANNED, _(BEING_PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_REJECTED, _(u'Afvist af undervisere eller værter')),
        (WORKFLOW_STATUS_PLANNED, _(PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_PLANNED_NO_BOOKING, _(PLANNED_NOBOOKING_TEXT)),
        (WORKFLOW_STATUS_CONFIRMED, _(u'Bekræftet af gæst')),
        (WORKFLOW_STATUS_REMINDED, _(u'Påmindelse afsendt')),
        (WORKFLOW_STATUS_EXECUTED, _(u'Afviklet')),
        (WORKFLOW_STATUS_EVALUATED, _(u'Evalueret')),
        (WORKFLOW_STATUS_CANCELLED, _(u'Aflyst')),
        (WORKFLOW_STATUS_NOSHOW, _(u'Udeblevet')),
        (WORKFLOW_STATUS_AUTOASSIGN_FAILED, _(u'Automatisk tildeling fejlet')),
    )

    workflow_status = models.IntegerField(
        choices=workflow_status_choices,
        default=WORKFLOW_STATUS_BEING_PLANNED
    )

    last_workflow_update = models.DateTimeField(default=timezone.now)
    needs_attention_since = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        verbose_name=_(u'Behov for opmærksomhed siden')
    )

    comments = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Interne kommentarer')
    )

    evaluation_link = models.CharField(
        max_length=1024,
        verbose_name=_(u'Link til evaluering'),
        blank=True,
        default='',
    )

    # ts_vector field for fulltext search
    search_index = VectorField()

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Tekst-værdier til fritekstsøgning'),
        editable=False
    )

    multi_master = models.ForeignKey(
        "MultiProductVisit",
        null=True,
        blank=True,
        related_name='subvisit',
        on_delete=models.SET_NULL
    )
    multi_priority = models.IntegerField(
        default=0
    )
    is_multi_sub = models.BooleanField(
        default=False
    )

    @property
    def organizationalunit(self):
        if self.product:
            return self.product.organizationalunit
        else:
            return None

    valid_status_changes = {
        WORKFLOW_STATUS_BEING_PLANNED: [
            WORKFLOW_STATUS_REJECTED,
            WORKFLOW_STATUS_PLANNED,
            WORKFLOW_STATUS_CANCELLED,
        ],
        WORKFLOW_STATUS_REJECTED: [
            WORKFLOW_STATUS_BEING_PLANNED,
            WORKFLOW_STATUS_CANCELLED,
        ],
        WORKFLOW_STATUS_PLANNED: [
            WORKFLOW_STATUS_CANCELLED,
        ],
        WORKFLOW_STATUS_PLANNED_NO_BOOKING: [
            WORKFLOW_STATUS_CANCELLED,
        ],
        WORKFLOW_STATUS_CONFIRMED: [
            WORKFLOW_STATUS_REMINDED,
            WORKFLOW_STATUS_EXECUTED,
            WORKFLOW_STATUS_CANCELLED,
            WORKFLOW_STATUS_NOSHOW,
        ],
        WORKFLOW_STATUS_REMINDED: [
            WORKFLOW_STATUS_EXECUTED,
            WORKFLOW_STATUS_CANCELLED,
            WORKFLOW_STATUS_NOSHOW,
        ],
        WORKFLOW_STATUS_EXECUTED: [
            WORKFLOW_STATUS_NOSHOW
        ],
        WORKFLOW_STATUS_EVALUATED: [
            WORKFLOW_STATUS_BEING_PLANNED,
        ],
        WORKFLOW_STATUS_CANCELLED: [
            WORKFLOW_STATUS_BEING_PLANNED,
        ],
        WORKFLOW_STATUS_NOSHOW: [
            WORKFLOW_STATUS_BEING_PLANNED,
        ],
        WORKFLOW_STATUS_AUTOASSIGN_FAILED: [
            WORKFLOW_STATUS_BEING_PLANNED,
            WORKFLOW_STATUS_CANCELLED,
            WORKFLOW_STATUS_PLANNED
        ]
    }

    # 15556: For these statuses, when the visit's starttime is passed,
    # add WORKFLOW_STATUS_NOSHOW to the list of status choices
    noshow_available_after_starttime = [
        WORKFLOW_STATUS_BEING_PLANNED,
        WORKFLOW_STATUS_PLANNED,
        WORKFLOW_STATUS_PLANNED_NO_BOOKING,
        WORKFLOW_STATUS_CONFIRMED,
        WORKFLOW_STATUS_REMINDED,
        WORKFLOW_STATUS_AUTOASSIGN_FAILED
    ]

    def can_assign_resources(self):
        being_planned = Visit.WORKFLOW_STATUS_BEING_PLANNED
        return self.workflow_status == being_planned

    def planned_status_is_blocked(self, skip_planned_check=False):

        if self.is_multiproductvisit:
            multiproductvisit = self.multiproductvisit
            subs_planned = multiproductvisit.subvisits_unordered.filter(
                Q(workflow_status=Visit.WORKFLOW_STATUS_PLANNED) |
                Q(workflow_status=Visit.WORKFLOW_STATUS_PLANNED_NO_BOOKING)
            ).count()
            if subs_planned < multiproductvisit.required_visits:
                return True

        # We have to have a chosen starttime before we are planned
        if not hasattr(self, 'eventtime') or not self.eventtime.start:
            return True

        # It's not blocked if we can't choose it
        if not skip_planned_check and \
                Visit.WORKFLOW_STATUS_PLANNED not in (
                    x[0] for x in self.possible_status_choices()
                ):
            return False

        for product in self.products:
            if product.is_resource_controlled:
                for x in product.resourcerequirement_set.all():
                    if not x.is_fullfilled_for(self):
                        return True

        if not self.is_multiproductvisit and \
                not self.product.is_resource_controlled:
            # Correct number of hosts/teachers must be assigned
            if self.needed_hosts > 0 or self.needed_teachers > 0:
                return True

            # Room assignment must be resolved
            if self.room_status == Visit.STATUS_NOT_ASSIGNED:
                return True

        return False

    def possible_status_choices(self):
        result = []

        allowed = self.valid_status_changes[self.workflow_status]

        if self.workflow_status in \
                Visit.noshow_available_after_starttime and \
                hasattr(self, 'eventtime') and self.eventtime.start and \
                timezone.now() > self.eventtime.start:
            allowed.append(Visit.WORKFLOW_STATUS_NOSHOW)

        for x in self.workflow_status_choices:
            if x[0] in allowed:
                result.append(x)

        return result

    def workflow_status_display(self):
        for value, label in self.workflow_status_choices:
            if value == self.workflow_status:
                return label

    def get_subjects(self):
        if hasattr(self, 'teacherbooking'):
            return self.teacherbooking.subjects.all()
        else:
            return None

    def update_last_workflow_change(self):
        last_workflow_status = None
        if self.pk:
            # Fetch old value
            item = Visit.objects.filter(
                pk=self.pk
            ).values("workflow_status").first()
            if item:
                last_workflow_status = item['workflow_status']

        if last_workflow_status is None or \
                last_workflow_status != self.workflow_status:
            self.last_workflow_update = timezone.now()
            if self.workflow_status == self.WORKFLOW_STATUS_EXECUTED:
                if self.evaluation is not None:
                    self.evaluation.send_first_notification()

    @property
    # QuerySet that finds EventTimes that will be affected by resource changes
    # on this visit.
    def affected_eventtimes(self):
        if (
            hasattr(self, 'eventtime') and
            self.eventtime.start and
            self.eventtime.end
        ):
            return self.product.affected_eventtimes.filter(
                start__lt=self.eventtime.end,
                end__gt=self.eventtime.start
            )
        else:
            return EventTime.objects.none()

    def update_availability(self):
        for x in self.affected_eventtimes:
            x.update_availability()

    def resources_updated(self):
        if self.workflow_status in [
            self.WORKFLOW_STATUS_BEING_PLANNED,
            self.WORKFLOW_STATUS_AUTOASSIGN_FAILED
        ] and not self.planned_status_is_blocked(True):
            self.workflow_status = self.WORKFLOW_STATUS_PLANNED
            self.save()
        elif self.workflow_status in [
                    self.WORKFLOW_STATUS_PLANNED,
                    self.WORKFLOW_STATUS_PLANNED_NO_BOOKING
                ] and self.planned_status_is_blocked(True):
            self.workflow_status = self.WORKFLOW_STATUS_BEING_PLANNED
            self.save()

    def resource_accepts(self):
        self.resources_updated()

    def resource_declines(self):
        if self.workflow_status == self.WORKFLOW_STATUS_BEING_PLANNED:
            self.workflow_status = self.WORKFLOW_STATUS_REJECTED
            self.save()

    def on_starttime(self):
        if self.eventtime is not None:
            if self.eventtime.start is not None and self.eventtime.end is None:
                self.on_expire()

    def on_endtime(self):
        self.on_expire()

    def on_expire(self):
        if self.workflow_status in [
            self.WORKFLOW_STATUS_BEING_PLANNED,
            self.WORKFLOW_STATUS_PLANNED,
            self.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
            self.WORKFLOW_STATUS_CONFIRMED,
            self.WORKFLOW_STATUS_REMINDED,
            self.WORKFLOW_STATUS_AUTOASSIGN_FAILED
        ]:
            self.workflow_status = self.WORKFLOW_STATUS_EXECUTED
            self.save()

    @property
    def display_title(self):
        return self.product.title

    @property
    def display_value(self):
        if not hasattr(self, 'eventtime') or not self.eventtime.start:
            return _(u'ikke-fastlagt tidspunkt')

        start = timezone.localtime(self.eventtime.start)
        result = formats.date_format(start, "DATETIME_FORMAT")

        if self.duration:
            try:
                (hours, mins) = self.duration.split(":", 2)
                if int(hours) > 0 or int(mins) > 0:
                    endtime = start + timedelta(
                        hours=int(hours), minutes=int(mins)
                    )
                    result += " - " + formats.date_format(
                        endtime, "TIME_FORMAT"
                    )
            except Exception as e:
                print e

        return result

    @property
    def id_display(self):
        return _(u'Besøg #%d') % self.id

    # Format date for basic display
    @property
    def date_display(self):
        if hasattr(self, 'eventtime') and self.eventtime.start:
            return formats.date_format(
                self.eventtime.naive_start,
                "DATETIME_FORMAT"
            )
        else:
            return _(u'ikke-fastlagt tidspunkt')

    # Format date for display with context (e.g. "on [date] at [time]")
    @property
    def date_display_context(self):
        if hasattr(self, 'eventtime') and self.eventtime.start:
            return _("d. %(date)s kl. %(time)s") % {
                'date': formats.date_format(
                    self.eventtime.naive_start, "DATE_FORMAT"
                ),
                'time': formats.date_format(
                    self.eventtime.naive_start, "TIME_FORMAT"
                )
            }
        else:
            return _(u'på ikke-fastlagt tidspunkt')

    @property
    def interval_display(self):
        return self.eventtime.interval_display

    @property
    def start_datetime(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.start
        else:
            return None

    @property
    def end_datetime(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.end
        else:
            return None

    @property
    def expired(self):
        if hasattr(self, 'eventtime') and self.eventtime.start and \
                self.eventtime.start <= timezone.now():
            return "expired"
        return ""

    def resources_assigned(self, requirement):
        if self.is_multiproductvisit:
            return self.multiproductvisit.resources_assigned(requirement)
        return self.resources.filter(
            visitresource__resource_requirement=requirement
        )

    def resources_required(self, resource_type):
        missing = 0
        for requirement in self.product.resourcerequirement_set.filter(
            resource_pool__resource_type_id=resource_type
        ):
            resources = self.visitresource.filter(
                resource_requirement=requirement
            )
            if resources.count() < requirement.required_amount:
                missing += (requirement.required_amount - resources.count())
        return missing

    @property
    def total_required_teachers(self):
        if self.override_needed_teachers is not None:
            return self.override_needed_teachers

        return self.product.total_required_teachers

    @property
    def needed_teachers(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_teachers
        elif self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_TEACHER)
        else:
            return self.total_required_teachers - \
                   self.assigned_teachers.count()

    @property
    def needs_teachers(self):
        return self.needed_teachers > 0

    @property
    def assigned_teachers(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.assigned_teachers
        if self.product.is_resource_controlled:
            return User.objects.filter(
                teacherresource__visitresource__visit=self
            )
        else:
            return self.teachers.all()

    @property
    def total_required_hosts(self):
        if self.override_needed_hosts is not None:
            return self.override_needed_hosts

        return self.product.total_required_hosts

    @property
    def needed_hosts(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_hosts
        elif self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_HOST)
        else:
            return self.total_required_hosts - self.assigned_hosts.count()

    @property
    def needs_hosts(self):
        return self.needed_hosts > 0

    @property
    def assigned_hosts(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.assigned_hosts
        if self.product.is_resource_controlled:
            return User.objects.filter(
                hostresource__visitresource__visit=self
            )
        else:
            return self.hosts.all()

    @property
    def total_required_rooms(self):
        if self.override_needed_hosts is not None:
            return self.override_needed_hosts
        return self.product.total_required_rooms

    @property
    def needed_rooms(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_rooms
        elif self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_ROOM)
        else:
            return 1 if self.room_status == self.STATUS_NOT_ASSIGNED else 0

    @property
    def needs_room(self):
        return self.needed_rooms > 0

    @property
    def needed_items(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_items
        if self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_ITEM)
        return 0

    @property
    def needed_vehicles(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_vehicles
        if self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_VEHICLE)
        return 0

    @property
    def is_booked(self):
        """Has this Visit instance been booked yet?"""
        return len(self.bookings.all()) > 0

    @property
    def is_bookable(self):
        # Can this visit be booked?
        if self.workflow_status not in self.BOOKABLE_STATES:
            return False
        if self.expired:
            return False
        if self.available_seats == 0:
            return False
        return True

    @property
    def has_changes_after_planned(self):
        # This is only valid for statuses that are considered planned
        if self.workflow_status == self.WORKFLOW_STATUS_BEING_PLANNED:
            return False

        return self.changes_after_last_status_change().exists()

    def changes_after_last_status_change(self):
        types = get_related_content_types(Visit)

        # Since log entry for workflow status change is logged after
        # the object itself is saved we have to be a bit fuzzy in our
        # comparison.
        fuzzy_adjustment = timezone.timedelta(seconds=1)

        return LogEntry.objects.filter(
            object_id=self.pk,
            content_type__in=types,
            action_time__gt=self.last_workflow_update + fuzzy_adjustment
        )

    @property
    def can_join_waitinglist(self):
        # Can this visit be booked (with spots on the waiting list)?
        if not hasattr(self, 'eventtime'):
            return False
        if not self.eventtime.bookable:
            return False
        if self.workflow_status not in self.BOOKABLE_STATES:
            return False
        if self.expired:
            return False
        if self.waiting_list_capacity <= 0:
            return False
        if self.waiting_list_closed:
            return False
        return True

    def get_bookings(self, include_waitinglist=False, include_regular=True):
        if include_regular:  # Include non-waitinglist bookings
            if include_waitinglist:
                return self.bookings.all()
            else:
                return self.bookings.filter(waitinglist_spot=0)
        else:
            if include_waitinglist:
                return self.bookings.filter(waitinglist_spot__gt=0). \
                    order_by("waitinglist_spot")
            else:
                return self.bookings.none()

    def set_needs_attention(self, since=None):
        if since is None:
            since = timezone.now()

        # Also mark parent as needing attention
        if self.is_multi_sub:
            self.multi_master.set_needs_attention(since=since)

        if not (
            self.needs_attention_since and
            self.needs_attention_since >= since
        ):
            self.needs_attention_since = since
            self.save()

    @property
    def booking_list(self):
        return self.get_bookings(False, True)

    @property
    def waiting_list(self):
        return self.get_bookings(True, False)

    def get_attendee_count(self,
                           include_waitinglist=False, include_regular=True):
        return self.get_bookings(
            include_waitinglist, include_regular
        ).aggregate(
            Sum('booker__attendee_count')
        )['booker__attendee_count__sum'] or 0

    @property
    def nr_attendees(self):
        return self.get_attendee_count(False, True)

    @property
    def nr_waiting(self):
        return self.get_attendee_count(True, False)

    @property
    def available_seats(self):
        limit = self.product.maximum_number_of_visitors
        if limit is None:
            return sys.maxint
        return max(limit - self.nr_attendees, 0)

    def get_workflow_status_class(self):
        return self.status_to_class_map.get(self.workflow_status, 'default')

    @classmethod
    def needs_teachers_qs(cls):
        req_type_key = "__".join([
            "eventtime",
            "product",
            "resourcerequirement",
            "resource_pool",
            "resource_type"
        ])
        assigned_type_key = "__".join([
            "visitresource",
            "resource_requirement",
            "resource_pool",
            "resource_type"
        ])
        return cls.objects.filter(
            **{req_type_key: ResourceType.RESOURCE_TYPE_TEACHER}
        ).filter(
            Q(**{assigned_type_key: ResourceType.RESOURCE_TYPE_TEACHER}) |
            Q(visitresource__isnull=True)
        ).annotate(
            needed=Sum(
                'eventtime__product__resourcerequirement__required_amount'
            ),
            assigned=Count('visitresource')
        ).filter(needed__gt=F("assigned"))

    def __unicode__(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.__unicode__()
        if hasattr(self, 'eventtime'):
            return _(u'Besøg %(id)s - %(title)s - %(time)s') % {
                'id': self.pk,
                'title': unicode(self.real.display_title),
                'time': unicode(self.eventtime.interval_display)
            }
        else:
            return unicode(_(u'Besøg %s - uden tidspunkt') % self.pk)

    @property
    def product(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.product
        else:
            return None

    def get_override_attr(self, attrname):
        result = getattr(self, 'override_' + attrname, None)

        if result is None:
            product = self.product
            if product:
                result = getattr(product, attrname)

        return result

    def set_override_attr(self, attrname, val):
        setattr(self, 'override_' + attrname, val)

    @classmethod
    def add_override_property(cls, attrname):
        setattr(cls, attrname, property(
            lambda self: self.get_override_attr(attrname),
            lambda self, val: self.set_override_attr(attrname, val)
        ))

    def as_searchtext(self):
        result = []

        product = self.product
        if product:
            result.append(product.as_searchtext())

        if self.bookings:
            for booking in self.bookings.all():
                result.append(booking.as_searchtext())

        return " ".join(result)

    @classmethod
    def being_planned_queryset(cls, **kwargs):
        return cls.objects.filter(
            workflow_status__in=[
                cls.WORKFLOW_STATUS_BEING_PLANNED,
                cls.WORKFLOW_STATUS_AUTOASSIGN_FAILED
            ],
            **kwargs
        )

    @classmethod
    def planned_queryset(cls, **kwargs):
        return cls.objects.filter(
            workflow_status__in=[
                cls.WORKFLOW_STATUS_PLANNED,
                cls.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
                cls.WORKFLOW_STATUS_CONFIRMED,
                cls.WORKFLOW_STATUS_REMINDED
            ],
        ).filter(**kwargs)

    @staticmethod
    def unit_filter(qs, unit_qs):
        mpv_qs = MultiProductVisit.objects.filter(
            subvisit__is_multi_sub=True,
            subvisit__eventtime__product__organizationalunit=unit_qs
        )
        return qs.filter(
            Q(eventtime__product__organizationalunit=unit_qs) |
            Q(multiproductvisit=mpv_qs)
        )

    # This is used from booking.signals.update_search_indexes
    def update_searchindex(self):
        if not self.pk:
            return False

        old_value = self.extra_search_text or ""
        new_value = self.as_searchtext() or ""

        if old_value != new_value:
            self.extra_search_text = new_value
            self.save()
            return True
        else:
            return False

    def save(self, *args, **kwargs):
        self.update_endtime()
        self.update_last_workflow_change()
        super(Visit, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('visit-view', args=[self.pk])

    def get_recipients(self, template_type):
        product = self.product
        if self.is_multiproductvisit and self.multiproductvisit.primary_visit:
            product = self.multiproductvisit.primary_visit.product
        if product:
            recipients = product.get_recipients(template_type)
        else:
            recipients = []
        if template_type.send_to_visit_hosts:
            recipients.extend(self.hosts.all())
        if template_type.send_to_visit_teachers:
            recipients.extend(self.teachers.all())
        if template_type.avoid_already_assigned:
            for item in self.hosts.all():
                if item in recipients:
                    recipients.remove(item)
            for item in self.teachers.all():
                if item in recipients:
                    recipients.remove(item)
        return recipients

    def get_reply_recipients(self, template_type):
        product = self.product
        if self.is_multiproductvisit and self.multiproductvisit.primary_visit:
            product = self.multiproductvisit.primary_visit.product
        if product:
            return product.get_reply_recipients(template_type)
        else:
            return []

    def create_inheriting_autosends(self):
        for template_type in EmailTemplateType.objects.filter(
            enable_autosend=True
        ):
            if not self.get_autosend(template_type, False, False):
                visitautosend = VisitAutosend(
                    visit=self,
                    inherit=True,
                    template_key=template_type.key,
                    template_type=template_type,
                    days=None,
                    enabled=False
                )
                visitautosend.save()

    def autosend_inherits(self, template_type):
        s = self.visitautosend_set.filter(
            template_type=template_type
        )

        # If no rule specified, always inherit
        if s.count() == 0:
            return True

        # Return true if there is a rule specifying that inheritance is wanted
        return s.filter(inherit=True).count() > 0

    def get_autosend(self, template_type, follow_inherit=True,
                     include_disabled=False):
        if self.is_multiproductvisit:
            return self.multiproductvisit.get_autosend(
                template_type, follow_inherit, include_disabled
            )
        if type(template_type) == int:
            template_type = EmailTemplateType.get(template_type)
        if follow_inherit and self.autosend_inherits(template_type):
            return self.product.get_autosend(template_type)
        else:
            try:
                query = self.visitautosend_set.filter(
                    template_type=template_type)
                if not include_disabled:
                    query = query.filter(enabled=True)
                return query[0]
            except:
                return None

    def get_autosends(self, follow_inherit=True,
                      include_disabled=False, yield_inherited=True):
        result = set()
        for autosend in self.visitautosend_set.all():
            if autosend.enabled or include_disabled:
                result.add(autosend)
            elif autosend.inherit and follow_inherit:
                inherited = autosend.get_inherited()
                if inherited is not None and \
                        (inherited.enabled or include_disabled):
                    if yield_inherited:
                        result.add(inherited)
                    else:
                        result.add(autosend)
        return result

    def autosend_enabled(self, template_type):
        return self.real.get_autosend(template_type, True) is not None

    # Sends a message to defined recipients pertaining to the Visit
    def autosend(self, template_type, recipients=None,
                 only_these_recipients=False):
        if type(template_type) == int:
            template_type = EmailTemplateType.get(template_type)
        if self.is_multiproductvisit:
            return self.multiproductvisit.autosend(
                template_type, recipients, only_these_recipients
            )
        if self.autosend_enabled(template_type):
            product = self.product
            unit = product.organizationalunit
            if recipients is None:
                recipients = set()
            else:
                recipients = set(recipients)
            if not only_these_recipients:
                recipients.update(self.get_recipients(template_type))

            # People who will receive any replies to the mail
            reply_recipients = self.get_reply_recipients(template_type)

            KUEmailMessage.send_email(
                template_type,
                {'visit': self, 'besoeg': self, 'product': product},
                list(recipients),
                self,
                unit,
                original_from_email=reply_recipients
            )

            if not only_these_recipients and template_type.send_to_booker:
                for booking in self.bookings.all():
                    KUEmailMessage.send_email(
                        template_type,
                        {
                            'visit': self,
                            'besoeg': self,
                            'product': product,
                            'booking': booking,
                            'booker': booking.booker
                        },
                        booking.booker,
                        self,
                        unit,
                        original_from_email=reply_recipients
                    )

    def get_autosend_display(self):
        autosends = self.get_autosends(True, False, False)
        return ', '.join([autosend.get_name() for autosend in autosends])

    def update_endtime(self):
        if self.deprecated_start_datetime is not None:
            product = self.product
            if product:
                duration = product.duration_as_timedelta
                if duration is not None:
                    self.deprecated_end_datetime = (
                        self.deprecated_start_datetime + duration
                    )

    def add_room_by_name(self, name):
        product = self.product
        locality = None

        if product and product.locality:
            locality = product.locality

        room = Room.objects.filter(
            name=name,
            locality=locality
        ).first()

        if room is None:
            room = Room(
                name=name,
                locality=self.locality
            )
            room.save()

        self.rooms.add(room)

        return room

    @staticmethod
    def get_latest_created():
        return Visit.objects.\
            order_by('-statistics__created_time')

    @staticmethod
    def get_latest_updated():
        return Visit.objects.\
            order_by('-statistics__updated_time')

    @staticmethod
    def get_latest_displayed():
        return Visit.objects.\
            order_by('-statistics__visited_time')

    @staticmethod
    def get_latest_booked():
        return Visit.objects.filter(
            bookings__isnull=False
        ).order_by(
            '-bookings__statistics__created_time'
        )

    @staticmethod
    def get_todays_visits():
        return Visit.get_occurring_on_date(timezone.now().date())

    @staticmethod
    def get_starting_on_date(date):
        return Visit.objects.none()
        return Visit.objects.filter(
            eventtime__start__year=date.year,
            eventtime__start__month=date.month,
            eventtime__start__day=date.day,
            is_multi_sub=False
        ).order_by('eventtime__start')

    @staticmethod
    def get_occurring_at_time(time):
        # Return the visits that take place exactly at this time
        # Meaning they begin before the queried time and end after the time
        return Visit.objects.filter(
            eventtime__start__lte=time,
            eventtime__end__gt=time,
            is_multi_sub=False
        )

    @staticmethod
    def get_occurring_on_date(date):
        # Convert date object to date-only for current timezone
        date = timezone.datetime(
            year=date.year,
            month=date.month,
            day=date.day,
            tzinfo=timezone.get_current_timezone()
        )

        # A visit happens on a date if it starts before the
        # end of the day and ends after the beginning of the day
        return Visit.objects.filter(
            eventtime__start__lte=date + timedelta(days=1),
            eventtime__end__gt=date,
            is_multi_sub=False
        )

    @staticmethod
    def get_recently_held(time=timezone.now()):
        return Visit.objects.filter(
            workflow_status__in=[
                Visit.WORKFLOW_STATUS_EXECUTED,
                Visit.WORKFLOW_STATUS_EVALUATED],
            eventtime__start__isnull=False,
            eventtime__end__lt=time,
            is_multi_sub=False
        ).order_by('-eventtime__end')

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()

    @staticmethod
    def set_endtime():
        for visit in Visit.objects.all():
            visit.save()

    def add_comment(self, user, text):
        VisitComment(
            visit=self,
            author=user,
            text=text
        ).save()

    def get_comments(self, user=None):
        if user is None:
            return VisitComment.objects.filter(visit=self)
        else:
            return VisitComment.objects.filter(
                visit=self,
                author=user
            )

    @property
    def waiting_list_capacity(self):
        product = self.product

        if not product:
            return 0

        from_product = product.fixed_waiting_list_capacity
        if from_product is not None:
            return from_product

        idlespots = product.waiting_list_length - self.nr_waiting

        return max(idlespots, 0)

    @property
    def last_waiting_list_spot(self):
        list = self.get_bookings(True, False)
        if list.count() == 0:
            return 0
        else:
            return list.last().waitinglist_spot

    @property
    def next_waiting_list_spot(self):
        return self.last_waiting_list_spot + 1

    def normalize_waitinglist(self):
        last = 0
        for booking in self.waiting_list:
            if booking.waitinglist_spot > last+1:
                booking.waitinglist_spot = last+1
                booking.save()
            last = booking.waitinglist_spot

    @property
    def waiting_list_closing_time(self):
        product = self.product

        if not product:
            return None

        if product.waiting_list_deadline_days is None and \
                product.waiting_list_deadline_hours is None:
            return None
        time = self.eventtime.start if hasattr(self, 'eventtime') else None
        if time:
            if product.waiting_list_deadline_days > 0:
                time = time - timedelta(
                    days=product.waiting_list_deadline_days
                )
            if product.waiting_list_deadline_hours > 0:
                time = time - timedelta(
                    hours=product.waiting_list_deadline_hours
                )
            return time
        return None

    @property
    def waiting_list_closed(self):
        product = self.product
        if not product or not product.do_create_waiting_list:
            return True
        closing_time = self.waiting_list_closing_time
        if closing_time:
            return closing_time < timezone.now()
        return False

    def requirement_details(self):
        details = []
        for type in ResourceType.objects.all():
            requirements = self.product.resourcerequirement_set.filter(
                resource_pool__resource_type=type
            )
            if requirements.count() > 0:
                required = 0
                acquired = 0
                for requirement in requirements:
                    required += requirement.required_amount
                    acquired += self.resources.filter(
                        visitresource__resource_requirement=requirement
                    ).count()
                details.append({
                    'required': required,
                    'acquired': acquired,
                    'type': type,
                    'is_teacher': (
                        type.id == ResourceType.RESOURCE_TYPE_TEACHER
                    ),
                    'is_host': (type.id == ResourceType.RESOURCE_TYPE_HOST)
                })
        return details

    @property
    def is_multiproductvisit(self):
        return hasattr(self, 'multiproductvisit')

    @property
    def real(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit
        return self

    @property
    def products(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.products
        return [self.product]

    @property
    def calendar_event_link(self):
        return reverse('visit-view', args=[self.pk])

    @property
    def calender_event_title(self):
        res = _(u'Besøg #%s') % self.pk
        if self.product:
            return '%s - %s' % (res, self.product.title)
        else:
            return res

    def context_for_user(self, user, request_usertype=None):
        profile = user.userprofile
        context = {
            'is_teacher': profile.is_teacher,
            'is_host': profile.is_host,
        }

        if self.is_multiproductvisit:
            context['is_potential_host'] = False
            context['is_assigned_as_host'] = False
        else:
            context['is_potential_host'] = (
                self.product.potential_hosts.filter(pk=user.pk).exists()
            )
            context['is_assigned_as_host'] = (
                self.assigned_hosts.filter(pk=user.pk).exists()
            )
            context['needs_hosts'] = self.needs_hosts

        context['can_become_host'] = (
            context['is_potential_host'] and
            not context['is_assigned_as_host'] and
            self.needs_hosts
        )

        if self.is_multiproductvisit:
            context['is_potential_teacher'] = False
            context['is_assigned_as_teacher'] = False
        else:
            context['is_potential_teacher'] = (
                self.product.potential_teachers.filter(pk=user.pk).exists()
            )
            context['is_assigned_as_teacher'] = (
                self.assigned_teachers.filter(pk=user.pk).exists()
            )
            context['needs_teachers'] = self.needs_teachers

        context['can_become_teacher'] = (
            context['is_potential_teacher'] and
            not context['is_assigned_as_teacher'] and
            self.needs_teachers
        )

        context['can_edit'] = profile.can_edit(self)
        context['can_notify'] = profile.can_notify(self)

        return context

    def resources_available_for_autoassign(self, resource_pool):
        eligible = resource_pool.resources.exclude(visitresource__visit=self)

        return [
            resource
            for resource in eligible
            if resource.available_for_visit(self)
        ]

    def autoassign_resources(self):
        if self.is_multiproductvisit:
            self.multiproductvisit.autoassign_resources()
        if self.product.time_mode == \
                Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN:
            for requirement in self.product.resourcerequirement_set.all():
                assigned = self.resources.filter(
                    visitresource__resource_requirement=requirement
                )
                extra_needed = requirement.required_amount - assigned.count()
                if extra_needed > 0:
                    eligible = list(
                        requirement.resource_pool.resources.exclude(
                            id__in=[resource.id for resource in assigned]
                        )
                    )
                    random.shuffle(eligible)
                    found = []
                    for resource in eligible:
                        if resource.available_for_visit(self):
                            found.append(resource)
                            if len(found) >= extra_needed:
                                break
                    if len(found) < extra_needed:
                        # requirement cannot be fulfilled;
                        # not enough available resources
                        self.workflow_status = \
                            self.WORKFLOW_STATUS_AUTOASSIGN_FAILED
                        self.save()
                    for resource in found:
                        VisitResource(
                            visit=self,
                            resource=resource,
                            resource_requirement=requirement
                        ).save()
            self.resources_updated()


Visit.add_override_property('duration')
Visit.add_override_property('locality')


class MultiProductVisit(Visit):

    date = models.DateField(
        null=True,
        blank=False,
        verbose_name=_(u'Dato')
    )
    required_visits = models.PositiveIntegerField(
        default=2,
        verbose_name=_(u'Antal ønskede besøg')
    )
    responsible = models.ForeignKey(
        User,
        blank=True,
        null=True,
        verbose_name=_(u'Besøgsansvarlig')
    )

    @property
    def date_ref(self):
        return self.eventtime.start.date()

    def create_eventtime(self, date=None):
        if date is None:
            date = self.date
        if date is not None:
            if not hasattr(self, 'eventtime') or self.eventtime is None:
                time = datetime(
                    date.year, date.month, date.day,
                    8, tzinfo=timezone.get_current_timezone()
                )
                EventTime(visit=self, start=time).save()

    @staticmethod
    def migrate_to_eventtime():
        for mpv in MultiProductVisit.objects.all():
            mpv.create_eventtime()

    @property
    def subvisits_unordered(self):
        # Faster than ordered, and often we don't need the ordering anyway
        return Visit.objects.filter(
            is_multi_sub=True,
            multi_master=self
        )

    @property
    def subvisits(self):
        return self.subvisits_unordered.order_by('multi_priority')

    @property
    def products(self):
        return [visit.product for visit in self.subvisits if visit.product]

    def potential_responsible(self):
        units = OrganizationalUnit.objects.filter(
            product__eventtime__visit__set=self.subvisits_unordered
        )
        return User.objects.filter(
            userprofile__organizationalunit=units
        )

    def planned_status_is_blocked(self):
        return True

    def resources_assigned(self, requirement):
        resource_list = []
        for visit in self.subvisits_unordered:
            resource_list += list(visit.resources_assigned(requirement))
        # return resource_list
        # Return as a Queryset, because someone may need the db methods
        return Resource.objects.filter(
            id__in=[res.id for res in resource_list]
        )

    @property
    def total_required_teachers(self):
        return sum(
            subvisit.total_required_teachers
            for subvisit in self.subvisits_unordered
        )

    @property
    def assigned_teachers(self):
        return User.objects.filter(
            id__in=flatten([
                [user.id for user in subvisit.assigned_teachers]
                for subvisit in self.subvisits_unordered
            ])
        )

    @property
    def needed_teachers(self):
        return sum(
            subvisit.needed_teachers
            for subvisit in self.subvisits_unordered
        )

    @property
    def needs_teachers(self):
        for subvisit in self.subvisits_unordered:
            if subvisit.needs_teachers:
                return True
        return False

    @property
    def total_required_hosts(self):
        return sum(
            subvisit.total_required_hosts
            for subvisit in self.subvisits_unordered
        )

    @property
    def assigned_hosts(self):
        return User.objects.filter(
            id__in=flatten([
                [user.id for user in subvisit.assigned_hosts]
                for subvisit in self.subvisits_unordered
            ])
        )

    @property
    def needed_hosts(self):
        return sum(
            subvisit.needed_hosts
            for subvisit in self.subvisits_unordered
        )

    @property
    def needs_hosts(self):
        for subvisit in self.subvisits_unordered:
            if subvisit.needs_hosts:
                return True
        return False

    @property
    def total_required_rooms(self):
        return sum(
            subvisit.total_required_rooms
            for subvisit in self.subvisits_unordered
        )

    @property
    def needed_rooms(self):
        return sum(
            subvisit.needed_rooms
            for subvisit in self.subvisits_unordered
        )

    @property
    def needs_room(self):
        for subvisit in self.subvisits_unordered:
            if subvisit.needs_room:
                return True
        return False

    @property
    def needed_items(self):
        return sum(
            subvisit.needed_items
            for subvisit in self.subvisits_unordered
        )

    @property
    def needed_vehicles(self):
        return sum(
            subvisit.needed_vehicles
            for subvisit in self.subvisits_unordered
        )

    @property
    def available_seats(self):
        return 0

    @property
    def display_title(self):
        # return _(u'prioriteret liste af %d tilbud') % len(self.products)
        count = len(self.subvisits_unordered)
        return __(
            "%(title)s, %(count)d prioritet",
            "%(title)s, %(count)d prioriteter",
            count
        ) % {
            'title': self.primary_visit.display_title,
            'count': count
        }

    @property
    def date_display(self):
        return formats.date_format(self.date_ref, "DATE_FORMAT")

    @property
    def date_display_context(self):
        return _("d. %s") % formats.date_format(self.date_ref, "DATE_FORMAT")

    @property
    def start_datetime(self):
        return self.date_ref

    @property
    def interval_display(self):
        return self.date_display

    @property
    def display_value(self):
        return self.date_display

    @property
    def primary_visit(self):
        # For the purposes of determining who can manage this visit,
        # return the highest-priority non-cancelled visit with a unit
        if self.subvisits_unordered.count() > 0:
            active = self.subvisits.filter(workflow_status__in=[
                Visit.WORKFLOW_STATUS_BEING_PLANNED,
                Visit.WORKFLOW_STATUS_CONFIRMED,
                Visit.WORKFLOW_STATUS_EVALUATED,
                Visit.WORKFLOW_STATUS_EXECUTED,
                Visit.WORKFLOW_STATUS_PLANNED,
                Visit.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
                Visit.WORKFLOW_STATUS_REMINDED,
                Visit.WORKFLOW_STATUS_AUTOASSIGN_FAILED
            ])
            for visit in active:
                if visit.organizationalunit is not None:
                    return visit
            return self.subvisits[0]
        return None

    @property
    def organizationalunit(self):
        # For the purposes of determining who can manage this visit,
        # return the unit of the highest-priority non-cancelled visit
        primary_visit = self.primary_visit
        if primary_visit:
            return primary_visit.organizationalunit

    def autosend_enabled(self, template_type):
        if template_type.key in [
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED,
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED
        ]:
            return True
        else:
            return super(MultiProductVisit, self).autosend_enabled(
                template_type
            )

    def get_autosend(self, template_type, follow_inherit=True,
                     include_disabled=False):
        return None
        # Disable all autosends
        # if follow_inherit and self.autosend_inherits(template_key):
        #     for product in self.products:
        #         autosend = product.get_autosend(template_key)
        #         if autosend:
        #             return autosend
        #     return None
        # else:
        #     return super(MultiProductVisit, self).get_autosend(
        #         template_key, follow_inherit, include_disabled
        #     )

    # Sends a message to defined recipients pertaining to the Visit
    def autosend(self, template_type, recipients=None,
                 only_these_recipients=False):
        if self.autosend_enabled(template_type):
            unit = None  # TODO: What should the unit be?
            if recipients is None:
                recipients = set()
            else:
                recipients = set(recipients)
            if not only_these_recipients:
                recipients.update(self.get_recipients(template_type))

            # People who will receive any replies to the mail
            reply_recipients = self.get_reply_recipients(template_type)

            params = {'visit': self, 'products': self.products}

            KUEmailMessage.send_email(
                template_type,
                params,
                list(recipients),
                self,
                unit,
                original_from_email=reply_recipients
            )

            if not only_these_recipients and template_type.send_to_booker:
                for booking in self.bookings.all():
                    KUEmailMessage.send_email(
                        template_type,
                        merge_dicts(params, {
                            'booking': booking,
                            'booker': booking.booker
                        }),
                        booking.booker,
                        self,
                        unit,
                        original_from_email=reply_recipients
                    )

    def autoassign_resources(self):
        for visit in self.subvisits_unordered:
            visit.autoassign_resources()

    def __unicode__(self):
        if hasattr(self, 'eventtime'):
            return _(u'Besøg %(id)s - Prioriteret liste af '
                     u'%(count)d underbesøg - %(time)s') % {
                'id': self.pk,
                'count': self.subvisits_unordered.count(),
                'time': unicode(self.eventtime.interval_display)
            }
        else:
            return unicode(_(u'Besøg %s - uden tidspunkt') % self.pk)


class MultiProductVisitTempProduct(models.Model):
    product = models.ForeignKey(Product, related_name='prod')
    multiproductvisittemp = models.ForeignKey('MultiProductVisitTemp')
    index = models.IntegerField()


class MultiProductVisitTemp(models.Model):
    date = models.DateField(
        null=False,
        blank=False,
        verbose_name=_(u'Dato')
    )

    @property
    def products_ordered(self):
        return [
            relation.product
            for relation in
            MultiProductVisitTempProduct.objects.filter(
                multiproductvisittemp=self
            ).order_by('index')
        ]

    products = models.ManyToManyField(
        Product,
        blank=True,
        through=MultiProductVisitTempProduct,
        related_name='products'
    )
    updated = models.DateTimeField(
        auto_now=True
    )
    notes = models.TextField(
        blank=True,
        verbose_name=u'Bemærkninger'
    )
    baseproduct = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        related_name='foobar'
    )
    required_visits = models.PositiveIntegerField(
        default=2,
        verbose_name=_(u'Antal ønskede besøg')
    )

    def create_mpv(self):
        mpv = MultiProductVisit(
            required_visits=self.required_visits
        )
        mpv.needs_attention_since = timezone.now()
        mpv.save()
        mpv.create_eventtime(self.date)
        mpv.ensure_statistics()
        for index, product in enumerate(self.products_ordered):
            eventtime = EventTime(
                product=product,
                bookable=False,
                has_specific_time=False
            )
            eventtime.save()
            eventtime.make_visit(
                product=product,
                multi_master=mpv,
                multi_priority=index,
                is_multi_sub=True
            )
            if index == 0:
                mpv.responsible = product.tilbudsansvarlig
        mpv.autoassign_resources()
        mpv.save()
        return mpv

    def has_products_in_different_locations(self):
        return len(
            set([product.locality for product in self.products.all()])
        ) > 1
        # return Locality.objects.filter(product=self.products).count() > 1


class VisitComment(models.Model):

    class Meta:
        ordering = ["-time"]

    visit = models.ForeignKey(
        Visit,
        verbose_name=_(u'Besøg'),
        null=False,
        blank=False
    )
    author = models.ForeignKey(
        User,
        null=True,  # Users can be deleted, but we want to keep their comments
        on_delete=models.SET_NULL,
    )
    deleted_user_name = models.CharField(
        max_length=30
    )
    text = models.CharField(
        max_length=500,
        verbose_name=_(u'Kommentartekst')
    )
    time = models.DateTimeField(
        verbose_name=_(u'Tidsstempel'),
        auto_now=True
    )

    def on_delete_author(self):
        self.deleted_user_name = self.author.username
        self.author = None
        self.save()

    @staticmethod
    def on_delete_user(user):
        for comment in VisitComment.objects.filter(author=user):
            comment.on_delete_author()


class Autosend(models.Model):
    template_key = models.IntegerField(
        verbose_name=_(u'Skabelon'),
        blank=False,
        null=False
    )
    days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_(u'Dage'),
    )
    enabled = models.BooleanField(
        verbose_name=_(u'Aktiv'),
        default=True
    )

    template_type = models.ForeignKey(
        EmailTemplateType,
        null=True
    )

    def save(self, *args, **kwargs):
        self.template_key = self.template_type.key
        super(Autosend, self).save(*args, **kwargs)

    def get_name(self):
        return unicode(self.template_type.name)

    def __unicode__(self):
        return "[%d] %s (%s)" % (
            self.id,
            self.get_name(),
            "enabled" if self.enabled else "disabled"
        )

    @property
    def days_relevant(self):
        return self.template_type.enable_days

    @staticmethod
    def migrate():
        for autosend in Autosend.objects.all():
            autosend.template_type = EmailTemplateType.get(
                autosend.template_key
            )
            autosend.save()


class ProductAutosend(Autosend):
    product = models.ForeignKey(
        Product,
        verbose_name=_(u'Besøg'),
        blank=False
    )

    def __unicode__(self):
        return "%s on %s" % (
            super(ProductAutosend, self).__unicode__(),
            self.product.__unicode__()
        )


class VisitAutosend(Autosend):
    visit = models.ForeignKey(
        Visit,
        verbose_name=_(u'BesøgForekomst'),
        blank=False
    )
    inherit = models.BooleanField(
        verbose_name=_(u'Genbrug indstilling fra tilbud')
    )

    def get_inherited(self):
        if self.inherit:
            return self.visit.get_autosend(self.template_type)

    def __unicode__(self):
        return "%s on %s" % (
            super(VisitAutosend, self).__unicode__(),
            self.visit.__unicode__()
        )


class Room(models.Model):

    class Meta:
        verbose_name = _(u"lokale")
        verbose_name_plural = _(u"lokaler")

    locality = models.ForeignKey(
        Locality,
        verbose_name=_(u'Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    name = models.CharField(
        max_length=64, verbose_name=_(u'Navn på lokale'), blank=False
    )

    def __unicode__(self):
        if self.locality:
            return '%s - %s' % (unicode(self.name), unicode(self.locality))
        else:
            return '%s - %s' % (unicode(self.name), _(u'Ingen lokalitet'))

    @property
    def name_with_locality(self):
        if self.locality:
            return '%s, %s' % (
                unicode(self.name),
                self.locality.name_and_address
            )
        else:
            return '%s, %s' % (
                unicode(self.name),
                _(u'<uden lokalitet>')
            )

    @classmethod
    def migrate(cls):
        for x in cls.objects.filter(locality__isnull=True):
            if x.product and x.product.locality:
                x.product.add_room_by_name(x.name)
            x.delete()

        # Copy any rooms from visits each visit's VOs.
        for x in Product.objects.filter(rooms__isnull=False).distinct():
            for y in x.visit_set.all():
                for r in x.rooms.all():
                    y.rooms.add(r)

    def save(self, *args, **kwargs):
        return_value = super(Room, self).save(*args, **kwargs)

        if not self.roomresource_set.exists():
            RoomResource.create(self)

        return return_value


class Region(models.Model):

    class Meta:
        verbose_name = _(u'region')
        verbose_name_plural = _(u'regioner')

    name = models.CharField(
        max_length=16,
        verbose_name=_(u'Navn')
    )

    # Not pretty, but it gets the job done for now
    name_en = models.CharField(
        max_length=16,
        null=True,
        verbose_name=_(u'Engelsk navn')
    )

    def __unicode__(self):
        return self.name

    @staticmethod
    def create_defaults():
        from booking.data import regions
        for name in regions.regions:
            try:
                Region.objects.get(name=name)
            except ObjectDoesNotExist:
                Region(name=name).save()


class Municipality(models.Model):

    class Meta:
        verbose_name = _(u'kommune')
        verbose_name_plural = _(u'kommuner')

    name = models.CharField(
        max_length=30,
        verbose_name=_(u'Navn'),
        unique=True
    )

    region = models.ForeignKey(
        Region,
        verbose_name=_(u'Region')
    )

    def __unicode__(self):
        return self.name

    @staticmethod
    def create_defaults():
        from booking.data import municipalities
        for item in municipalities.municipalities:
            municipality = Municipality.objects.filter(name=item['name']).\
                first()
            region = Region.objects.get(name=item['region'])
            if municipality is None:
                municipality = Municipality(name=item['name'], region=region)
                municipality.save()
            elif municipality.region != region:
                municipality.region = region
                municipality.save()


class PostCode(models.Model):

    class Meta:
        verbose_name = _(u'postnummer')
        verbose_name_plural = _(u'postnumre')

    number = models.IntegerField(
        primary_key=True
    )
    city = models.CharField(
        max_length=48
    )
    region = models.ForeignKey(
        Region
    )

    def __unicode__(self):
        return "%d %s" % (self.number, self.city)

    @staticmethod
    def get(code):
        try:
            return PostCode.objects.get(number=int(code))
        except PostCode.DoesNotExist:
            return None

    @staticmethod
    def create_defaults():
        Region.create_defaults()
        from booking.data import postcodes
        regions = {}
        for postcode_def in postcodes.postcodes:
            postcode_number = postcode_def['number']
            city_name = postcode_def['city']
            region_name = postcode_def['region']
            region = regions.get(region_name)
            if region is None:
                try:
                    region = Region.objects.get(name=region_name)
                    regions[region_name] = region
                except Region.DoesNotExist:
                    print "Unknown region '%s'. May be a typo, please fix in" \
                          " booking/data/postcodes.py" % region_name
                    return
            try:
                postcode = PostCode.objects.get(number=postcode_number)
            except PostCode.DoesNotExist:
                postcode = PostCode(number=postcode_number,
                                    city=city_name, region=region)
                postcode.save()
            else:
                if postcode.city != city_name:
                    postcode.city = city_name
                    postcode.save()
                if postcode.region != region:
                    postcode.region = region
                    postcode.save()


class School(models.Model):

    class Meta:
        verbose_name = _(u'uddannelsesinstitution')
        verbose_name_plural = _(u'uddannelsesinstitutioner')
        ordering = ["name", "postcode"]

    name = models.CharField(
        max_length=128,
    )
    postcode = models.ForeignKey(
        PostCode,
        null=True
    )
    municipality = models.ForeignKey(
        Municipality,
        null=True
    )
    address = models.CharField(
        max_length=128,
        verbose_name=_(u'Adresse'),
        null=True
    )
    cvr = models.IntegerField(
        verbose_name=_(u'CVR-nummer'),
        null=True
    )
    ean = models.BigIntegerField(
        verbose_name=_(u'EAN-nummer'),
        null=True
    )

    ELEMENTARY_SCHOOL = Subject.SUBJECT_TYPE_GRUNDSKOLE
    GYMNASIE = Subject.SUBJECT_TYPE_GYMNASIE
    type_choices = (
        (ELEMENTARY_SCHOOL, u'Folkeskole'),
        (GYMNASIE, u'Gymnasie')
    )

    type = models.IntegerField(
        choices=type_choices,
        default=1,
        verbose_name=_(u'Uddannelsestype')
    )

    def __unicode__(self):
        return self.name

    @staticmethod
    def search(query, type=None):
        query = query.lower()
        qs = School.objects.filter(name__icontains=query)
        if type is not None:
            try:
                type = int(type)
                if type in [id for id, title in School.type_choices]:
                    qs = qs.filter(type=type)
            except ValueError:
                pass
        return qs

    @staticmethod
    def create_defaults():
        PostCode.create_defaults()
        Municipality.create_defaults()
        from booking.data import schools
        # for data, type in [
        #        (schools.elementary_schools, School.ELEMENTARY_SCHOOL),
        #        (schools.high_schools, School.GYMNASIE)]:
        data = schools.high_schools
        type = School.GYMNASIE
        for name, postnr in data:
            try:
                school = School.objects.get(name=name,
                                            postcode__number=postnr)
                if school.type != type:
                    school.type = type
                    school.save()
            except School.DoesNotExist:
                try:
                    postcode = PostCode.get(postnr)
                    School(
                        name=name, postcode=postcode,
                        type=type
                    ).save()
                except PostCode.DoesNotExist:
                    print "Warning: Postcode %d not found in database. " \
                          "Not adding school %s" % (postcode, name)

        data = schools.elementary_schools
        type = School.ELEMENTARY_SCHOOL
        for item in data:
            name = item['name']
            postnr = item['postnr']
            address = item.get('address')
            cvr = item.get('cvr')
            ean = item.get('ean')
            try:
                municipality = Municipality.objects.get(
                    name=item.get('municipality')
                ) if 'municipality' in item else None
            except Municipality.DoesNotExist:
                print "Municipality '%s' does not exist" % \
                      item.get('municipality')
                return

            try:
                school = School.objects.get(name=name,
                                            postcode__number=postnr)
                if school.type != type:
                    school.type = type

                school.address = address
                school.cvr = cvr
                school.ean = ean
                school.municipality = municipality
                school.save()
            except School.DoesNotExist:
                try:
                    postcode = PostCode.get(postnr)
                    School(
                        name=name, postcode=postcode, type=type,
                        address=address, cvr=cvr, ean=ean,
                        municipality=municipality
                    ).save()
                except PostCode.DoesNotExist:
                    print "Warning: Postcode %d not found in database. " \
                          "Not adding school %s" % (postcode, name)


class Guest(models.Model):

    class Meta:
        verbose_name = _(u'besøgende')
        verbose_name_plural = _(u'besøgende')

    # A person booking a visit
    firstname = models.CharField(
        max_length=64,
        blank=False,
        verbose_name=u'Fornavn'
    )
    lastname = models.CharField(
        max_length=64,
        blank=False,
        verbose_name=u'Efternavn'
    )
    email = models.EmailField(
        max_length=64,
        blank=False,
        verbose_name=u'Email'
    )
    phone = models.CharField(
        max_length=14,
        blank=False,
        verbose_name=u'Telefon'
    )

    stx = 0
    hf = 1
    htx = 2
    eux = 3
    valgfag = 4
    hhx = 5
    line_choices = (
        (stx, _(u'stx')),
        (hf, _(u'hf')),
        (htx, _(u'htx')),
        (eux, _(u'eux')),
        (hhx, _(u'hhx')),
    )
    line = models.IntegerField(
        choices=line_choices,
        blank=True,
        null=True,
        verbose_name=u'Linje',
    )

    g1 = 1
    g2 = 2
    g3 = 3
    student = 4
    other = 5
    f0 = 17
    f1 = 7
    f2 = 8
    f3 = 9
    f4 = 10
    f5 = 11
    f6 = 12
    f7 = 13
    f8 = 14
    f9 = 15
    f10 = 16

    level_map = {
        Subject.SUBJECT_TYPE_GRUNDSKOLE: [f0, f1, f2, f3, f4, f5, f6, f7,
                                          f8, f9, f10, other],
        Subject.SUBJECT_TYPE_GYMNASIE: [g1, g2, g3, student, other],
        Subject.SUBJECT_TYPE_BOTH: [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9,
                                    f10, g1, g2, g3, student, other]
    }

    level_choices = (
        (f0, _(u'0. klasse')),
        (f1, _(u'1. klasse')),
        (f2, _(u'2. klasse')),
        (f3, _(u'3. klasse')),
        (f4, _(u'4. klasse')),
        (f5, _(u'5. klasse')),
        (f6, _(u'6. klasse')),
        (f7, _(u'7. klasse')),
        (f8, _(u'8. klasse')),
        (f9, _(u'9. klasse')),
        (f10, _(u'10. klasse')),
        (g1, _(u'1.g')),
        (g2, _(u'2.g')),
        (g3, _(u'3.g')),
        (student, _(u'Student')),
        (other, _(u'Andet')),
    )
    level = models.IntegerField(
        choices=level_choices,
        blank=False,
        verbose_name=u'Niveau'
    )

    grundskole_level_conversion = {
        f0: GrundskoleLevel.f0,
        f1: GrundskoleLevel.f1,
        f2: GrundskoleLevel.f2,
        f3: GrundskoleLevel.f3,
        f4: GrundskoleLevel.f4,
        f5: GrundskoleLevel.f5,
        f6: GrundskoleLevel.f6,
        f7: GrundskoleLevel.f7,
        f8: GrundskoleLevel.f8,
        f9: GrundskoleLevel.f9,
        f10: GrundskoleLevel.f10
    }

    @staticmethod
    def grundskole_level_map():
        return {
            thisref: GrundskoleLevel.objects.get(level=grundskoleref).id
            for thisref, grundskoleref
            in Guest.grundskole_level_conversion.iteritems()
        }

    school = models.ForeignKey(
        School,
        null=True,
        verbose_name=u'Skole'
    )

    attendee_count = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=u'Antal deltagere',
        validators=[validators.MinValueValidator(int(1))]
    )

    def as_searchtext(self):
        return " ".join([unicode(x) for x in [
            self.firstname,
            self.lastname,
            self.email,
            self.phone,
            self.get_level_display(),
            self.school
        ] if x])

    def __unicode__(self):
        if self.email is not None and self.email != "":
            return "%s %s <%s>" % (self.firstname, self.lastname, self.email)
        return "%s %s" % (self.firstname, self.lastname)

    def get_email(self):
        return self.email

    def get_name(self):
        return "%s %s" % (self.firstname, self.lastname)

    def get_full_name(self):
        return self.get_name()

    def get_full_email(self):
        return full_email(self.email, self.get_name())


class Booking(models.Model):

    class Meta:
        verbose_name = _(u'booking')
        verbose_name_plural = _(u'bookinger')

    booker = models.ForeignKey(Guest)

    visit = models.ForeignKey(
        Visit,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name=_(u'Besøg')
    )

    waitinglist_spot = models.IntegerField(
        default=0,
        verbose_name=_(u'Ventelisteposition')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=u'Bemærkninger'
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True,
        on_delete=models.SET_NULL,
    )

    def get_visit_attr(self, attrname):
        if not self.visit:
            return None
        return getattr(self.visit, attrname, None)

    def raise_readonly_attr_error(self, attrname):
        raise Exception(
            _(u"Attribute %s on Booking is readonly.") % attrname +
            _(u"Set it on the Visit instead.")
        )

    @classmethod
    # Adds property to this class that will fetch the same attribute on
    # the associated visit, if available. The property will raise
    # an exception on assignment.
    def add_visit_attr(cls, attrname):
        setattr(cls, attrname, property(
            lambda self: self.get_visit_attr(attrname),
            lambda self, val: self.raise_readonly_attr_error(attrname)
        ))

    @classmethod
    def queryset_for_user(cls, user, qs=None):
        if not user or not user.userprofile:
            return Booking.objects.none()

        if qs is None:
            qs = Booking.objects.all()

        return qs.filter(
            product__organizationalunit=user.userprofile.get_unit_queryset()
        )

    def get_absolute_url(self):
        return reverse('booking-view', args=[self.pk])

    def get_url(self):
        return settings.PUBLIC_URL + self.get_absolute_url()

    def get_recipients(self, template_type):
        recipients = self.visit.get_recipients(template_type)
        if template_type.send_to_booker:
            recipients.append(self.booker)
        return recipients

    def get_reply_recipients(self, template_type):
        return self.visit.get_reply_recipients(template_type)

    def autosend(self, template_type, recipients=None,
                 only_these_recipients=False):

        visit = self.visit.real
        if visit.autosend_enabled(template_type):
            product = visit.product
            unit = visit.organizationalunit
            if recipients is None:
                recipients = set()
            else:
                recipients = set(recipients)
            if not only_these_recipients:
                recipients.update(self.get_recipients(template_type))

            KUEmailMessage.send_email(
                template_type,
                {
                    'booking': self,
                    'product': product,
                    'booker': self.booker,
                    'besoeg': visit,
                    'visit': visit,
                },
                list(recipients),
                self.visit,
                organizationalunit=unit,
                original_from_email=self.get_reply_recipients(template_type)
            )
            return True
        return False

    def as_searchtext(self):
        return " ".join([unicode(x) for x in [
            self.booker.as_searchtext(),
            self.notes
        ] if x])

    @staticmethod
    def get_latest_created():
        return Booking.objects.order_by('-statistics__created_time')

    @staticmethod
    def get_latest_updated():
        return Booking.objects.order_by('-statistics__updated_time')

    @staticmethod
    def get_latest_displayed():
        return Booking.objects.order_by('-statistics__visited_time')

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()

    def __unicode__(self):
        return _("Tilmelding #%d") % self.id

    @property
    def is_waiting(self):
        return self.waitinglist_spot > 0

    def enqueue(self):
        if not self.is_waiting:
            self.waitinglist_spot = self.visit.next_waiting_list_spot
            self.save()

    @property
    def can_dequeue(self):
        return self.is_waiting and self.visit.available_seats \
            >= self.booker.attendee_count

    def dequeue(self):
        if self.can_dequeue:
            self.waitinglist_spot = 0
            self.save()
            self.visit.normalize_waitinglist()

    @property
    def organizationalunit(self):
        return self.visit.real.organizationalunit


Booking.add_visit_attr('product')
Booking.add_visit_attr('hosts')
Booking.add_visit_attr('teachers')
Booking.add_visit_attr('host_status')
Booking.add_visit_attr('teacher_status')
Booking.add_visit_attr('room_status')
Booking.add_visit_attr('workflow_status')
Booking.add_visit_attr('comments')


class ClassBooking(Booking):

    class Meta:
        verbose_name = _(u'booking for klassebesøg')
        verbose_name_plural = _(u'bookinger for klassebesøg')

    tour_desired = models.BooleanField(
        verbose_name=_(u'Rundvisning ønsket'),
        default=False
    )
    catering_desired = models.BooleanField(
        verbose_name=_(u'Forplejning ønsket'),
        default=False
    )
    presentation_desired = models.BooleanField(
        verbose_name=_(u'Oplæg om uddannelse ønsket'),
        default=False
    )
    custom_desired = models.BooleanField(
        verbose_name=_(u'Specialtilbud ønsket'),
        default=False
    )


class TeacherBooking(Booking):

    class Meta:
        verbose_name = _(u'booking for lærerarrangement')
        verbose_name_plural = _(u'bookinger for lærerarrangementer')

    subjects = models.ManyToManyField(
        Subject,
        blank=False
    )

    def as_searchtext(self):
        result = [super(TeacherBooking, self).as_searchtext()]

        for x in self.subjects.all():
            result.append(x.name)

        return " ".join(result)


class BookingGymnasieSubjectLevel(models.Model):

    class Meta:
        verbose_name = _('fagniveau for booking (gymnasium)')
        verbose_name_plural = _('fagniveauer for bookinger (gymnasium)')

    booking = models.ForeignKey(Booking, blank=False, null=False)
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GYMNASIE,
            ]
        }
    )
    level = models.ForeignKey(GymnasieLevel, blank=False, null=False)

    def __unicode__(self):
        return u"%s (for booking %s)" % (self.display_value(), self.booking.pk)

    def display_value(self):
        return u'%s på %s niveau' % (self.subject.name, self.level)


class BookingGrundskoleSubjectLevel(models.Model):

    class Meta:
        verbose_name = _('klasseniveau for booking (grundskole)')
        verbose_name_plural = _('klasseniveauer for bookinger(grundskole)')

    booking = models.ForeignKey(Booking, blank=False, null=False)
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GRUNDSKOLE,
            ]
        }
    )
    level = models.ForeignKey(GrundskoleLevel, blank=False, null=False)

    def __unicode__(self):
        return u"%s (for booking %s)" % (self.display_value(), self.booking.pk)

    def display_value(self):
        return u'%s på %s niveau' % (self.subject.name, self.level)


class KUEmailMessage(models.Model):
    """Email data for logging purposes."""
    created = models.DateTimeField(
        blank=False,
        null=False,
        default=timezone.now
    )
    subject = models.TextField(blank=False, null=False)
    body = models.TextField(blank=False, null=False)
    htmlbody = models.TextField(blank=True, null=True)
    from_email = models.TextField(blank=False, null=False)
    original_from_email = models.TextField(blank=True, null=True)
    recipients = models.TextField(
        blank=False,
        null=False
    )
    content_type = models.ForeignKey(ContentType, null=True, default=None)
    object_id = models.PositiveIntegerField(null=True, default=None)
    content_object = GenericForeignKey('content_type', 'object_id')
    reply_nonce = models.UUIDField(
        blank=True,
        null=True,
        default=None
    )
    template_key = models.IntegerField(
        verbose_name=u'Template key',
        default=None,
        null=True,
        blank=True
    )
    template_type = models.ForeignKey(
        EmailTemplateType,
        verbose_name=u'Template type',
        default=None,
        null=True,
        blank=True
    )

    @staticmethod
    def extract_addresses(recipients):
        if type(recipients) != list:
            recipients = [recipients]
        emails = {}
        for recipient in recipients:
            name = None
            address = None
            user = None
            guest = None
            if isinstance(recipient, basestring):
                address = recipient
            elif isinstance(recipient, User):
                name = recipient.get_full_name()
                address = recipient.email
                user = recipient
            elif isinstance(recipient, Guest):
                name = recipient.get_name()
                address = recipient.get_email()
                guest = recipient
            else:
                try:
                    name = recipient.get_name()
                except:
                    pass
                try:
                    address = recipient.get_email()
                except:
                    pass
            if address is not None and address != '' and (
                    address not in emails or (
                        user and not emails[address]['user']
                    )
            ):

                email = {
                    'address': address,
                    'user': user,
                    'guest': guest,
                }

                if name is not None:
                    email['name'] = name
                    email['full'] = u"\"%s\" <%s>" % (name, address)
                else:
                    email['full'] = address

                email['get_full_name'] = email.get('name', email['full'])
                emails[address] = email
        return emails.values()

    @staticmethod
    def save_email(email_message, instance,
                   reply_nonce=None, htmlbody=None,
                   template_type=None, original_from_email=None):
        """
        :param email_message: An instance of
        django.core.mail.message.EmailMessage
        :param instance: The object that the message concerns i.e. Booking,
        Product etc.
        :return: None
        """
        ctype = ContentType.objects.get_for_model(instance)
        template_key = None if template_type is None else template_type.key
        htmlbody = None
        for (content, mimetype) in email_message.alternatives:
            if mimetype == 'text/html':
                htmlbody = content
                break
        ku_email_message = KUEmailMessage(
            subject=email_message.subject,
            body=email_message.body,
            htmlbody=htmlbody,
            from_email=email_message.from_email,
            original_from_email=", ".join([
                address['full']
                for address in KUEmailMessage.extract_addresses(
                    original_from_email
                )
            ]),
            recipients=', '.join(email_message.recipients()),
            content_type=ctype,
            object_id=instance.id,
            reply_nonce=reply_nonce,
            template_type=template_type,
            template_key=template_key
        )
        ku_email_message.save()

        return ku_email_message

    @staticmethod
    def send_email(template, context, recipients, instance, unit=None,
                   original_from_email=None, **kwargs):
        if isinstance(template, EmailTemplateType):
            key = template.key
            template = EmailTemplate.get_template(template, unit)
            if template is None:
                raise Exception(
                    u"Template with key %s does not exist!" % key
                )
        if not isinstance(template, EmailTemplate):
            raise Exception(
                u"Invalid template object '%s'" % str(template)
            )

        # Alias any visit to "besoeg" for easier use by danes
        if 'besoeg' not in context and 'visit' in context:
            context['besoeg'] = context['visit']

        if type(recipients) is not list:
            recipients = [recipients]

        emails = KUEmailMessage.extract_addresses(recipients)

        for email in emails:
            nonce = uuid.uuid4()
            ctx = {
                'organizationalunit': unit,
                'recipient': email,
                'sender': settings.DEFAULT_FROM_EMAIL,
                'reply_nonce': nonce
            }
            ctx.update(context)

            # If we know the visit and the guest we can find the
            # booking if it is missing.
            if 'booking' not in ctx and \
               'besoeg' in ctx and 'guest' in email:
                ctx['booking'] = Booking.objects.filter(
                    visit=ctx['besoeg'],
                    booker=email['guest']
                ).first()

            subject = template.expand_subject(ctx)
            subject = subject.replace('\n', '')

            body = template.expand_body(ctx, encapsulate=True).strip()

            if body.startswith("<!DOCTYPE"):
                htmlbody = body
                textbody = html2text(htmlbody)
            else:
                htmlbody = None
                textbody = body

            message = EmailMultiAlternatives(
                subject=subject,
                body=textbody,
                # from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email['full']],
            )
            if htmlbody is not None:
                message.attach_alternative(htmlbody, 'text/html')
            message.send()

            msg_obj = KUEmailMessage.save_email(
                message, instance, reply_nonce=nonce,
                template_type=template.type,
                original_from_email=original_from_email
            )
            KUEmailRecipient.register(msg_obj, email)

        # Log the sending
        if emails and instance:
            log_action(
                context.get("web_user", None),
                instance,
                LOGACTION_MAIL_SENT,
                "\n".join([unicode(x) for x in [
                    _(u"Template: ") + template.type.name,
                    _(u"Modtagere: ") + ", ".join(
                        [x['full'] for x in emails]
                    ),
                    context.get('log_message', None)
                ] if x])
            )

    def get_reply_url(self, full=False):
        url = reverse('reply-to-email', args=[self.reply_nonce])
        if full:
            url = settings.PUBLIC_URL + url
        return url

    @staticmethod
    def migrate():
        for email in KUEmailMessage.objects.all():
            if email.template_key is not None:
                email.template_type = EmailTemplateType.get(
                    email.template_key
                )
                email.save()


class KUEmailRecipient(models.Model):
    email_message = models.ForeignKey(KUEmailMessage)
    name = models.TextField(blank=True, null=True)
    formatted_address = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True)

    @staticmethod
    def register(msg_obj, userdata):
        result = KUEmailRecipient(
            email_message=msg_obj,
            name=userdata.get("name", None),
            formatted_address=userdata.get("full", None),
            email=userdata.get("address", None),
            user=userdata.get("user", None),
        )
        result.save()
        return result


class BookerResponseNonce(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    booker = models.ForeignKey(Guest)
    created = models.DateTimeField(default=timezone.now)
    expires_in = models.DurationField(default=timedelta(hours=48))

    def as_url(self):
        return reverse('booking-accept-view', args=[self.uuid])

    def as_full_url(self, request):
        return request.build_absolute_uri(self.as_url())

    def as_public_url(self):
        return settings.PUBLIC_URL + self.as_url()

    def is_expired(self):
        return (self.created + self.expires_in) < timezone.now()

    @classmethod
    def create(cls, booker, **kwargs):
        attrs = {
            'booker': booker,
        }
        attrs.update(kwargs)

        return cls.objects.create(**attrs)


class Evaluation(models.Model):
    url = models.CharField(
        max_length=1024,
        verbose_name=u'Evaluerings-URL'
    )
    visit = models.OneToOneField(
        Visit,
        null=False,
        blank=False
    )
    guests = models.ManyToManyField(
        Guest,
        through='EvaluationGuest'
    )

    def send_notification(self, template_type, new_status, filter=None):
        qs = self.evaluationguest_set.all()
        if filter is not None:
            qs = qs.filter(**filter)
        for evalguest in qs:
            for booking in evalguest.guest.booking_set.filter(
                visit=self.visit
            ):
                # There really should be only one here
                try:
                    sent = booking.autosend(
                        template_type
                    )
                    if sent:
                        evalguest.status = new_status
                        evalguest.save()
                except Exception as e:
                    print e

    def send_first_notification(self):
        self.send_notification(
            EmailTemplateType.notify_guest__evaluation_first,
            EvaluationGuest.STATUS_FIRST_SENT
        )

    def send_second_notification(self):
        self.send_notification(
            EmailTemplateType.notify_guest__evaluation_second,
            EvaluationGuest.STATUS_SECOND_SENT,
            {'status': EvaluationGuest.STATUS_FIRST_SENT}
        )

    def status_count(self, status):
        return self.evaluationguest_set.filter(status=status).count()

    def no_participation_count(self):
        return self.status_count(EvaluationGuest.STATUS_NO_PARTICIPATION)

    def not_sent_count(self):
        return self.status_count(EvaluationGuest.STATUS_NOT_SENT)

    def first_sent_count(self):
        return self.status_count(EvaluationGuest.STATUS_FIRST_SENT)

    def second_sent_count(self):
        return self.status_count(EvaluationGuest.STATUS_SECOND_SENT)

    def link_clicked_count(self):
        return self.status_count(EvaluationGuest.STATUS_LINK_CLICKED)


class EvaluationGuest(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        null=False,
        blank=False
    )
    guest = models.OneToOneField(
        Guest,
        null=False,
        blank=False
    )
    STATUS_NO_PARTICIPATION = 0
    STATUS_NOT_SENT = 1
    STATUS_FIRST_SENT = 2
    STATUS_SECOND_SENT = 3
    STATUS_LINK_CLICKED = 4
    status_choices = [
        (STATUS_NO_PARTICIPATION, _(u'Modtager ikke evaluering')),
        (STATUS_NOT_SENT, _(u'Ikke afholdt / ikke afsendt')),
        (STATUS_FIRST_SENT, _(u'Sendt første gang')),
        (STATUS_SECOND_SENT, _(u'Sendt anden gang')),
        (STATUS_LINK_CLICKED, _(u'Har klikket på link'))
    ]
    status = models.SmallIntegerField(
        choices=status_choices,
        verbose_name=u'status'
    )
    shortlink_id = models.CharField(
        max_length=16,
    )

    @property
    def shortlink(self):
        return "http://localhost:8000/l/%s" % self.shortlink_id

    @property
    def status_display(self):
        for status, label in self.status_choices:
            if status == self.status:
                return label

    def save(self, *args, **kwargs):
        if self.shortlink_id is None or len(self.shortlink_id) == 0:
            self.shortlink_id = ''.join(get_random_string(length=13))
        return super(EvaluationGuest, self).save(*args, **kwargs)

    @property
    def url(self):
        template = Template(
            "{% load booking_tags %}" +
            "{% load i18n %}" +
            "{% language 'da' %}\n" +
            unicode(self.evaluation.url) +
            "{% endlanguage %}\n"
        )
        context = make_context({
            'evaluation': self.evaluation,
            'guest': self.guest,
            'visit': self.evaluation.visit
        })

        rendered = template.render(context)
        return rendered

        # return self.evaluation.url

    def link_clicked(self):
        self.status = self.STATUS_LINK_CLICKED
        self.save()


from booking.resource_based import models as rb_models  # noqa

EventTime = rb_models.EventTime
Calendar = rb_models.Calendar
CalendarEvent = rb_models.CalendarEvent
CalendarEventInstance = rb_models.CalendarEventInstance
ResourceType = rb_models.ResourceType
Resource = rb_models.Resource
TeacherResource = rb_models.TeacherResource
HostResource = rb_models.HostResource
RoomResource = rb_models.RoomResource
ItemResource = rb_models.ItemResource
VehicleResource = rb_models.VehicleResource
ResourcePool = rb_models.ResourcePool
ResourceRequirement = rb_models.ResourceRequirement
VisitResource = rb_models.VisitResource
