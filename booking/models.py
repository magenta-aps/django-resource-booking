# encoding: utf-8

import math
import random
import re
import uuid
from datetime import timedelta, datetime, date, time

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.db import models
from django.db.models import Case, When
from django.db.models import Q
from django.db.models import Sum
from django.db.models.base import ModelBase
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.template.base import Template, VariableNode
from django.template.context import make_context
from django.template.loader import get_template
from django.template.loader_tags import IncludeNode
from django.utils import formats
from django.utils import six
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as __

from booking.constants import LOGACTION_MAIL_SENT, AVAILABLE_SEATS_NO_LIMIT
from booking.logging import log_action
from booking.managers import (
    VisitQuerySet,
    BookingQuerySet,
    ProductQuerySet,
    SchoolQuerySet,
    KUEmailMessageQuerySet,
    SurveyXactEvaluationGuestQuerySet
)
from booking.mixins import AvailabilityUpdaterMixin
from booking.utils import (
    ClassProperty,
    CustomStorage,
    bool2int,
    getattr_long,
    prune_list,
    surveyxact_upload,
    flatten,
    full_email,
    get_related_content_types,
    html2text,
    INFINITY,
    merge_dicts,
    prose_list_join
)

from user_profile.constants import COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR
from user_profile.constants import TEACHER, HOST, NONE, get_role_name

BLANK_LABEL = '---------'
BLANK_OPTION = (None, BLANK_LABEL,)


class RoomResponsible(models.Model):
    class Meta:
        verbose_name = _('Lokaleanvarlig')
        verbose_name_plural = _('Lokaleanvarlige')

    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=14, null=True, blank=True)

    organizationalunit = models.ForeignKey(
        "OrganizationalUnit",
        blank=True,
        null=True,
        on_delete=models.SET_NULL
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
    admin_delete_button.short_description = _("Delete")

    def __str__(self):
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
        verbose_name = _("enhedstype")
        verbose_name_plural = _("Enhedstyper")

    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name


class OrganizationalUnit(models.Model):
    """A generic organizational unit, such as a faculty or an institute"""

    class Meta:
        verbose_name = _("enhed")
        verbose_name_plural = _("enheder")
        ordering = ['name']

    name = models.CharField(max_length=100)
    type = models.ForeignKey(
        OrganizationalUnitType,
        on_delete=models.CASCADE
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    contact = models.ForeignKey(
        User, null=True, blank=True,
        verbose_name=_('Kontaktperson'),
        related_name="contactperson_for_units",
        on_delete=models.SET_NULL,
    )
    url = models.URLField(
        verbose_name='Hjemmeside',
        null=True,
        blank=True
    )
    autoassign_resources_enabled = models.BooleanField(
        verbose_name=_('Automatisk ressourcetildeling mulig'),
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

    def __str__(self):
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

    def get_coordinators(self):
        return self.get_users(COORDINATOR)

    def get_editors(self):

        # Try using all available coordinators
        res = self.get_users(COORDINATOR)
        if len(res) > 0:
            return res

        # If no coordinators was found use faculty editors
        res = User.objects.filter(
            userprofile__organizationalunit__in=self.get_faculty_queryset(),
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
            recipients.extend(KUEmailRecipient.multiple(
                self.get_hosts(), KUEmailRecipient.TYPE_HOST
            ))

        if template_type.send_to_unit_teachers:
            recipients.extend(KUEmailRecipient.multiple(
                self.get_teachers(), KUEmailRecipient.TYPE_TEACHER
            ))

        if template_type.send_to_editors:
            recipients.extend(KUEmailRecipient.multiple(
                self.get_editors(), KUEmailRecipient.TYPE_EDITOR
            ))

        return recipients

    def get_reply_recipients(self, template_type):
        if template_type.reply_to_unit_responsible:
            return [KUEmailRecipient.create(
                self.contact,
                KUEmailRecipient.TYPE_UNIT_RESPONSIBLE
            )]
        return []

    @classmethod
    def root_unit_id(cls):
        unit = cls.objects.filter(
            type__name="Københavns Universitet"
        ).first()
        if unit:
            return unit.pk
        else:
            return ""


# Master data related to bookable resources start here
class Subject(models.Model):
    """A relevant subject from primary or secondary education."""

    class Meta:
        verbose_name = _("fag")
        verbose_name_plural = _("fag")
        ordering = ["name"]

    SUBJECT_TYPE_GYMNASIE = 2**0
    SUBJECT_TYPE_GRUNDSKOLE = 2**1
    # NEXT_VALUE = 2**2

    SUBJECT_TYPE_BOTH = SUBJECT_TYPE_GYMNASIE | SUBJECT_TYPE_GRUNDSKOLE

    type_choices = (
        (SUBJECT_TYPE_GYMNASIE, _('Gymnasie')),
        (SUBJECT_TYPE_GRUNDSKOLE, _('Grundskole')),
        (SUBJECT_TYPE_BOTH, _('Både gymnasie og grundskole')),
    )

    name = models.CharField(max_length=256)
    subject_type = models.IntegerField(
        choices=type_choices,
        verbose_name='Skoleniveau',
        default=SUBJECT_TYPE_GYMNASIE,
        blank=False,
    )
    description = models.TextField(blank=True)

    def __str__(self):
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

    ALL_NAME = 'Alle'

    @classmethod
    def get_all(cls):
        try:
            return Subject.objects.get(name=Subject.ALL_NAME)
        except Subject.DoesNotExist:
            subject = Subject(
                name=Subject.ALL_NAME,
                subject_type=cls.SUBJECT_TYPE_BOTH,
                description='Placeholder for "alle fag"'
            )
            subject.save()
            return subject

    def is_all(self):
        return self.name == Subject.ALL_NAME


class Link(models.Model):
    """"An URL and relevant metadata."""
    url = models.URLField()
    name = models.CharField(max_length=256)
    # Note: "description" is intended as automatic text when linking in web
    # pages.
    description = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tag class, just name and description fields."""
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Topic(models.Model):
    """Tag class, just name and description fields."""

    class Meta:
        verbose_name = _("emne")
        verbose_name_plural = _("emner")

    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StudyMaterial(models.Model):
    """Material for the students to study before visiting."""

    class Meta:
        verbose_name = _('undervisningsmateriale')
        verbose_name_plural = _('undervisningsmaterialer')

    URL = 0
    ATTACHMENT = 1
    study_material_choices = (
        (URL, _("URL")),
        (ATTACHMENT, _("Vedhæftet fil"))
    )
    type = models.IntegerField(choices=study_material_choices, default=URL)
    url = models.URLField(null=True, blank=True)
    file = models.FileField(upload_to='material', null=True,
                            blank=True, storage=CustomStorage())
    product = models.ForeignKey('Product', null=True,
                                on_delete=models.CASCADE,)

    def __str__(self):
        s = "{0}: {1}".format(
            'URL' if self.type == self.URL else _("Vedhæftet fil"),
            self.url if self.type == self.URL else self.file
        )
        return s


class Locality(models.Model):
    """A locality where a visit may take place."""

    class Meta:
        verbose_name = _('lokalitet')
        verbose_name_plural = _('lokaliteter')
        ordering = ["name"]

    name = models.CharField(max_length=256, verbose_name=_('Navn'))
    description = models.TextField(blank=True, verbose_name=_('Beskrivelse'))
    address_line = models.CharField(max_length=256, verbose_name=_('Adresse'))
    zip_city = models.CharField(
        max_length=256, verbose_name=_('Postnummer og by')
    )
    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        verbose_name=_('Enhed'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    # Used to signify special addreses with no pre-known location, such as
    # the booker's own location
    no_address = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def name_and_address(self):
        if self.no_address:
            return self.name
        return "%s (%s)" % (
            self.name,
            ", ".join([
                x for x in [self.address_line, self.zip_city]
                if len(x.strip()) > 0
            ])
        )

    @property
    def full_address(self):
        return " ".join([
            x for x in [self.name, self.address_line, self.zip_city]
            if len(x.strip()) > 0
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

    @staticmethod
    def create_defaults():
        from booking.data import localities
        data = localities.localities
        for item in data:
            try:
                Locality.objects.get(name=item['name'])
            except Locality.DoesNotExist:
                Locality(**item).save()


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
    NOTIFY_GUEST__BOOKING_CREATED_UNTIMED = 23  # Ticket 16914
    NOTIFY_GUEST__EVALUATION_FIRST = 24  # Ticket 13819
    NOTIFY_GUEST__EVALUATION_FIRST_STUDENTS = 26  # Ticket 13819
    NOTIFY_GUEST__EVALUATION_SECOND = 25  # Ticket 13819
    NOTIFY_GUEST__EVALUATION_SECOND_STUDENTS = 27  # Ticket 13819

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
        verbose_name='Type',
        default=1
    )

    name_da = models.CharField(
        verbose_name='Navn',
        max_length=1024,
        null=True
    )

    ordering = models.IntegerField(
        verbose_name='Sortering',
        default=0
    )

    @property
    def name(self):
        return self.name_da

    def __str__(self):
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

    # Template will be autosent to booker on waitinglist
    send_to_booker_on_waitinglist = models.BooleanField(default=False)

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

    # Template will be autosent to room responsible of the product
    send_to_room_responsible = models.BooleanField(default=False)

    # Does the "days" field make sense?
    enable_days = models.BooleanField(default=False)

    # Does the {{ booking }} variable make sense
    enable_booking = models.BooleanField(default=False)

    avoid_already_assigned = models.BooleanField(default=False)

    is_default = models.BooleanField(default=False)

    enable_autosend = models.BooleanField(default=False)

    form_show = models.BooleanField(default=False)

    disabled_for_product_types = models.TextField(default=None, null=True)

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

    @property
    def disabled_product_types(self):
        if self.disabled_for_product_types is None:
            return []
        return [int(p) for p in self.disabled_for_product_types.split(' ')]

    def set_disabled_product_types(self, product_types):
        self.disabled_for_product_types = ' '.join([
            str(p) for p in product_types
        ])

    @staticmethod
    def set_default(key, **kwargs):
        try:
            template_type = EmailTemplateType.objects.get(key=key)
        except EmailTemplateType.DoesNotExist:
            template_type = EmailTemplateType(key=key)
        for attr in template_type._meta.fields:
            if attr.name in kwargs:
                if attr.name == 'disabled_for_product_types':
                    template_type.set_disabled_product_types(kwargs[attr.name])
                else:
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
            name_da='Besked til gæst ved tilmelding (med fast tid)',
            manual_sending_visit_enabled=False,
            manual_sending_mpv_enabled=False,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=1
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED,
            name_da='Besked til gæst ved tilmelding (besøg uden fast tid)',
            manual_sending_visit_enabled=False,
            manual_sending_mpv_enabled=False,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=2
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_WAITING,
            name_da='Besked til gæster der har tilmeldt sig venteliste',
            manual_sending_visit_enabled=False,
            manual_sending_mpv_enabled=False,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=3
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__GENERAL_MSG,
            name_da='Generel besked til gæst(er)',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=False,
            ordering=4
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_OPEN,
            name_da='Mail til gæst fra venteliste, '
                    'der får tilbudt plads på besøget',
            manual_sending_visit_enabled=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=False,
            ordering=5
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_ACCEPTED,
            name_da='Besked til gæst ved accept af plads (fra venteliste)',
            manual_sending_visit_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=True,
            enable_booking=True,
            enable_autosend=True,
            is_default=True,
            form_show=False,
            ordering=6
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__SPOT_REJECTED,
            name_da='Besked til gæst ved afvisning af plads (fra venteliste)',
            manual_sending_visit_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=True,
            enable_booking=True,
            enable_autosend=False,
            form_show=False,
            ordering=7
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST_REMINDER,
            name_da='Reminder til gæst',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            enable_days=True,
            enable_autosend=True,
            form_show=True,
            ordering=8
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED,
            name_da='Besked til koordinator, når gæst har tilmeldt sig besøg',
            manual_sending_visit_enabled=False,
            send_to_contactperson=True,
            enable_booking=True,
            is_default=True,
            enable_autosend=True,
            form_show=True,
            ordering=9
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_EDITORS__SPOT_REJECTED,
            name_da='Besked til koordinatorer ved afvisning '
                    'af plads (fra venteliste)',
            manual_sending_visit_enabled=False,
            send_to_contactperson=True,
            enable_booking=True,
            enable_autosend=True,
            is_default=True,
            form_show=False,
            ordering=10
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER,
            name_da='Besked til vært, når en gæst har lavet en tilmelding',
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
            name_da='Besked til underviser, når en gæst '
                    'har lavet en tilmelding',
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
            name_da='Bekræftelsesmail til vært',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            send_to_visit_added_host=True,
            enable_autosend=True,
            form_show=True,
            ordering=13
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED,
            name_da='Bekræftelsesmail til underviser',
            manual_sending_visit_enabled=True,
            send_to_visit_added_teacher=True,
            enable_autosend=True,
            form_show=True,
            ordering=14
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE,
            name_da='Notifikation til koordinatorer om '
                    'ledig værtsrolle på besøg',
            manual_sending_visit_enabled=False,
            manual_sending_mpv_sub_enabled=False,
            send_to_editors=True,
            enable_days=True,
            enable_autosend=True,
            form_show=True,
            ordering=15
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_HOST__REQ_ROOM,
            name_da='Besked til lokaleansvarlig',
            send_to_room_responsible=True,
            manual_sending_visit_enabled=True,
            manual_sending_mpv_sub_enabled=True,
            enable_autosend=True,
            form_show=True,
            ordering=16
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED,
            name_da='Besked til alle ved aflysning',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_contactperson=True,
            send_to_room_responsible=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=17
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE,
            name_da='Besked om færdigplanlagt besøg til alle involverede',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_contactperson=True,
            send_to_room_responsible=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_booking=True,
            enable_autosend=True,
            form_show=True,
            ordering=18
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER,
            name_da='Reminder om besøg til alle involverede',
            manual_sending_visit_enabled=True,
            manual_sending_booking_enabled=True,
            manual_sending_booking_mpv_enabled=True,
            send_to_contactperson=True,
            send_to_room_responsible=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            send_to_visit_hosts=True,
            send_to_visit_teachers=True,
            enable_days=True,
            enable_autosend=True,
            form_show=True,
            ordering=19
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE,
            name_da='Besked til tilbudsansvarlig',
            manual_sending_visit_enabled=True,
            enable_autosend=False,
            form_show=False,
            ordering=21
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__EMAIL_REPLY,
            # name_da=u'Svar på e-mail fra systemet',
            name_da='Skabelon med informationer om tilmelding fra gæst',
            enable_autosend=False,
            form_show=False,
            ordering=22
        )

        EmailTemplateType.set_default(
            EmailTemplateType.SYSTEM__USER_CREATED,
            name_da='Besked til bruger ved brugeroprettelse',
            manual_sending_visit_enabled=True,
            form_show=False,
            ordering=23
        )

        evaluation_disabled_for = [
            key
            for key, label in Product.resource_type_choices
            if key not in Product.evaluation_autosends_enabled
        ]

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST,
            name_da='Besked til bruger angående evaluering (første besked)',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            form_show=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            enable_autosend=True,
            enable_booking=True,
            is_default=True,
            ordering=24,
            disabled_for_product_types=evaluation_disabled_for
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST_STUDENTS,
            name_da='Besked til bruger angående evaluering (første besked), '
                    'for videresendelse til elever',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            form_show=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            enable_autosend=True,
            enable_booking=True,
            is_default=True,
            ordering=25,
            disabled_for_product_types=evaluation_disabled_for
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND,
            name_da='Besked til bruger angående evaluering (anden besked)',
            manual_sending_visit_enabled=True,
            manual_sending_mpv_enabled=True,
            form_show=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            enable_autosend=True,
            enable_booking=True,
            enable_days=False,
            is_default=True,
            ordering=26,
            disabled_for_product_types=evaluation_disabled_for
        )

        EmailTemplateType.set_default(
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND_STUDENTS,
            name_da='Besked til bruger angående evaluering (anden besked), '
                    'for videresendelse til elever',
            manual_sending_visit_enabled=True,
            form_show=True,
            send_to_booker=True,
            send_to_booker_on_waitinglist=False,
            enable_autosend=True,
            enable_booking=True,
            is_default=True,
            ordering=27,
            disabled_for_product_types=evaluation_disabled_for
        )

    @staticmethod
    def get_keys(**kwargs):
        return [
            template_type.key
            for template_type in EmailTemplateType.objects.filter(**kwargs)
        ]

    @staticmethod
    def get_choices(**kwargs):
        types = EmailTemplateType.objects.filter(**kwargs).order_by('ordering')
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
                if qs.count() == 0 and product.type not in \
                        template_type.disabled_product_types:
                    print(
                        "    creating autosend type %d for product %d" %
                        (template_type.key, product.id)
                    )
                    autosend = ProductAutosend(
                        template_key=template_type.key,
                        template_type=template_type,
                        product=product,
                        enabled=template_type.is_default
                    )
                    autosend.save()
                elif qs.count() > 1:
                    print(
                        "    removing extraneous autosend %d for product %d" %
                        (template_type.key, product.id)
                    )
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
                    if qs.count() == 0 and visit.product.type not in \
                            template_type.disabled_product_types:
                        print(
                                "    creating autosend type %d "
                                "for visit %d" % (template_type.key, visit.id)
                        )
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
                        print(
                                "    removing extraneous autosend %d for "
                                "visit %d" % (template_type.key, visit.id)
                        )
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
        verbose_name='Type',
        default=1
    )

    type = models.ForeignKey(
        EmailTemplateType,
        null=True,
        on_delete=models.SET_NULL
    )

    subject = models.CharField(
        max_length=65584,
        verbose_name='Emne'
    )

    body = models.CharField(
        max_length=65584,
        verbose_name='Tekst'
    )

    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        verbose_name='Enhed',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    @property
    def name(self):
        return self.type.name

    def expand_subject(self, context, keep_placeholders=False):
        return self._expand(self.subject, context, keep_placeholders, False)

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
    def get_template_object(template_text, escape=True):
        # Add default includes and encapsulate in danish
        lines = [] + EmailTemplate.default_includes + ["{% language 'da' %}"]
        if not escape:
            lines.append("{% autoescape off %}")
        lines.append(template_text)
        if not escape:
            lines.append("{% endautoescape %}")
        lines.append("{% endlanguage %}")
        encapsulated = "\n".join(lines)
        return Template(encapsulated)

    @staticmethod
    def _expand(text, context, keep_placeholders=False, escape=True):
        template = EmailTemplate.get_template_object(text, escape)

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
            unit = unit.parent if unit.parent != unit else None
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
            self._add_template_vars(template, variables)
        return variables

    def _add_template_vars(self, template, variables):
        for node in template:
            # Include everything that is send to included sub-templates
            for x in node.get_nodes_by_type(IncludeNode):
                try:
                    subtemplate = get_template(x.template.var)
                    self._add_template_vars(subtemplate.template, variables)
                except Exception as e:
                    print("Error while processcing included template: %s" % e)
            for x in node.get_nodes_by_type(VariableNode):
                variables.append(str(x.filter_expression))

    @staticmethod
    def migrate():
        for emailtemplate in EmailTemplate.objects.all():
            emailtemplate.type = EmailTemplateType.get(
                emailtemplate.key
            )
            emailtemplate.save()


class KUEmailRecipient(models.Model):

    TYPE_UNKNOWN = 0
    TYPE_GUEST = 1
    TYPE_TEACHER = 2
    TYPE_HOST = 3
    TYPE_COORDINATOR = 4
    TYPE_EDITOR = 5
    TYPE_INQUIREE = 6
    TYPE_ROOM_RESPONSIBLE = 7
    TYPE_PRODUCT_RESPONSIBLE = 8
    TYPE_UNIT_RESPONSIBLE = 9

    type_choices = [
        (TYPE_UNKNOWN, 'Anden'),
        (TYPE_GUEST, 'Gæst'),
        (TYPE_TEACHER, 'Underviser'),
        (TYPE_HOST, 'Vært'),
        (TYPE_COORDINATOR, 'Koordinator'),
        (TYPE_INQUIREE, 'Modtager af spørgsmål'),
        (TYPE_ROOM_RESPONSIBLE, 'Lokaleansvarlig'),
        (TYPE_PRODUCT_RESPONSIBLE, 'Tilbudsansvarlig'),
        (TYPE_UNIT_RESPONSIBLE, 'Enhedsansvarlig')
    ]

    type_map = {
        TEACHER: TYPE_TEACHER,
        HOST: TYPE_HOST,
        COORDINATOR: TYPE_COORDINATOR,
        # ADMINISTRATOR = 3
        FACULTY_EDITOR: TYPE_EDITOR,
        NONE: TYPE_UNKNOWN
    }

    all_types = set([k for k, v in type_choices])

    email_message = models.ForeignKey(
        'KUEmailMessage',
        on_delete=models.CASCADE
    )
    name = models.TextField(blank=True, null=True)
    formatted_address = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    guest = models.ForeignKey(
        'Guest',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    type = models.IntegerField(choices=type_choices, default=TYPE_UNKNOWN)

    def __str__(self):
        return "KUEmailRecipient<%s,%s>" % (self.email, self.role_name)

    @classmethod
    def create(cls, base=None, recipient_type=None):
        ku_email_recipient = cls()
        address = None
        if isinstance(base, str):
            address = base
        elif isinstance(base, User):
            ku_email_recipient.user = base
            ku_email_recipient.name = base.get_full_name()
            ku_email_recipient.type = KUEmailRecipient.type_map.get(
                ku_email_recipient.user.userprofile.get_role(), recipient_type
            )
            address = base.email
        elif isinstance(base, Guest):
            ku_email_recipient.guest = base
            ku_email_recipient.name = base.get_name()
            ku_email_recipient.type = KUEmailRecipient.TYPE_GUEST
            address = base.get_email()
        else:
            try:
                ku_email_recipient.name = base.get_name()
            except:
                pass
            try:
                address = base.get_email()
            except:
                pass

        if recipient_type is not None:
            ku_email_recipient.type = recipient_type

        if address is not None and address != '':
            if ku_email_recipient.name is not None:
                ku_email_recipient.formatted_address = u"\"%s\" <%s>" % (
                    ku_email_recipient.name,
                    address
                )
            else:
                ku_email_recipient.formatted_address = address
        ku_email_recipient.email = address

        return ku_email_recipient

    def get_full_name(self):
        return self.name if self.name is not None else self.formatted_address

    @property
    def role_name(self):
        for recipient_type, name in KUEmailRecipient.type_choices:
            if self.type == recipient_type:
                return name
        return "Ukendt (%d)" % self.type

    @staticmethod
    def multiple(bases, recipient_type=None):
        if isinstance(bases, QuerySet):
            bases = list(bases)
        if type(bases) is not list:
            bases = [bases]
        return list([
            x for x in [
                KUEmailRecipient.create(base, recipient_type) for base in bases
            ] if x.formatted_address is not None
        ])

    @property
    def is_guest(self):
        return self.type == KUEmailRecipient.TYPE_GUEST

    @property
    def is_teacher(self):
        return self.type == KUEmailRecipient.TYPE_TEACHER

    @property
    def is_host(self):
        return self.type == KUEmailRecipient.TYPE_HOST

    @property
    def is_coordinator(self):
        return self.type == KUEmailRecipient.TYPE_COORDINATOR

    @property
    def is_editor(self):
        return self.type == KUEmailRecipient.TYPE_EDITOR

    @property
    def is_inquiree(self):
        return self.type == KUEmailRecipient.TYPE_INQUIREE

    @property
    def is_room_responsible(self):
        return self.type == KUEmailRecipient.TYPE_ROOM_RESPONSIBLE

    @property
    def is_product_responsible(self):
        return self.type == KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE

    @property
    def is_unit_responsible(self):
        return self.type == KUEmailRecipient.TYPE_UNIT_RESPONSIBLE

    @staticmethod
    def filter_list(recp_list, types=all_types):
        return [x for x in recp_list if x.type in types]

    @staticmethod
    def exclude_list(recp_list, types=all_types):
        return [x for x in recp_list if x.type not in types]


class ObjectStatistics(models.Model):
    class Meta:
        verbose_name_plural = "object statistics"

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
        verbose_name = _("gymnasiefagtilknytning")
        verbose_name_plural = _("gymnasiefagtilknytninger")
        ordering = ["subject__name"]

    class_level_choices = [(i, str(i)) for i in range(0, 11)]

    product = models.ForeignKey(
        "Product",
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        blank=False,
        null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GYMNASIE,
                Subject.SUBJECT_TYPE_BOTH
            ]
        },
        on_delete=models.CASCADE
    )

    display_value_cached = models.CharField(
        null=True,
        max_length=100
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
            level = GymnasieLevel.objects.get(pk=x)
            f.level.add(level)

        return f

    def __str__(self):
        return "%s (for '%s')" % (self.display_value(), self.product.title)

    def ordered_levels(self):
        return self.level.all().order_by('level')

    @classmethod
    def display(cls, subject, levels):
        levels = [str(x) for x in levels.all()]
        levels_desc = None

        nr_levels = len(levels)
        if nr_levels == 1:
            levels_desc = levels[0]
        elif nr_levels == 2:
            levels_desc = '%s eller %s' % (levels[0], levels[1])
        elif nr_levels > 2:
            last = levels.pop()
            levels_desc = '%s eller %s' % (", ".join(levels), last)

        if levels_desc:
            return '%s på %s niveau' % (
                subject.name, levels_desc
            )
        else:
            return subject.name

    def display_value(self):
        if self.display_value_cached is None:
            self.display_value_cached = ProductGymnasieFag.display(
                self.subject, self.ordered_levels()
            )
            self.save()
        return self.display_value_cached

    def as_submitvalue(self):
        res = str(self.subject.pk)
        levels = ",".join([str(x.pk) for x in self.ordered_levels().all()])

        if levels:
            res = ",".join([res, levels])

        return res


class ProductGrundskoleFag(models.Model):
    class Meta:
        verbose_name = _("grundskolefagtilknytning")
        verbose_name_plural = _("grundskolefagtilknytninger")
        ordering = ["subject__name"]

    class_level_choices = [(i, str(i)) for i in range(0, 11)]

    product = models.ForeignKey(
        "Product",
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GRUNDSKOLE,
                Subject.SUBJECT_TYPE_BOTH
            ]
        },
        on_delete=models.CASCADE
    )

    # TODO: We should validate that min <= max here.
    class_level_min = models.IntegerField(choices=class_level_choices,
                                          default=0,
                                          verbose_name=_('Klassetrin fra'))
    class_level_max = models.IntegerField(choices=class_level_choices,
                                          default=10,
                                          verbose_name=_('Klassetrin til'))

    @classmethod
    def create_from_submitvalue(cls, product, value):
        f = ProductGrundskoleFag(product=product)

        values = value.split(",")

        # First element in value list is pk of subject
        f.subject = Subject.objects.get(pk=values.pop(0))

        f.class_level_min = values.pop(0) or 0 if values else 0
        f.class_level_max = values.pop(0) or 0 if values else 0

        f.save()

        return f

    def __str__(self):
        return "%s (for '%s')" % (self.display_value(), self.product.title)

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
            return '%s på klassetrin %s' % (
                subject.name,
                "-".join([str(x) for x in class_range])
            )
        else:
            return subject.name

    def display_value(self):
        return ProductGrundskoleFag.display(
            self.subject, self.class_level_min, self.class_level_max
        )

    def as_submitvalue(self):
        return ",".join([
            str(self.subject.pk),
            str(self.class_level_min or 0),
            str(self.class_level_max or 0)
        ])


class GymnasieLevel(models.Model):

    class Meta:
        verbose_name = _('Gymnasieniveau')
        verbose_name_plural = _('Gymnasieniveauer')
        ordering = ['level']

    # Level choices - A, B or C
    A = 0
    B = 1
    C = 2

    level_choices = (
        (A, 'A'), (B, 'B'), (C, 'C')
    )

    level = models.IntegerField(choices=level_choices,
                                verbose_name=_("Gymnasieniveau"),
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

    def __str__(self):
        return self.get_level_display()


class GrundskoleLevel(models.Model):

    class Meta:
        verbose_name = _('Grundskoleniveau')
        verbose_name_plural = _('Grundskoleniveauer')
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
        (f0, _('0. klasse')),
        (f1, _('1. klasse')),
        (f2, _('2. klasse')),
        (f3, _('3. klasse')),
        (f4, _('4. klasse')),
        (f5, _('5. klasse')),
        (f6, _('6. klasse')),
        (f7, _('7. klasse')),
        (f8, _('8. klasse')),
        (f9, _('9. klasse')),
        (f10, _('10. klasse')),
    )

    level = models.IntegerField(choices=level_choices,
                                verbose_name=_("Grundskoleniveau"),
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

    def __str__(self):
        return self.get_level_display()


class Product(AvailabilityUpdaterMixin, models.Model):
    """A bookable Product of any kind."""

    class Meta:
        verbose_name = _("tilbud")
        verbose_name_plural = _("tilbud")
        indexes = [
            GinIndex(fields=['search_vector'])
        ]

    objects = ProductQuerySet.as_manager()

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
        (STUDENT_FOR_A_DAY, _("Studerende for en dag")),
        (STUDIEPRAKTIK, _("Studiepraktik")),
        (OPEN_HOUSE, _("Åbent hus")),
        (TEACHER_EVENT, _("Tilbud til undervisere")),
        (GROUP_VISIT, _("Besøg med klassen")),
        (STUDY_PROJECT, _("Studieretningsprojekt")),
        (ASSIGNMENT_HELP, _("Lektiehjælp")),
        (OTHER_OFFERS,  _("Andre tilbud")),
        (STUDY_MATERIAL, _("Undervisningsmateriale"))
    )

    evaluation_autosends_enabled = [
        GROUP_VISIT,
        OTHER_OFFERS
    ]

    # Institution choice - primary or secondary school.
    PRIMARY = 0
    SECONDARY = 1

    institution_choices = Subject.type_choices

    # Level choices - A, B or C
    A = 0
    B = 1
    C = 2

    level_choices = (
        (A, 'A'), (B, 'B'), (C, 'C')
    )

    # Product state - created, active and discontinued.
    CREATED = 0
    ACTIVE = 1
    DISCONTINUED = 2

    state_choices = (
        BLANK_OPTION,
        (CREATED, _("Under udarbejdelse")),
        (ACTIVE, _("Offentlig")),
        (DISCONTINUED, _("Skjult"))
    )

    class_level_choices = [(i, str(i)) for i in range(0, 11)]

    type = models.IntegerField(choices=resource_type_choices,
                               default=STUDY_MATERIAL)
    state = models.IntegerField(choices=state_choices,
                                verbose_name=_("Status"), blank=False)
    title = models.CharField(
        max_length=80,
        blank=False,
        verbose_name=_('Titel')
    )
    teaser = models.TextField(
        max_length=300,
        blank=False,
        verbose_name=_('Teaser')
    )
    description = models.TextField(
        blank=False,
        verbose_name=_('Beskrivelse')
    )
    mouseover_description = models.CharField(
        max_length=512, blank=True, verbose_name=_('Mouseover-tekst')
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
                                            verbose_name=_('Institution'),
                                            default=SECONDARY,
                                            blank=False)

    locality = models.ForeignKey(
        Locality,
        verbose_name=_('Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    rooms = models.ManyToManyField(
        'Room',
        verbose_name=_('Lokaler'),
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
            TIME_MODE_GUEST_SUGGESTED,
            TIME_MODE_RESOURCE_CONTROLLED,
            TIME_MODE_NONE,
            TIME_MODE_NO_BOOKING,
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
         _("Tilbuddet har ingen tidspunkter og ingen tilmelding")),
        (TIME_MODE_RESOURCE_CONTROLLED,
         _("Tilbuddets tidspunkter styres af ressourcer")),
        (TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN,
         _("Tilbuddets tidspunkter styres af ressourcer,"
           " med automatisk tildeling")),
        (TIME_MODE_SPECIFIC,
         _("Tilbuddet har faste tidspunkter")),
        (TIME_MODE_NO_BOOKING,
         _("Tilbuddet har faste tidspunkter, men er uden tilmelding")),
        (TIME_MODE_GUEST_SUGGESTED,
         _("Gæster foreslår mulige tidspunkter")),
    )

    # Note: Default here is a type that can not be selected in the dropdown.
    # This is to get that default on products that does not have a form field
    # for time_mode. Products that does a have a form field will have to
    # choose a specific time mode.
    time_mode = models.IntegerField(
        verbose_name=_("Håndtering af tidspunkter"),
        choices=time_mode_choices,
        default=TIME_MODE_NONE,
    )

    tilbudsansvarlig = models.ForeignKey(
        User,
        verbose_name=_('Koordinator'),
        related_name='tilbudsansvarlig_for_set',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    roomresponsible = models.ManyToManyField(
        RoomResponsible,
        verbose_name=_('Lokaleansvarlige'),
        related_name='ansvarlig_for_besoeg_set',
        blank=True,
    )

    potentielle_undervisere = models.ManyToManyField(
        User,
        verbose_name=_('Potentielle undervisere'),
        related_name='potentiel_underviser_for_set',
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
    )

    potentielle_vaerter = models.ManyToManyField(
        User,
        verbose_name=_('Potentielle værter'),
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
        verbose_name=_('Forberedelsestid')
    )

    price = models.DecimalField(
        default=0,
        null=True,
        blank=True,
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Pris'),
        validators=[validators.MinValueValidator(0)]
    )

    gymnasiefag = models.ManyToManyField(
        Subject, blank=True,
        verbose_name=_('Gymnasiefag'),
        through='ProductGymnasieFag',
        related_name='gymnasie_resources'
    )

    grundskolefag = models.ManyToManyField(
        Subject, blank=True,
        verbose_name=_('Grundskolefag'),
        through='ProductGrundskoleFag',
        related_name='grundskole_resources'
    )

    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))
    topics = models.ManyToManyField(
        Topic, blank=True, verbose_name=_('Emner')
    )

    # Comment field for internal use in backend.
    comment = models.TextField(blank=True, verbose_name=_('Kommentar'))

    created_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        verbose_name=_("Oprettet af"),
        related_name='created_visits_set',
        on_delete=models.SET_NULL
    )

    # ts_vector field for fulltext search
    search_vector = SearchVectorField(null=True)

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Tekst-værdier til fritekstsøgning'),
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
        verbose_name=_("Tilbuddet kræver brug af et eller flere lokaler")
    )

    duration_choices = []
    for hour in range(0, 12, 1):
        for minute in range(0, 60, 15):
            value = "%.2d:%.2d" % (hour, minute)
            duration_choices.append((value, value),)

    duration = models.CharField(
        max_length=8,
        verbose_name=_('Varighed'),
        blank=True,
        null=True,
        choices=duration_choices
    )

    do_send_evaluation = models.BooleanField(
        verbose_name=_("Udsend evaluering"),
        default=False
    )
    is_group_visit = models.BooleanField(
        default=True,
        verbose_name=_('Gruppebesøg')
    )
    # Min/max number of visitors - only relevant for group visits.
    minimum_number_of_visitors = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Mindste antal deltagere'),
        validators=[validators.MinValueValidator(0)]
    )
    maximum_number_of_visitors = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Højeste antal deltagere'),
        validators=[validators.MinValueValidator(0)]
    )

    # Waiting lists
    do_create_waiting_list = models.BooleanField(
        default=False,
        verbose_name=_('Ventelister')
    )
    waiting_list_length = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Antal pladser'),
        validators=[validators.MinValueValidator(0)]
    )
    waiting_list_deadline_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Lukning af venteliste (dage inden besøg)'),
        validators=[validators.MinValueValidator(0)]
    )
    waiting_list_deadline_hours = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Lukning af venteliste (timer inden besøg)'),

        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(23)
        ]
    )

    do_show_countdown = models.BooleanField(
        default=False,
        verbose_name=_('Vis nedtælling')
    )

    tour_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_('Mulighed for rundvisning')
    )

    catering_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_('Mulighed for forplejning')
    )

    presentation_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_('Mulighed for oplæg om uddannelse')
    )

    custom_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_('Andet')
    )

    custom_name = models.CharField(
        blank=True,
        null=True,
        verbose_name=_('Navn for tilpasset mulighed'),
        max_length=50
    )

    NEEDED_NUMBER_NONE = 0
    NEEDED_NUMBER_MORE_THAN_TEN = -10

    needed_number_choices = [
        BLANK_OPTION,
        (NEEDED_NUMBER_NONE, _('Ingen'))
    ] + [
        (x, str(x)) for x in range(1, 11)
    ] + [
        (NEEDED_NUMBER_MORE_THAN_TEN, _('Mere end 10'))
    ]

    needed_hosts = models.IntegerField(
        default=0,
        verbose_name=_('Nødvendigt antal værter'),
        choices=needed_number_choices,
        blank=False
    )

    needed_teachers = models.IntegerField(
        default=0,
        verbose_name=_('Nødvendigt antal undervisere'),
        choices=needed_number_choices,
        blank=False
    )

    only_one_guest_per_visit = models.BooleanField(
        default=False,
        verbose_name=_('Der tillades kun 1 tilmelding pr. besøg')
    )

    booking_close_days_before = models.IntegerField(
        default=6,
        verbose_name=_('Antal dage før afholdelse, '
                       'hvor der lukkes for tilmeldinger'),
        blank=False,
        null=True,
        validators=[validators.MinValueValidator(0)]
    )

    booking_max_days_in_future = models.PositiveIntegerField(
        default=90,
        verbose_name=_(
            'Maksimalt antal dage i fremtiden hvor der kan tilmeldes'
        ),
        blank=False,
        null=True
    )

    inquire_enabled = models.BooleanField(
        default=True,
        verbose_name=_('"Spørg om tilbud" aktiveret')
    )

    education_name = models.CharField(
        blank=True,
        null=True,
        verbose_name=_('Navn på uddannelsen'),
        max_length=50
    )

    @property
    def student_evaluation(self):
        return self.surveyxactevaluation_set.filter(for_students=True).first()

    @property
    def teacher_evaluation(self):
        return self.surveyxactevaluation_set.filter(for_teachers=True).first()

    @property
    def common_evaluation(self):
        return self.surveyxactevaluation_set.filter(
            for_students=True, for_teachers=True
        ).first()

    @property
    def evaluations(self):
        return [
            evaluation for evaluation in [
                self.student_evaluation, self.teacher_evaluation
            ]
            if evaluation is not None
        ]

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
    def booking_cutoff_before(self):
        return timedelta(days=self.booking_close_days_before) \
            if self.booking_close_days_before is not None else None

    @property
    def booking_cutoff_after(self):
        return timedelta(days=self.booking_max_days_in_future) \
            if self.booking_max_days_in_future is not None else None

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
        if self.only_one_guest_per_visit:
            qs = qs.filter(
                visit__bookings__isnull=True
            )
        if self.maximum_number_of_visitors is not None:
            max = (self.maximum_number_of_visitors +
                   (self.waiting_list_length or 0))

            qs = qs.annotate(
                attendees=Coalesce(
                    Sum(
                        Case(
                            When(
                                visit__bookings__cancelled=False,
                                then='visit__bookings__booker__attendee_count'
                            )
                        )
                    ),
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

    def future_bookable_times(self, use_cutoff=False):
        filter = {'start__gte': timezone.now()}
        if use_cutoff:
            cutoff_before = self.booking_cutoff_before
            if cutoff_before is not None:
                filter['start__gte'] = timezone.now() + cutoff_before
            cutoff_after = self.booking_cutoff_after
            if cutoff_after is not None:
                filter['start__lte'] = timezone.now() + cutoff_after
        return self.bookable_times.filter(**filter)

    def future_bookable_times_with_cutoff(self):
        return self.future_bookable_times(use_cutoff=True)

    @property
    # QuerySet that finds all EventTimes that will be affected by a change
    # in resource assignment for this product.
    # Finds:
    #  - All potential resources that can be assigned to this product
    #  - All ResourcePools that make use of these resources
    #  - All EventTimes for products that has requirements that uses these
    #    ResourcePools.
    def affected_eventtimes(self):
        # If we're in the process of creating, we can't affect anything yet
        if self.pk is None:
            return EventTime.objects.none()

        if self.is_resource_controlled:
            potential_resources = Resource.objects.filter(
                resourcepool__resourcerequirement__product=self
            )
        else:
            potential_teachers = self.potentielle_undervisere.all()
            potential_hosts = self.potentielle_vaerter.all()
            potential_resources = Resource.objects.filter(
                Q(teacherresource__user__in=potential_teachers) |
                Q(hostresource__user__in=potential_hosts)
            )
        resource_pools = ResourcePool.objects.filter(
            resources__in=potential_resources
        )
        return EventTime.objects.filter(
            product__resourcerequirement__resource_pool__in=resource_pools
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
            return _("Max. %(visitors)d") % \
                {'visitors': self.maximum_number_of_visitors}
        elif self.minimum_number_of_visitors:
            return _("Min. %(visitors)d") % \
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

    # This is used from booking.signals.update_search_vectors
    def update_searchvector(self):

        extra_search_old = self.extra_search_text or ""
        extra_search_new = self.generate_extra_search_text() or ""
        search_vector = SearchVector(
            "title",
            "teaser",
            "description",
            "mouseover_description",
            "extra_search_text"
        )

        if (extra_search_old != extra_search_new) or (
            self.search_vector != search_vector
        ):
            self.extra_search_text = extra_search_new
            self.search_vector = search_vector
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
        return " ".join([str(x) for x in [
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

    def all_subjects_except_default(self):
        return [
            x for x in self.productgymnasiefag_set.exclude(
                subject__name=Subject.ALL_NAME
            )
        ] + [
            x for x in self.productgrundskolefag_set.exclude(
                subject__name=Subject.ALL_NAME
            )
        ]

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
            recipients.extend(KUEmailRecipient.multiple(
                self.potential_hosts.all(),
                KUEmailRecipient.TYPE_HOST
            ))

        if template_type.send_to_potential_teachers:
            recipients.extend(KUEmailRecipient.multiple(
                self.potential_teachers.all(),
                KUEmailRecipient.TYPE_TEACHER
            ))

        if template_type.send_to_contactperson:
            if self.inquire_user:
                recipients.append(KUEmailRecipient.create(
                    self.inquire_user,
                    KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE
                ))

        if template_type.send_to_room_responsible:
            recipients.extend(KUEmailRecipient.multiple(
                self.roomresponsible.all(),
                KUEmailRecipient.TYPE_ROOM_RESPONSIBLE
            ))

        return recipients

    def get_reply_recipients(self, template_type):
        recipients = self.organizationalunit.get_reply_recipients(
            template_type
        )
        if template_type.reply_to_product_responsible:
            recipients.extend(KUEmailRecipient.multiple(
                self.get_responsible_persons(),
                KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE
            ))
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
        for eventtime in self.future_bookable_times(use_cutoff=True):
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

    NONBOOKABLE_REASON__TYPE_NOT_BOOKABLE = 1
    NONBOOKABLE_REASON__NOT_ACTIVE = 2
    NONBOOKABLE_REASON__HAS_NO_BOOKABLE_VISITS = 3
    NONBOOKABLE_REASON__BOOKING_CUTOFF = 4
    NONBOOKABLE_REASON__NO_CALENDAR_TIME = 5
    NONBOOKABLE_REASON__BOOKING_FUTURE = 6

    nonbookable_reason_text = {
        NONBOOKABLE_REASON__TYPE_NOT_BOOKABLE:
            _('Tilbudstypen kan ikke tilmeldes.'),
        NONBOOKABLE_REASON__NOT_ACTIVE:
            _('Tilbuddet er ikke aktivt.'),
        NONBOOKABLE_REASON__HAS_NO_BOOKABLE_VISITS:
            _('Der er ingen ledige besøg.'),
        NONBOOKABLE_REASON__BOOKING_CUTOFF:
            _('Der er lukket for tilmelding %d dage før afholdelse.'),
        NONBOOKABLE_REASON__NO_CALENDAR_TIME:
            _('Der er ikke er flere ledige tider.'),
        NONBOOKABLE_REASON__BOOKING_FUTURE:
            _('Der er lukket for tilmelding %d dage efter dags dato.')
    }

    def nonbookable_text(self, bookability):
        text = Product.nonbookable_reason_text.get(bookability, None)
        if text is not None:
            if bookability == Product.NONBOOKABLE_REASON__BOOKING_CUTOFF:
                return text % self.booking_close_days_before
            if bookability == Product.NONBOOKABLE_REASON__BOOKING_FUTURE:
                return text % self.booking_max_days_in_future
            return text

    def is_bookable(self, start_time=None, end_time=None, return_reason=False):

        if not self.is_type_bookable:
            return self.NONBOOKABLE_REASON__TYPE_NOT_BOOKABLE \
                if return_reason else False

        if self.state != Product.ACTIVE:
            return self.NONBOOKABLE_REASON__NOT_ACTIVE \
                if return_reason else False

        if not self.has_bookable_visits:
            return self.NONBOOKABLE_REASON__HAS_NO_BOOKABLE_VISITS \
                if return_reason else False

        # Special case for calendar-controlled products where guest suggests
        # a date
        if self.time_mode == Product.TIME_MODE_GUEST_SUGGESTED:
            # If no time was specified, we assume there is some time where
            # the product is available:
            if start_time is None:
                return True

            # The date that the user has chosen for his visit
            start_date = start_time \
                if isinstance(start_time, date) \
                else start_time.date()

            # We don't accept bookings performed later
            # than x days before visit start
            cutoff = self.booking_cutoff_before
            if cutoff is not None:
                if timezone.now().date() > start_date - cutoff:
                    return self.NONBOOKABLE_REASON__BOOKING_CUTOFF \
                        if return_reason else False

            # We don't accept bookings for visits later
            # than x days after today
            cutoff = self.booking_cutoff_after
            if cutoff is not None:
                if start_date > timezone.now().date() + cutoff:
                    return self.NONBOOKABLE_REASON__BOOKING_FUTURE \
                        if return_reason else False

            # If start_time is a date and there is no end_date assume
            # midnight-to-midnight on the given date in the current timezone.
            if end_time is None and isinstance(start_time, date):
                # Start time is midnight
                start_time = timezone.make_aware(
                    datetime.combine(start_time, time())
                )
                end_time = start_time + timedelta(hours=24)

            # Check if we have an available time in our calendar within the
            # specified interval.
            if not self.has_available_calendar_time(start_time, end_time):
                return self.NONBOOKABLE_REASON__NO_CALENDAR_TIME \
                    if return_reason else False

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
        return self.type in Product.askable_types \
               and self.inquire_user \
               and self.inquire_enabled

    @property
    def duration_as_timedelta(self):
        if self.duration is not None and ':' in self.duration:
            (hours, minutes) = self.duration.split(":")
            return timedelta(
                hours=int(hours),
                minutes=int(minutes)
            )

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
        return '%.2d:%.2d' % (math.floor(mins / 60), mins % 60)

    def get_duration_display(self):
        mins = self.duration_in_minutes
        if mins > 0:
            hours = math.floor(mins / 60)
            mins = mins % 60
            if(hours == 1):
                return _("1 time og %(minutes)d minutter") % {'minutes': mins}
            else:
                return _("%(hours)d timer og %(minutes)d minutter") % {
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

    def __str__(self):
        return _(u"Tilbud #%(pk)s - %(title)s") % \
            {'pk': self.pk, 'title': self.title}


class Visit(AvailabilityUpdaterMixin, models.Model):

    def __init__(self, *args, **kwargs):
        super(Visit, self).__init__(*args, **kwargs)
        self.qs_cache = {}

    class Meta:
        verbose_name = _("besøg")
        verbose_name_plural = _("besøg")
        ordering = ['id']
        indexes = [
            GinIndex(fields=['search_vector'])
        ]

    objects = VisitQuerySet.as_manager()

    desired_time = models.CharField(
        null=True,
        blank=True,
        max_length=2000,
        verbose_name='Ønsket tidspunkt'
    )

    override_duration = models.CharField(
        max_length=8,
        verbose_name=_('Varighed'),
        blank=True,
        null=True,
    )

    override_locality = models.ForeignKey(
        Locality,
        verbose_name=_('Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    rooms = models.ManyToManyField(
        'Room',
        verbose_name=_('Lokaler'),
        blank=True
    )

    persons_needed_choices = (
        (None, _("Brug værdi fra tilbud")),
    ) + tuple((x, x) for x in range(1, 10))

    override_needed_hosts = models.IntegerField(
        verbose_name=_("Antal nødvendige værter"),
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
        verbose_name=_('Tilknyttede værter')
    )

    hosts_rejected = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
        related_name='rejected_hosted_visits',
        verbose_name=_('Værter, som har afslået')
    )

    override_needed_teachers = models.IntegerField(
        verbose_name=_("Antal nødvendige undervisere"),
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
        verbose_name=_('Tilknyttede undervisere')
    )

    teachers_rejected = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
        related_name='rejected_taught_visits',
        verbose_name=_('Undervisere, som har afslået')
    )

    STATUS_NOT_NEEDED = 0
    STATUS_ASSIGNED = 1
    STATUS_NOT_ASSIGNED = 2

    room_status_choices = (
        (STATUS_NOT_NEEDED, _('Tildeling af lokaler ikke påkrævet')),
        (STATUS_NOT_ASSIGNED, _('Afventer tildeling/bekræftelse')),
        (STATUS_ASSIGNED, _('Tildelt/bekræftet'))
    )

    room_status = models.IntegerField(
        choices=room_status_choices,
        default=STATUS_NOT_ASSIGNED,
        verbose_name=_('Status for tildeling af lokaler')
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
        verbose_name=_('Besøgets ressourcer')
    )

    cancelled_eventtime = models.ForeignKey(
        'EventTime',
        verbose_name=_("Tidspunkt for aflyst besøg"),
        related_name='cancelled_visits',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL
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

    BEING_PLANNED_STATUS_TEXT = 'Under planlægning'
    PLANNED_STATUS_TEXT = 'Planlagt (ressourcer tildelt)'
    PLANNED_NOBOOKING_TEXT = 'Planlagt og lukket for booking'

    status_to_class_map = {
        WORKFLOW_STATUS_BEING_PLANNED: 'warning',
        WORKFLOW_STATUS_REJECTED: 'danger',
        WORKFLOW_STATUS_PLANNED: 'success',
        WORKFLOW_STATUS_CONFIRMED: 'success',
        WORKFLOW_STATUS_REMINDED: 'success',
        WORKFLOW_STATUS_EXECUTED: 'success',
        WORKFLOW_STATUS_EVALUATED: 'success',
        WORKFLOW_STATUS_CANCELLED: 'danger',
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
        (WORKFLOW_STATUS_REJECTED, _('Afvist af undervisere eller vært')),
        (WORKFLOW_STATUS_PLANNED, _(PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_PLANNED_NO_BOOKING, _(PLANNED_NOBOOKING_TEXT)),
        (WORKFLOW_STATUS_CONFIRMED, _('Bekræftet af gæst')),
        (WORKFLOW_STATUS_REMINDED, _('Påmindelse afsendt')),
        (WORKFLOW_STATUS_EXECUTED, _('Afviklet')),
        (WORKFLOW_STATUS_EVALUATED, _('Evalueret')),
        (WORKFLOW_STATUS_CANCELLED, _('Aflyst')),
        (WORKFLOW_STATUS_NOSHOW, _('Udeblevet')),
        (WORKFLOW_STATUS_AUTOASSIGN_FAILED, _('Automatisk tildeling fejlet')),
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
        verbose_name=_('Behov for opmærksomhed siden')
    )

    comments = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Interne kommentarer')
    )

    # ts_vector field for fulltext search
    search_vector = SearchVectorField(null=True)

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Tekst-værdier til fritekstsøgning'),
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
        WORKFLOW_STATUS_CANCELLED: [],
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

        # Visits of bookable products, that have no uncancelled bookings
        if not self.is_multi_sub \
                and len([
                    x for x in self.products
                    if x.type in Product.bookable_types
                ]) \
                and self.bookings.filter(cancelled=False).count() == 0:
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

    @property
    def is_cancelled(self):
        return self.workflow_status == Visit.WORKFLOW_STATUS_CANCELLED

    @property
    def is_rejected(self):
        return self.workflow_status == Visit.WORKFLOW_STATUS_REJECTED

    def cancel_visit(self):
        self.workflow_status = Visit.WORKFLOW_STATUS_CANCELLED

        if(hasattr(self, 'eventtime')):
            # Break relation to the eventtime
            eventtime = self.eventtime
            self.eventtime.visit = None
            eventtime.save()
            # Register as a cancelled visit for the given time
            self.cancelled_eventtime = eventtime
            self.save()

    @classmethod
    def workflow_status_name(cls, workflow_status):
        for value, label in cls.workflow_status_choices:
            if value == workflow_status:
                return label

    def workflow_status_display(self):
        return Visit.workflow_status_name(self.workflow_status)

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
                product = self.products[0]
                for evaluation in product.surveyxactevaluation_set.all():
                    evaluation.send_first_notification(self)

    @property
    # QuerySet that finds EventTimes that will be affected by resource changes
    # on this visit.
    def affected_eventtimes(self):
        if (
            hasattr(self, 'eventtime') and
            self.eventtime.start and
            self.eventtime.end
        ):
            return EventTime.objects.filter(
                product__in=self.products,
                start__lt=self.eventtime.end,
                end__gt=self.eventtime.start
            )
        else:
            return EventTime.objects.none()

    @property
    # Calendars that needs to be updated if assigned teachers or hosts are
    # changed.
    def affected_calendars(self):
        return Calendar.objects.filter(
            Q(resource__teacherresource__user__in=self.teachers.all()) |
            Q(resource__hostresource__user__in=self.hosts.all()) |
            Q(resource__roomresource__room__in=self.rooms.all()) |
            Q(resource__in=self.resources.all())
        )

    def update_availability(self):
        for x in self.affected_eventtimes:
            x.update_availability()

    def resources_updated(self):

        orig_status = self.workflow_status

        # If current status is rejected by personel, check if personel is
        # still needed and if not change status accordingly
        if (
            self.workflow_status == self.WORKFLOW_STATUS_REJECTED and
            not self.needs_hosts and
            not self.needs_teachers
        ):
            if self.planned_status_is_blocked(True):
                self.workflow_status = self.WORKFLOW_STATUS_BEING_PLANNED
            elif not self.is_multiproductvisit:
                self.workflow_status = self.WORKFLOW_STATUS_PLANNED

        elif self.workflow_status in [
            self.WORKFLOW_STATUS_BEING_PLANNED,
            self.WORKFLOW_STATUS_AUTOASSIGN_FAILED
        ] and not self.is_multiproductvisit \
                and not self.planned_status_is_blocked(True):
            self.workflow_status = self.WORKFLOW_STATUS_PLANNED

        elif self.workflow_status in [
                    self.WORKFLOW_STATUS_PLANNED,
                    self.WORKFLOW_STATUS_PLANNED_NO_BOOKING
                ] and self.planned_status_is_blocked(True):
            self.workflow_status = self.WORKFLOW_STATUS_BEING_PLANNED

        if orig_status != self.workflow_status:
            self.save()
            # Send out planned notification if we switched to planned
            if self.workflow_status == self.WORKFLOW_STATUS_PLANNED:
                if not self.is_multi_sub:
                    self.autosend(
                        EmailTemplateType.notify_all__booking_complete
                    )
        if self.is_multi_sub:
            self.multi_master.resources_updated()

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
            self.WORKFLOW_STATUS_PLANNED,
            self.WORKFLOW_STATUS_PLANNED_NO_BOOKING,
            self.WORKFLOW_STATUS_CONFIRMED,
            self.WORKFLOW_STATUS_REMINDED
        ]:
            self.workflow_status = self.WORKFLOW_STATUS_EXECUTED
            self.save()

    @property
    def display_title(self):
        try:
            if self.product.type == Product.STUDENT_FOR_A_DAY:
                return self.bookings.first().booker.get_full_name()
            return self.bookings.first().booker.school.name
        except:
            return self.product.title if self.product \
                else _("Besøg #%d") % self.id

    @property
    def display_value(self):
        if not hasattr(self, 'eventtime') or not self.eventtime.start:
            return _('ikke-fastlagt tidspunkt')
        return self.eventtime.interval_display

    @property
    def id_display(self):
        return _('Besøg #%d') % self.id

    # Format date for basic display
    @property
    def date_display(self):
        if hasattr(self, 'eventtime') and self.eventtime.start:
            return formats.date_format(
                self.eventtime.naive_start,
                "DATETIME_FORMAT"
            )
        else:
            return _('ikke-fastlagt tidspunkt')

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
            return _('på ikke-fastlagt tidspunkt')

    @property
    def interval_display(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.interval_display
        elif self.cancelled_eventtime:
            return self.cancelled_eventtime.interval_display
        else:
            return ""

    @property
    def start_datetime(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.start
        elif self.cancelled_eventtime:
            return self.cancelled_eventtime.start
        else:
            return None

    @property
    def end_datetime(self):
        if hasattr(self, 'eventtime'):
            return self.eventtime.end
        elif self.cancelled_eventtime:
            return self.cancelled_eventtime.end
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
            resources_count = self.visitresource.filter(
                resource_requirement=requirement
            ).count()
            if resources_count < requirement.required_amount:
                missing += (requirement.required_amount - resources_count)
        return missing

    @property
    def total_required_teachers(self):
        if self.override_needed_teachers is not None:
            return self.override_needed_teachers
        if self.product is not None:
            return self.product.total_required_teachers
        return 0

    @property
    def needed_teachers(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_teachers
        elif self.product is not None and self.product.is_resource_controlled:
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
        if self.product is not None and self.product.is_resource_controlled:
            return User.objects.filter(
                teacherresource__visitresource__visit=self
            )
        else:
            return self.teachers.all()

    @property
    def total_required_hosts(self):
        if self.override_needed_hosts is not None:
            return self.override_needed_hosts
        if self.product is not None:
            return self.product.total_required_hosts
        return 0

    @property
    def needed_hosts(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_hosts
        elif self.product is not None and self.product.is_resource_controlled:
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
        if self.product is not None and self.product.is_resource_controlled:
            return User.objects.filter(
                hostresource__visitresource__visit=self
            )
        else:
            return self.hosts.all()

    @property
    def responsible_persons(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.responsible_persons
        if self.product is not None:
            return self.product.get_responsible_persons()
        return []

    @property
    def total_required_rooms(self):
        if self.override_needed_hosts is not None:
            return self.override_needed_hosts
        return self.product.total_required_rooms

    @property
    def needed_rooms(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_rooms
        elif self.product is not None and self.product.is_resource_controlled:
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
        if self.product is not None and self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_ITEM)
        return 0

    @property
    def needed_vehicles(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.needed_vehicles
        if self.product is not None and self.product.is_resource_controlled:
            return self.resources_required(ResourceType.RESOURCE_TYPE_VEHICLE)
        return 0

    @property
    def is_booked(self):
        """Has this Visit instance been booked yet?"""
        return len(self.bookings.all()) > 0

    @property
    def only_one_guest_per_visit(self):
        for product in self.products:
            if product.only_one_guest_per_visit:
                return True
        return False

    @property
    def is_bookable(self):
        # Can this visit be booked?
        if self.workflow_status not in self.BOOKABLE_STATES:
            return False
        if self.expired:
            return False
        if self.available_seats == 0:
            return False
        if self.bookings.count() > 0 and self.only_one_guest_per_visit:
            return False
        return True

    def is_being_planned(self):
        return self.workflow_status == self.WORKFLOW_STATUS_BEING_PLANNED

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
        if self.bookings.count() > 0 and self.only_one_guest_per_visit:
            return False
        return True

    def get_bookings(self, include_waiting=False, include_non_waiting=True,
                     include_cancelled=False, include_non_cancelled=True):

        # The code is easier to read and understand with these inversions
        exclude_cancelled = not include_cancelled
        exclude_non_cancelled = not include_non_cancelled
        exclude_waiting = not include_waiting
        exclude_non_waiting = not include_non_waiting

        if exclude_waiting and exclude_non_waiting:
            return self.bookings.none()

        if exclude_cancelled and exclude_non_cancelled:
            return self.bookings.none()

        qs = self.bookings.all().prefetch_related("visit")

        if exclude_waiting:  # Only accept non-waiting
            qs = qs.filter(waitinglist_spot=0)
        elif exclude_non_waiting:  # Only accept waiting
            qs = qs.filter(waitinglist_spot__gt=0)
        # else:       Accept both waiting and non-waiting
        #     pass    no change to qs

        if exclude_cancelled:  # Only accept non-cancelled
            qs = qs.filter(cancelled=False)
        elif exclude_non_cancelled:  # Only accept cancelled
            qs = qs.filter(cancelled=True)
        # else:       Accept cancelled and non-cancelled
        #     pass    no change to qs

        if include_waiting:
            qs = qs.order_by("waitinglist_spot")

        return qs

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
    def multi_top(self):
        if self.is_multi_sub:
            return self.multi_master
        return self

    @property
    def booking_list(self):
        return self.get_bookings(False, True)

    @property
    def waiting_list(self):
        return self.get_bookings(True, False)

    @property
    def cancelled_list(self):
        return self.get_bookings(True, True, True, False)

    def get_attendee_count(
            self, include_waiting=False, include_non_waiting=True,
            include_cancelled=False, include_non_cancelled=True
    ):
        return self.get_bookings(
            include_waiting, include_non_waiting,
            include_cancelled, include_non_cancelled
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
    def nr_cancelled_attendees(self):
        return self.get_attendee_count(True, True, True, False)

    @property
    def available_seats(self):
        limit = self.product.maximum_number_of_visitors \
            if self.product is not None else None
        if limit is None:
            return AVAILABLE_SEATS_NO_LIMIT
        return max(limit - self.nr_attendees, 0)

    def get_workflow_status_class(self):
        return self.status_to_class_map.get(self.workflow_status, 'default')

    def __str__(self):
        if self.is_multiproductvisit:
            return str(self.multiproductvisit)
        if hasattr(self, 'eventtime'):
            return _('Besøg %(id)s - %(title)s - %(time)s') % {
                'id': self.pk,
                'title': self.real.display_title,
                'time': self.eventtime.interval_display
            }
        elif self.cancelled_eventtime:
            return _('Besøg %(id)s - %(title)s - %(time)s (aflyst)') % {
                'id': self.pk,
                'title': self.real.display_title,
                'time': self.cancelled_eventtime.interval_display
            }
        else:
            return _('Besøg %s - uden tidspunkt') % self.pk

    @property
    def product(self):
        try:
            return self.eventtime.product
        except:
            pass
        try:
            return self.cancelled_eventtime.product
        except:
            pass
        return None

    @property
    def unit(self):
        if self.is_multiproductvisit:
            return self.multiproductvisit.unit
        try:
            return self.product.organizationalunit
        except:
            pass

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

    # This is used from booking.signals.update_search_vectors
    def update_searchvector(self):
        old_value = self.extra_search_text or ""
        new_value = self.as_searchtext() or ""

        if (old_value != new_value) or (
            self.search_vector is None
        ):
            self.extra_search_text = new_value
            self.search_vector = SearchVector("extra_search_text")
            self.save()
            return True
        else:
            return False

    def save(self, *args, **kwargs):
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
            recipients.extend(KUEmailRecipient.multiple(
                self.assigned_hosts, KUEmailRecipient.TYPE_HOST
            ))
        if template_type.send_to_visit_teachers:
            recipients.extend(KUEmailRecipient.multiple(
                self.assigned_teachers, KUEmailRecipient.TYPE_TEACHER
            ))
        if template_type.avoid_already_assigned:
            new_recipients = []
            for recipient in recipients:
                user = recipient.user
                if user is None or (
                        user not in self.hosts.all() and
                        user not in self.teachers.all()
                ):
                    new_recipients.append(recipient)
            recipients = new_recipients
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
        if follow_inherit and self.product is not None and \
                self.autosend_inherits(template_type):
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
                 only_these_recipients=False,
                 only_these_types=KUEmailRecipient.all_types
                 ):
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
                recipients = []
            if not only_these_recipients:
                recipients.extend(self.get_recipients(template_type))
            recipients = KUEmailRecipient.filter_list(
                recipients,
                only_these_types
            )

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
                # Mails to bookers on MPVs are sent from the parent visit
                if not self.is_multi_sub:
                    bookings = self.bookings.all()
                    for booking in bookings:
                        if not booking.is_waiting or \
                                template_type.send_to_booker_on_waitinglist:
                            KUEmailMessage.send_email(
                                template_type,
                                {
                                    'visit': self,
                                    'besoeg': self,
                                    'product': product,
                                    'booking': booking,
                                    'booker': booking.booker
                                },
                                KUEmailRecipient.create(booking.booker),
                                self,
                                unit,
                                original_from_email=reply_recipients
                            )

    def get_autosend_display(self):
        autosends = self.get_autosends(True, False, False)
        return [autosend.get_name() for autosend in autosends]

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
        for requirement in self.product.resourcerequirement_set.filter(
            resource_pool__isnull=True
        ):
            details.append({
                'unknown': True,
                'id': requirement.id
            })
        return details

    is_multiproductvisit = models.BooleanField(
        default=False
    )

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
    def products_unique_address(self):
        addresses = {
            product.locality.id: product
            for product in self.products
            if product is not None
        }
        return addresses.values()

    @property
    def unit_qs(self):
        return OrganizationalUnit.objects.filter(
            product__eventtime__visit=self
        )

    @property
    def calendar_event_link(self):
        return reverse('visit-view', args=[self.pk])

    @property
    def calender_event_title(self):
        output = [_('Besøg #%s') % self.pk]
        if self.product:
            output.append(" - %s" % self.product.title)
        teachers = ', '.join([
            teacher.get_full_name()
            for teacher in self.teachers.all()
        ]) if self.teachers.exists() else _("<ingen>")
        output.append(_("\nUndervisere: %s") % teachers)
        hosts = ', '.join([
            host.get_full_name()
            for host in self.hosts.all()
        ]) if self.hosts.exists() else _("<ingen>")
        output.append(_("\nVærter: %s") % hosts)
        return ''.join(output)

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
                if self.product is not None else False
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
                if self.product is not None else False
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
        if self.product is not None and self.product.time_mode == \
                Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN:
            for requirement in self.product.resourcerequirement_set.all():
                if requirement.being_deleted:
                    # Deletion of VisitResources can start this process, but
                    # we must ignore requirements that are scheduled for
                    # deletion.
                    continue
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

    @property
    def student_evaluation_guests(self):
        return SurveyXactEvaluationGuest.objects.filter(
            guest__booking__visit=self,
            evaluation__for_students=True
        )

    @property
    def teacher_evaluation_guests(self):
        return SurveyXactEvaluationGuest.objects.filter(
            guest__booking__visit=self,
            evaluation__for_students=False
        )

    def evaluations(self, filter=None, ordered=False):
        evaluation_ids = set()
        for guest in SurveyXactEvaluationGuest.objects.filter(
            guest__booking__visit=self,
        ):
            evaluation_ids.add(guest.evaluation.id)
        evaluations = SurveyXactEvaluation.objects.filter(
            id__in=evaluation_ids
        )
        if filter is not None:
            evaluations = evaluations.filter(**filter)
        evaluations = list(evaluations)
        if ordered:
            evaluations.sort(key=lambda e: self.products.index(e.product))
        return evaluations

    @property
    def student_evaluation(self):
        evaluations = self.evaluations({'for_students': True}, True)
        return evaluations[0] if len(evaluations) > 0 else None

    @property
    def teacher_evaluation(self):
        evaluations = self.evaluations({'for_teachers': True}, True)
        return evaluations[0] if len(evaluations) > 0 else None

    @property
    def common_evaluation(self):
        return self.evaluations.filter(
            for_students=True, for_teachers=True
        ).first()

    # Used by evaluation statistics page
    def evaluation_guestset(self):
        statuslist = [
            key for (key, label) in
            SurveyXactEvaluationGuest.status_choices
        ]
        output = []
        if (hasattr(self.product, "student_evaluation") and
                self.product.student_evaluation is not None):
            student_status = {status: 0 for status in statuslist}
            for student in self.student_evaluation_guests.all():
                student_status[student.status] += 1
            output.append((
                _('Elever'),
                self.product.student_evaluation,
                [student_status[key] for key in statuslist]
            ))
        if (hasattr(self.product, "teacher_evaluation") and
                self.product.teacher_evaluation is not None):
            teacher_status = {status: 0 for status in statuslist}
            for teacher in self.teacher_evaluation_guests.all():
                teacher_status[teacher.status] += 1
            output.append((
                _('Lærere'),
                self.product.teacher_evaluation,
                [teacher_status[key] for key in statuslist]
            ))
        return output

    @staticmethod
    def evaluation_guestset_labels():
        return [
            label for (key, label) in
            SurveyXactEvaluationGuest.status_choices
        ]


Visit.add_override_property('duration')
Visit.add_override_property('locality')


class MultiProductVisit(Visit):
    date = models.DateField(
        null=True,
        blank=False,
        verbose_name=_('Dato')
    )
    required_visits = models.PositiveIntegerField(
        default=2,
        verbose_name=_('Antal ønskede besøg')
    )
    responsible = models.ForeignKey(
        User,
        blank=True,
        null=True,
        verbose_name=_('Besøgsansvarlig'),
        on_delete=models.SET_NULL
    )

    def __init__(self, *args, **kwargs):
        super(MultiProductVisit, self).__init__(*args, **kwargs)
        self.is_multiproductvisit = True
        self.qs_cache = {}

    @property
    def date_ref(self):
        return timezone.localtime(self.eventtime.start).date() \
            if self.eventtime.start is not None else None

    def create_eventtime(self, date=None, endtime=None):
        if date is None:
            date = self.date
        if date is not None:
            if not hasattr(self, 'eventtime') or self.eventtime is None:
                time = datetime(
                    date.year, date.month, date.day,
                    8, 0, 0, tzinfo=timezone.get_current_timezone()
                )
                EventTime(visit=self, start=time, end=endtime).save()

    @staticmethod
    def migrate_to_eventtime():
        for mpv in MultiProductVisit.objects.all():
            mpv.create_eventtime()

    @property
    def subvisits_unordered(self):
        # Faster than ordered, and often we don't need the ordering anyway
        if 'subvisits_unordered' not in self.qs_cache:
            self.qs_cache['subvisits_unordered'] = VisitQuerySet.prefetch(
                Visit.objects.filter(
                    is_multi_sub=True,
                    multi_master=self
                )
            )
            list(self.qs_cache['subvisits_unordered'])
        return self.qs_cache['subvisits_unordered']

    @property
    def subvisits_unordered_noncancelled(self):
        if 'subvisits_unordered_noncancelled' not in self.qs_cache:
            self.qs_cache['subvisits_unordered_noncancelled'] = \
                VisitQuerySet.prefetch(self.subvisits_unordered.active_qs())
            list(self.qs_cache['subvisits_unordered_noncancelled'])
        return self.qs_cache['subvisits_unordered_noncancelled']

    @property
    def subvisits(self):
        if 'subvisits_ordered' not in self.qs_cache:
            self.qs_cache['subvisits_ordered'] = VisitQuerySet.prefetch(
                self.subvisits_unordered.order_by('multi_priority')
            )
        return self.qs_cache['subvisits_ordered']

    @property
    def subvisits_by_time(self):
        return self.subvisits_unordered.order_by('eventtime__start')

    @property
    def products(self):
        return [visit.product for visit in self.subvisits if visit.product]

    @property
    def products_ordered(self):
        return self.products

    def potential_responsible(self):
        return User.objects.filter(
            userprofile__organizationalunit__in=self.unit_qs
        )

    @property
    def unit_qs(self):
        return OrganizationalUnit.objects.filter(
            product__eventtime__visit__in=self.subvisits_unordered
        )

    @property
    def unit(self):
        try:
            return self.products[0].organizationalunit
        except:
            pass

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
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def assigned_teachers(self):
        return User.objects.filter(
            id__in=flatten([
                [user.id for user in subvisit.assigned_teachers]
                for subvisit in self.subvisits_unordered_noncancelled
            ])
        )

    @property
    def needed_teachers(self):
        return sum(
            subvisit.needed_teachers
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def needs_teachers(self):
        for subvisit in self.subvisits_unordered_noncancelled:
            if subvisit.needs_teachers:
                return True
        return False

    @property
    def total_required_hosts(self):
        return sum(
            subvisit.total_required_hosts
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def assigned_hosts(self):
        return User.objects.filter(
            id__in=flatten([
                [user.id for user in subvisit.assigned_hosts]
                for subvisit in self.subvisits_unordered_noncancelled
            ])
        )

    @property
    def needed_hosts(self):
        return sum(
            subvisit.needed_hosts
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def needs_hosts(self):
        for subvisit in self.subvisits_unordered_noncancelled:
            if subvisit.needs_hosts:
                return True
        return False

    @property
    def total_required_rooms(self):
        return sum(
            subvisit.total_required_rooms
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def needed_rooms(self):
        return sum(
            subvisit.needed_rooms
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def needs_room(self):
        for subvisit in self.subvisits_unordered_noncancelled:
            if subvisit.needs_room:
                return True
        return False

    @property
    def needed_items(self):
        return sum(
            subvisit.needed_items
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def needed_vehicles(self):
        return sum(
            subvisit.needed_vehicles
            for subvisit in self.subvisits_unordered_noncancelled
        )

    @property
    def responsible_persons(self):
        responsible = set()
        for visit in self.subvisits_unordered_noncancelled:
            if visit.product is not None:
                responsible.update(visit.product.get_responsible_persons())
        return responsible

    @property
    def available_seats(self):
        return 0

    @property
    def display_title(self):
        # return _(u'prioriteret liste af %d tilbud') % len(self.products)
        try:
            return self.bookings.first().booker.school.name
        except:
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
        return formats.date_format(self.date_ref, "DATE_FORMAT") \
            if self.date_ref is not None else _('Intet tidspunkt')

    @property
    def date_display_context(self):
        return _("d. %s") % formats.date_format(self.date_ref, "DATE_FORMAT") \
            if self.date_ref is not None else _('Intet tidspunkt')

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
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED,
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE
        ]:
            return True
        else:
            return super(MultiProductVisit, self).autosend_enabled(
                template_type
            )

    def autosend_enabled_booker_only(self, template_type):
        if template_type.key in [
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE
        ]:
            return True

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
                 only_these_recipients=False,
                 only_these_types=KUEmailRecipient.all_types
                 ):
        unit = None  # TODO: What should the unit be?
        params = {'visit': self, 'products': self.products}

        # If template specifies to send to teachers or hosts,
        # send to those recipients by the subvisits
        if template_type.send_to_visit_teachers \
                or template_type.send_to_visit_hosts:
            filter = set([])
            if template_type.send_to_visit_teachers:
                filter.add(KUEmailRecipient.TYPE_TEACHER)
            if template_type.send_to_visit_hosts:
                filter.add(KUEmailRecipient.TYPE_HOST)
            filter = filter.intersection(only_these_types)
            for subvisit in self.subvisits:
                subvisit.autosend(
                    template_type,
                    recipients,
                    only_these_recipients,
                    filter
                )
            only_these_types -= set(filter)

        if self.autosend_enabled(template_type):

            # Gather recipients
            if recipients is None:
                recipients = []
            if not only_these_recipients:
                recipients.extend(self.get_recipients(template_type))
            recipients = KUEmailRecipient.filter_list(
                recipients,
                only_these_types
            )

            KUEmailMessage.send_email(
                template_type,
                params,
                list(recipients),
                self,
                unit,
                original_from_email=self.get_reply_recipients(template_type)
            )

        if not only_these_recipients and template_type.send_to_booker and (
                self.autosend_enabled(template_type) or
                self.autosend_enabled_booker_only(template_type)
        ):
            for booking in self.bookings.all():
                if (
                        not booking.is_waiting or
                        template_type.send_to_booker_on_waitinglist
                ) and (
                        not booking.cancelled
                ):
                    KUEmailMessage.send_email(
                        template_type,
                        merge_dicts(params, {
                            'booking': booking,
                            'booker': booking.booker
                        }),
                        KUEmailRecipient.create(booking.booker),
                        self,
                        unit,
                        original_from_email=self.get_reply_recipients(
                            template_type
                        )
                    )

    def autoassign_resources(self):
        for visit in self.subvisits_unordered:
            visit.autoassign_resources()

    def __str__(self):
        if hasattr(self, 'eventtime'):
            return _('Besøg %(id)s - Prioriteret liste af '
                     '%(count)d underbesøg - %(time)s') % {
                'id': self.pk,
                'count': self.subvisits_unordered.count(),
                'time': self.eventtime.interval_display
            }
        else:
            return _('Besøg %s - uden tidspunkt') % self.pk


class MultiProductVisitTempProduct(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='prod',
        on_delete=models.CASCADE
    )
    multiproductvisittemp = models.ForeignKey(
        'MultiProductVisitTemp',
        on_delete=models.CASCADE
    )
    index = models.IntegerField()


class MultiProductVisitTemp(models.Model):
    date = models.DateField(
        null=False,
        blank=False,
        verbose_name=_('Dato')
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
        verbose_name='Bemærkninger'
    )
    baseproduct = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        related_name='foobar',
        on_delete=models.CASCADE
    )
    required_visits = models.PositiveIntegerField(
        default=2,
        verbose_name=_('Antal ønskede besøg')
    )

    def create_mpv(self):
        mpv = MultiProductVisit(
            required_visits=self.required_visits
        )
        mpv.needs_attention_since = timezone.now()
        mpv.save()
        mpv.eventtime = EventTime(
            bookable=False,
            has_specific_time=False,
            visit=mpv
        )
        mpv.eventtime.save()
        mpv.ensure_statistics()
        for index, product in enumerate(self.products_ordered):
            eventtime = EventTime(
                product=product,
                bookable=False,
                has_specific_time=False
            )
            eventtime.save()
            eventtime.make_visit(
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


class VisitComment(models.Model):

    class Meta:
        ordering = ["-time"]

    visit = models.ForeignKey(
        Visit,
        verbose_name=_('Besøg'),
        null=False,
        blank=False,
        on_delete=models.CASCADE
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
        verbose_name=_('Kommentartekst')
    )
    time = models.DateTimeField(
        verbose_name=_('Tidsstempel'),
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
        verbose_name=_('Skabelon'),
        blank=False,
        null=False
    )
    days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Dage'),
    )
    enabled = models.BooleanField(
        verbose_name=_('Aktiv'),
        default=True
    )

    template_type = models.ForeignKey(
        EmailTemplateType,
        null=True,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        self.template_key = self.template_type.key
        super(Autosend, self).save(*args, **kwargs)

    def get_name(self):
        return self.template_type.name

    def __str__(self):
        return "[%d] %s (%s)" % (
            self.id,
            self.get_name(),
            "enabled" if self.enabled else "disabled"
        )

    @property
    def as_initial(self):
        result = {}
        for x in ('template_type', 'enabled', 'days'):
            result[x] = getattr(self, x)
        return result

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
        verbose_name=_('Besøg'),
        blank=False,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "%s on %s" % (
            super(ProductAutosend, self).__str__(),
            self.product.__str__()
        )


class VisitAutosend(Autosend):
    visit = models.ForeignKey(
        Visit,
        verbose_name=_('BesøgForekomst'),
        blank=False,
        on_delete=models.CASCADE
    )
    inherit = models.BooleanField(
        verbose_name=_('Genbrug indstilling fra tilbud')
    )

    def get_inherited(self):
        if self.inherit:
            return self.visit.get_autosend(self.template_type)

    def __str__(self):
        return "%s on %s" % (
            super(VisitAutosend, self).__str__(),
            self.visit.__str__()
        )


class Room(models.Model):

    class Meta:
        verbose_name = _("lokale")
        verbose_name_plural = _("lokaler")

    locality = models.ForeignKey(
        Locality,
        verbose_name=_('Lokalitet'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    name = models.CharField(
        max_length=64, verbose_name=_('Navn på lokale'), blank=False
    )

    def __str__(self):
        if self.locality:
            return '%s - %s' % (self.name, str(self.locality))
        else:
            return '%s - %s' % (self.name, _('Ingen lokalitet'))

    @property
    def name_with_locality(self):
        if self.locality:
            return '%s, %s' % (
                self.name,
                self.locality.name_and_address
            )
        else:
            return '%s, %s' % (
                self.name,
                _('<uden lokalitet>')
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

    @property
    def resource(self):
        return self.roomresource_set.first()


class Region(models.Model):

    class Meta:
        verbose_name = _('region')
        verbose_name_plural = _('regioner')

    name = models.CharField(
        max_length=16,
        verbose_name=_('Navn')
    )

    # Not pretty, but it gets the job done for now
    name_en = models.CharField(
        max_length=16,
        null=True,
        verbose_name=_('Engelsk navn')
    )

    def __str__(self):
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
        verbose_name = _('kommune')
        verbose_name_plural = _('kommuner')

    name = models.CharField(
        max_length=30,
        verbose_name=_('Navn'),
        unique=True
    )

    region = models.ForeignKey(
        Region,
        verbose_name=_('Region'),
        on_delete=models.CASCADE
    )

    def __str__(self):
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
        verbose_name = _('postnummer')
        verbose_name_plural = _('postnumre')

    number = models.IntegerField(
        primary_key=True
    )
    city = models.CharField(
        max_length=48
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE
    )

    def __str__(self):
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
                    print(
                            "Unknown region '%s'. May be a typo, please fix "
                            "in booking/data/postcodes.py" % region_name
                    )
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
        verbose_name = _('uddannelsesinstitution')
        verbose_name_plural = _('uddannelsesinstitutioner')
        ordering = ["name", "postcode"]

    objects = SchoolQuerySet.as_manager()

    name = models.CharField(
        max_length=128,
    )
    postcode = models.ForeignKey(
        PostCode,
        null=True,
        on_delete=models.SET_NULL
    )
    municipality = models.ForeignKey(
        Municipality,
        null=True,
        on_delete=models.SET_NULL
    )
    address = models.CharField(
        max_length=128,
        verbose_name=_('Adresse'),
        null=True
    )
    cvr = models.IntegerField(
        verbose_name=_('CVR-nummer'),
        null=True
    )
    ean = models.BigIntegerField(
        verbose_name=_('EAN-nummer'),
        null=True
    )

    ELEMENTARY_SCHOOL = Subject.SUBJECT_TYPE_GRUNDSKOLE
    GYMNASIE = Subject.SUBJECT_TYPE_GYMNASIE
    type_choices = (
        (ELEMENTARY_SCHOOL, 'Folkeskole'),
        (GYMNASIE, 'Gymnasie')
    )

    type = models.IntegerField(
        choices=type_choices,
        default=1,
        verbose_name=_('Uddannelsestype')
    )

    def __str__(self):
        if self.postcode is not None:
            return "%s (%d %s)" % \
                   (self.name, self.postcode.number, self.postcode.city)
        return self.name

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
                    print(
                            "Warning: Postcode %d not found in database. "
                            "Not adding school %s" % (postcode, name)
                    )

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
                print(
                        "Municipality '%s' does not exist" %
                        item.get('municipality')
                )
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
                    print(
                            "Warning: Postcode %d not found in database. "
                            "Not adding school %s" % (postcode, name)
                    )

    @staticmethod
    def dedup():
        remove = {}
        for school in School.objects.filter(postcode__isnull=False):
            if school.id not in remove:
                others = School.objects.filter(
                    name=school.name,
                    postcode=school.postcode
                ).exclude(id=school.id).order_by('id')
                for other in others:
                    for booker in other.guest_set.all():
                        print(
                                "wire booker to %d instead of %d" %
                                (school.id, other.id)
                        )
                        booker.school = school
                        booker.save()
                    remove[other.id] = True
                    print("remove school %d (%s)" % (other.id, other.name))
        r = School.objects.filter(id__in=remove.keys())
        r.delete()


class Guest(models.Model):

    class Meta:
        verbose_name = _('besøgende')
        verbose_name_plural = _('besøgende')

    # A person booking a visit
    firstname = models.CharField(
        max_length=64,
        blank=False,
        verbose_name='Fornavn'
    )
    lastname = models.CharField(
        max_length=64,
        blank=False,
        verbose_name='Efternavn'
    )
    email = models.EmailField(
        max_length=64,
        blank=False,
        verbose_name='Email'
    )
    phone = models.CharField(
        max_length=14,
        blank=False,
        verbose_name='Telefon'
    )

    stx = 0
    hf = 1
    htx = 2
    eux = 3
    valgfag = 4
    hhx = 5
    line_choices = (
        (stx, _('stx')),
        (hf, _('hf')),
        (htx, _('htx')),
        (eux, _('eux')),
        (hhx, _('hhx')),
    )
    line = models.IntegerField(
        choices=line_choices,
        blank=True,
        null=True,
        verbose_name='Linje',
    )
    sx_line_conversion = {
        stx: 21,
        hf: 22,
        htx: 23,
        eux: 24,
        hhx: 25
    }

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
        (f0, _('0. klasse')),
        (f1, _('1. klasse')),
        (f2, _('2. klasse')),
        (f3, _('3. klasse')),
        (f4, _('4. klasse')),
        (f5, _('5. klasse')),
        (f6, _('6. klasse')),
        (f7, _('7. klasse')),
        (f8, _('8. klasse')),
        (f9, _('9. klasse')),
        (f10, _('10. klasse')),
        (g1, _('1.g')),
        (g2, _('2.g')),
        (g3, _('3.g')),
        (student, _('Afsluttet gymnasieuddannelse')),
        (other, _('Andet')),
    )
    level = models.IntegerField(
        choices=level_choices,
        blank=False,
        verbose_name='Niveau'
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

    anonymized = "[anonymiseret]"

    @staticmethod
    def grundskole_level_map():
        return {
            thisref: GrundskoleLevel.objects.get(level=grundskoleref).id
            for thisref, grundskoleref
            in Guest.grundskole_level_conversion.items()
        }

    school = models.ForeignKey(
        School,
        null=True,
        verbose_name='Skole',
        on_delete=models.SET_NULL
    )

    attendee_count = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Antal deltagere',
        validators=[validators.MinValueValidator(int(1))]
    )

    teacher_count = models.IntegerField(
        blank=True,
        null=True,
        default=None,
        verbose_name='Heraf lærere'
    )

    consent = models.BooleanField(
        verbose_name=_('Samtykke'),
        default=False,
    )

    @property
    def student_count(self):
        try:
            return self.attendee_count - (self.teacher_count or 0)
        except:
            return 0

    def evaluationguest_student(self):
        try:
            return self.surveyxactevaluationguest_set.filter(
                evaluation__for_students=True, evaluation__for_teachers=False
            ).first()
        except:
            return None

    def evaluationguest_teacher(self):
        try:
            return self.surveyxactevaluationguest_set.filter(
                evaluation__for_students=False, evaluation__for_teachers=True
            ).first()
        except:
            return None

    def as_searchtext(self):
        return " ".join([str(x) for x in [
            self.firstname,
            self.lastname,
            self.email,
            self.phone,
            self.get_level_display(),
            self.school
        ] if x])

    def __str__(self):
        if self.email is not None and self.email != "":
            return "%s %s <%s>" % (self.firstname, self.lastname, self.email)
        return "%s %s" % (self.firstname, self.lastname)

    def get_email(self):
        return self.email

    def get_name(self):
        if self.firstname == Guest.anonymized:
            return Guest.anonymized
        return "%s %s" % (self.firstname, self.lastname)

    def get_full_name(self):
        return self.get_name()

    def get_full_email(self):
        return full_email(self.email, self.get_name())

    def anonymize(self):
        self.firstname = self.lastname = self.email = self.phone = \
            Guest.anonymized
        self.save()

    @staticmethod
    def filter_anonymized():
        return Q(
            firstname=Guest.anonymized,
            lastname=Guest.anonymized,
            email=Guest.anonymized,
            phone=Guest.anonymized
        )


class Booking(models.Model):

    class Meta:
        verbose_name = _('booking')
        verbose_name_plural = _('bookinger')

    objects = BookingQuerySet.as_manager()

    booker = models.OneToOneField(
        Guest,
        on_delete=models.CASCADE
    )

    visit = models.ForeignKey(
        Visit,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name=_('Besøg'),
        on_delete=models.SET_NULL
    )

    waitinglist_spot = models.IntegerField(
        default=0,
        verbose_name=_('Ventelisteposition')
    )

    notes = models.TextField(
        blank=True,
        verbose_name='Bemærkninger'
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True,
        on_delete=models.SET_NULL,
    )

    cancelled = models.BooleanField(
        default=False,
        verbose_name='Aflyst'
    )

    def get_visit_attr(self, attrname):
        if not self.visit:
            return None
        return getattr(self.visit, attrname, None)

    def raise_readonly_attr_error(self, attrname):
        raise Exception(
            _("Attribute %s on Booking is readonly.") % attrname +
            _("Set it on the Visit instead.")
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

        unit_qs = user.userprofile.get_unit_queryset()
        return qs.filter(
            visit__eventtime__product__organizationalunit__in=unit_qs
        )

    def get_absolute_url(self):
        return reverse('booking-view', args=[self.pk])

    def get_url(self):
        return settings.PUBLIC_URL + self.get_absolute_url()

    def get_recipients(self, template_type):
        recipients = self.visit.get_recipients(template_type)
        if template_type.send_to_booker and (
            not self.is_waiting or
            template_type.send_to_booker_on_waitinglist
        ) and (
            not self.cancelled
        ):
            recipients.append(
                KUEmailRecipient.create(
                    self.booker,
                    KUEmailRecipient.TYPE_GUEST
                )
            )
        return recipients

    def get_reply_recipients(self, template_type):
        return self.visit.get_reply_recipients(template_type)

    def autosend(self, template_type, recipients=None,
                 only_these_recipients=False,
                 only_these_types=KUEmailRecipient.all_types
                 ):

        visit = self.visit.real
        enabled = visit.autosend_enabled(template_type)

        if visit.is_multiproductvisit and template_type.key in [
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST,
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST_STUDENTS,
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND,
            EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND_STUDENTS
        ]:
            for product in visit.products:
                if product.autosend_enabled(template_type):
                    # print("Making exception for evaluation " \
                    #       "mail with product %d" % product.id)
                    enabled = True
                    break

        if enabled:
            product = visit.product
            unit = visit.organizationalunit
            if recipients is None:
                recipients = []
            if not only_these_recipients:
                recipients.extend(self.get_recipients(template_type))
            recipients = KUEmailRecipient.filter_list(
                recipients,
                only_these_types
            )
            KUEmailMessage.send_email(
                template_type,
                {
                    'booking': self,
                    'product': product,
                    'booker': self.booker,
                    'besoeg': visit,
                    'visit': visit,
                },
                recipients,
                self.visit,
                organizationalunit=unit,
                original_from_email=self.get_reply_recipients(template_type)
            )
            return True
        return False

    def as_searchtext(self):
        return " ".join([x for x in [
            self.booker.as_searchtext(),
            self.notes
        ] if x])

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()

    def __str__(self):
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
        verbose_name = _('booking for klassebesøg')
        verbose_name_plural = _('bookinger for klassebesøg')

    tour_desired = models.BooleanField(
        verbose_name=_('Rundvisning ønsket'),
        default=False
    )
    catering_desired = models.BooleanField(
        verbose_name=_('Forplejning ønsket'),
        default=False
    )
    presentation_desired = models.BooleanField(
        verbose_name=_('Oplæg om uddannelse ønsket'),
        default=False
    )
    custom_desired = models.BooleanField(
        verbose_name=_('Specialtilbud ønsket'),
        default=False
    )

    def verbose_desires(self):
        desires = []
        if self.tour_desired:
            desires.append(_('rundvisning'))
        if self.catering_desired:
            desires.append(_('forplejning'))
        if self.presentation_desired:
            desires.append(_('oplæg om uddannelse'))
        if self.custom_desired:
            try:
                desires.append(self.visit.product.custom_name.lower())
            except:
                pass
        return prose_list_join(desires, ', ', _(' og '))


class TeacherBooking(Booking):

    class Meta:
        verbose_name = _('booking for tilbud til undervisere')
        verbose_name_plural = _('bookinger for tilbud til undervisere')

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

    booking = models.ForeignKey(
        Booking,
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GYMNASIE,
            ]
        }
    )
    level = models.ForeignKey(
        GymnasieLevel,
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "%s (for booking %s)" % (self.display_value(), self.booking.pk)

    def display_value(self):
        return '%s på %s niveau' % (self.subject.name, self.level)


class BookingGrundskoleSubjectLevel(models.Model):

    class Meta:
        verbose_name = _('klasseniveau for booking (grundskole)')
        verbose_name_plural = _('klasseniveauer for bookinger(grundskole)')

    booking = models.ForeignKey(
        Booking,
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GRUNDSKOLE,
            ]
        }
    )
    level = models.ForeignKey(
        GrundskoleLevel,
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "%s (for booking %s)" % (self.display_value(), self.booking.pk)

    def display_value(self):
        return '%s på %s niveau' % (self.subject.name, self.level)


class KUEmailMessage(models.Model):
    """Email data for logging purposes."""

    objects = KUEmailMessageQuerySet.as_manager()

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
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        default=None,
        on_delete=models.SET_NULL
    )
    object_id = models.PositiveIntegerField(null=True, default=None)
    content_object = GenericForeignKey('content_type', 'object_id')
    reply_nonce = models.UUIDField(
        blank=True,
        null=True,
        default=None
    )
    template_key = models.IntegerField(
        verbose_name='Template key',
        default=None,
        null=True,
        blank=True
    )
    template_type = models.ForeignKey(
        EmailTemplateType,
        verbose_name='Template type',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    reply_to_message = models.ForeignKey(
        'KUEmailMessage',
        verbose_name='Reply to',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    @staticmethod
    def extract_addresses(recipients):
        if type(recipients) != list:
            recipients = [recipients]
        emails = []
        for recipient in recipients:
            name = None
            address = None
            user = None
            guest = None
            if isinstance(recipient, str):
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
            if address is not None and address != '':

                email = {
                    'address': address,
                    'user': user,
                    'guest': guest,
                }

                if name is not None:
                    email['name'] = name
                    email['full'] = "\"%s\" <%s>" % (name, address)
                else:
                    email['full'] = address

                email['get_full_name'] = email.get('name', email['full'])

                if guest is not None:
                    email['type'] = 'Gæst'
                elif user is not None:
                    role = user.userprofile.get_role()
                    if role != NONE:
                        email['type'] = get_role_name(role)
                if 'type' not in email:
                    email['type'] = 'Anden'

                emails.append(email)
        return emails

    @staticmethod
    def save_email(
            email_message, instance, reply_nonce=None, htmlbody=None,
            template_type=None, original_from_email=None, reply_to_message=None
    ):
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
        if type(original_from_email) is not list:
            original_from_email = [original_from_email]
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
                address.formatted_address
                for address in original_from_email
                if isinstance(address, KUEmailRecipient)
            ]),
            recipients=', '.join(email_message.recipients()),
            content_type=ctype,
            object_id=instance.id,
            reply_nonce=reply_nonce,
            template_type=template_type,
            template_key=template_key,
            reply_to_message=reply_to_message
        )
        ku_email_message.save()

        return ku_email_message

    @staticmethod
    def send_email(template, context, recipients, instance,
                   organizationalunit=None, original_from_email=None,
                   reply_to_message=None, **kwargs):
        if isinstance(template, EmailTemplateType):
            key = template.key
            template = EmailTemplate.get_template(
                template, organizationalunit
            )
            if template is None:
                raise Exception(
                    "Template with key %s does not exist!" % key
                )
        if not isinstance(template, EmailTemplate):
            raise Exception(
                "Invalid template object '%s'" % str(template)
            )

        # Alias any visit to "besoeg" for easier use by danes
        if 'besoeg' not in context and 'visit' in context:
            context['besoeg'] = context['visit']

        if type(recipients) is not list:
            recipients = [recipients]

        for recipient in recipients:
            nonce = uuid.uuid4()
            ctx = {
                'organizationalunit': organizationalunit,
                'recipient': recipient,
                'sender': settings.DEFAULT_FROM_EMAIL,
                'reply_nonce': nonce
            }
            ctx.update(context)

            # If we know the visit and the guest we can find the
            # booking if it is missing.
            if 'booking' not in ctx and \
               'besoeg' in ctx and recipient.is_guest:
                ctx['booking'] = Booking.objects.filter(
                    visit=ctx['besoeg'],
                    booker=recipient.guest
                ).first()

            subject = template.expand_subject(ctx)
            subject = ''.join([
                re.sub(r'\s+', ' ', x)
                for x in subject.split('\n')
            ]).strip()
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
                to=[recipient.formatted_address],
            )
            if htmlbody is not None:
                message.attach_alternative(htmlbody, 'text/html')
            message.send()

            msg_obj = KUEmailMessage.save_email(
                message, instance, reply_nonce=nonce,
                template_type=template.type,
                original_from_email=original_from_email,
                reply_to_message=reply_to_message
            )
            recipient.email_message = msg_obj
            recipient.save()

        # Log the sending
        if recipients and instance:
            logmessage = [
                _("Template: %s") % template.type.name
                if template.type else "None",
                _("Modtagere: %s") % ", ".join([
                    "%s (%s)" % (x.formatted_address, x.role_name)
                    for x in recipients
                ])
            ]
            ctxmsg = context.get('log_message', None)
            if ctxmsg:
                logmessage.append(str(ctxmsg))

            log_action(
                context.get("web_user", None),
                instance,
                LOGACTION_MAIL_SENT,
                "\n".join(logmessage)
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

    @property
    def replies(self):
        return KUEmailMessage.objects.filter(reply_to_message=self)\
            .order_by('-created')

    anonymized = "[anonymiseret]"
    anonymized_filter = {'recipients': anonymized}

    def anonymize(self):
        self.recipients = KUEmailMessage.anonymized
        self.body = KUEmailMessage.anonymized
        self.htmlbody = KUEmailMessage.anonymized
        self.save()


class BookerResponseNonce(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    booker = models.ForeignKey(
        Guest,
        on_delete=models.CASCADE
    )
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


class SurveyXactEvaluation(models.Model):

    DEFAULT_STUDENT_SURVEY_ID = \
        settings.SURVEYXACT['default_survey_id']['student']
    DEFAULT_TEACHER_SURVEY_ID = \
        settings.SURVEYXACT['default_survey_id']['teacher']

    surveyId = models.IntegerField()

    guests = models.ManyToManyField(
        Guest,
        through='SurveyXactEvaluationGuest'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True
    )

    for_students = models.BooleanField(
        default=False
    )
    for_teachers = models.BooleanField(
        default=False
    )

    @property
    def evaluationguests(self):
        return self.surveyxactevaluationguest_set.all().order_by('id')

    def send_notification(self, template_type, new_status, filter=None):
        qs = self.evaluationguests
        if filter is not None:
            qs = qs.filter(**filter)
        for evalguest in qs:
            sent = evalguest.booking.autosend(
                template_type
            )
            if sent:
                evalguest.status = new_status
                evalguest.save()

    def send_first_notification(self, visit):
        qs = self.evaluationguests.filter(guest__booking__visit=visit)
        for evalguest in qs:
            evalguest.send(True)

    def send_second_notification(self, visit):
        qs = self.evaluationguests.filter(
            status=SurveyXactEvaluationGuest.STATUS_FIRST_SENT,
            guest__booking__visit=visit
        )
        for evalguest in qs:
            evalguest.send(True)

    def product_autosend_activated(self):
        return self.product.get_autosends().filter(
            template_type__key__in=[
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST,
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST_STUDENTS,
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND,
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND_STUDENTS
            ]
        )

    def product_autosend_activated_data(self):
        autosends = set([
            autosend.template_type.key
            for autosend in self.product_autosend_activated()
        ])
        return {
            'teacher_first':
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST in autosends,
            'teacher_second':
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND in autosends,
            'student_first':
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST_STUDENTS
                in autosends,
            'student_second':
                EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND_STUDENTS
                in autosends
        }

    def save(self, *args, **kwargs):
        super(SurveyXactEvaluation, self).save(*args, **kwargs)
        for visit in self.product.get_visits():
            if visit.is_multi_sub:
                visit = visit.multi_master
            for booking in visit.booking_list:
                guest = booking.booker
                if SurveyXactEvaluationGuest.objects.filter(
                    evaluation=self,
                    guest=guest
                ).count() == 0:
                    evaluationguest = SurveyXactEvaluationGuest(
                        evaluation=self,
                        guest=guest
                    )
                    evaluationguest.save()

    def __str__(self):
        return "SurveyXactEvaluation #%d (%s)" % (self.pk, self.product.title)


class SurveyXactEvaluationGuest(models.Model):
    objects = SurveyXactEvaluationGuestQuerySet.as_manager()

    evaluation = models.ForeignKey(
        SurveyXactEvaluation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    guest = models.ForeignKey(
        Guest,
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )
    # deprecate
    visit = models.ForeignKey(
        Visit,
        null=False,
        on_delete=models.CASCADE
    )
    STATUS_NO_PARTICIPATION = 0
    STATUS_NOT_SENT = 1
    STATUS_FIRST_SENT = 2
    STATUS_SECOND_SENT = 3
    STATUS_LINK_CLICKED = 4
    status_choices = [
        (STATUS_NO_PARTICIPATION, _('Modtager ikke evaluering')),
        (STATUS_NOT_SENT, _('Ikke afholdt / ikke afsendt')),
        (STATUS_FIRST_SENT, _('Sendt første gang')),
        (STATUS_SECOND_SENT, _('Sendt anden gang')),
        (STATUS_LINK_CLICKED, _('Har klikket på link'))
    ]
    status = models.SmallIntegerField(
        choices=status_choices,
        verbose_name='status',
        default=STATUS_NOT_SENT
    )
    shortlink_id = models.CharField(
        max_length=16,
    )

    @property
    def link(self):
        return self.link_obtain(self.shortlink_id)

    @staticmethod
    def link_obtain(shortlink_id):
        s = settings.PUBLIC_URL + reverse(
            'evaluation-redirect',
            args=[shortlink_id]
        )
        return s

    @property
    def status_display(self):
        for status, label in self.status_choices:
            if status == self.status:
                return label

    def save(self, *args, **kwargs):
        if self.shortlink_id is None or len(self.shortlink_id) == 0:
            self.shortlink_id = ''.join(get_random_string(length=13))
        return super(SurveyXactEvaluationGuest, self).save(*args, **kwargs)

    @property
    def booking(self):
        return self.guest.booking

    @property
    def visit(self):
        return self.guest.booking.visit

    @property
    def product(self):
        return self.evaluation.product

    @staticmethod
    def get_redirect_url(shortlink_id, set_link_click=False):
        try:
            evalguest = SurveyXactEvaluationGuest.objects.get(
                shortlink_id=shortlink_id,
            )
        except:
            return None
        url = surveyxact_upload(
            evalguest.evaluation.surveyId, evalguest.get_surveyxact_data()
        )
        if url is None or 'error' in url:
            return None
        if set_link_click:
            evalguest.link_clicked()
        return url

    def get_surveyxact_data(self):
        product = self.product
        visit = self.visit
        guest = self.guest
        data = {
            'email': guest.email,
            'ID': product.id,
            'tid': visit.start_datetime.strftime('%Y.%m.%d %H:%M:%S')
            if visit.start_datetime is not None else None,
            'niveau': Guest.grundskole_level_conversion.get(
                self.guest.level, None
            )
            if guest.line is None
            else Guest.sx_line_conversion.get(guest.line, None),
            'antal': guest.attendee_count,
            'elever': guest.student_count,
            'lærere': guest.teacher_count or 0,
            'oplæg': bool2int(
                getattr(visit, 'presentation_desired', False)
            ),
            'rundvis': bool2int(
                getattr(visit, 'tour_desired', False)
            ),
            'region': getattr_long(guest, 'school.municipality.region.id'),
            'skole': getattr_long(guest, 'school.name'),
            'skole_id': getattr_long(guest, 'school.id'),
            'postnr': getattr_long(guest, 'school.postcode.number'),
            'gæst': ' '.join(
                prune_list([guest.firstname, guest.lastname], True)
            )
        }

        visits = visit.real.subvisits \
            if visit.is_multiproductvisit \
            else [visit]

        index = 1
        for visit in visits:
            if not visit.is_cancelled and not visit.is_rejected:
                teachers = list(visit.assigned_teachers)
                product = visit.product
                data.update({
                    "akt%d" % index: product.title,
                    "type%d" % index: product.type,
                    "enhed%d" % index: getattr_long(
                        product, 'organizationalunit.id'
                    ),
                    "oenhed%d" % index: getattr_long(
                        product, 'organizationalunit.parent.id'
                    ),
                    "undvn%d" % index: ', '.join([
                        teacher.get_full_name() for teacher in teachers
                    ]),
                    "undvm%d" % index: ', '.join([
                        teacher.email for teacher in teachers
                    ])
                })
                index += 1
                if index > 4:
                    break
        return data

    def link_clicked(self):
        self.status = self.STATUS_LINK_CLICKED
        self.save()

    def send(self, first=True):
        template_types = []
        if first:
            if self.evaluation.for_students:
                template_types.append(
                    EmailTemplateType.notify_guest__evaluation_first_students
                )
            if self.evaluation.for_teachers:
                template_types.append(
                    EmailTemplateType.notify_guest__evaluation_first
                )
            new_status = SurveyXactEvaluationGuest.STATUS_FIRST_SENT
        else:
            if self.evaluation.for_students:
                template_types.append(
                    EmailTemplateType.notify_guest__evaluation_second_students
                )
            if self.evaluation.for_teachers:
                template_types.append(
                    EmailTemplateType.notify_guest__evaluation_second
                )
            new_status = SurveyXactEvaluationGuest.STATUS_SECOND_SENT

        sent = False
        for template_type in template_types:
            if self.booking.autosend(template_type):
                sent = True
        if sent:
            self.status = new_status
            self.save()


class Guide(models.Model):
    value = models.IntegerField(
        null=False
    )
    name = models.CharField(
        null=False,
        max_length=64
    )

    def __str__(self):
        return self.name

    @staticmethod
    def create_defaults():
        from booking.data import guides
        for value, name in guides.guides.items():
            if Guide.objects.filter(value=value).count() == 0:
                guide = Guide(value=value, name=name)
                guide.save()


class ExercisePresentation(models.Model):
    value = models.IntegerField(
        null=False
    )
    name = models.CharField(
        null=False,
        max_length=256
    )

    def __str__(self):
        return self.name

    @staticmethod
    def create_defaults():
        from booking.data import exercises_presentations
        for value, name in exercises_presentations.\
                exercises_presentations.items():
            if ExercisePresentation.objects.filter(value=value).count() == 0:
                exercise_presentation = ExercisePresentation(
                    value=value, name=name
                )
                exercise_presentation.save()


from booking.resource_based import models as rb_models  # noqa

EventTime = rb_models.EventTime
Calendar = rb_models.Calendar
CalendarEvent = rb_models.CalendarEvent
CalendarEventInstance = rb_models.CalendarEventInstance
CalendarCalculatedAvailable = rb_models.CalendarCalculatedAvailable
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
