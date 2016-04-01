# encoding: utf-8
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import Sum
from django.db.models import Q
from django.template.context import make_context
from django.utils import timezone
from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.base import Template, VariableNode

from recurrence.fields import RecurrenceField
from booking.utils import ClassProperty, full_email, CustomStorage, html2text
from resource_booking import settings

from datetime import datetime, timedelta

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


class Person(models.Model):
    """A dude or chick"""

    class Meta:
        verbose_name = _(u'kontaktperson')
        verbose_name_plural = _(u'kontaktpersoner')

    # Eventually this could just be a pointer to AD
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=14, null=True, blank=True)

    unit = models.ForeignKey("Unit", blank=True, null=True)

    allow_null_unit_editing = True

    def __unicode__(self):
        return self.name

    def get_name(self):
        return self.name

    def get_email(self):
        return self.email

    def get_full_email(self):
        return full_email(self.email, self.name)


# Units (faculties, institutes etc)
class UnitType(models.Model):
    """A type of organization, e.g. 'faculty' """

    class Meta:
        verbose_name = _(u"enhedstype")
        verbose_name_plural = _(u"Enhedstyper")

    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    """A generic organizational unit, such as a faculty or an institute"""

    class Meta:
        verbose_name = _(u"enhed")
        verbose_name_plural = _(u"enheder")
        ordering = ['name']

    name = models.CharField(max_length=100)
    type = models.ForeignKey(UnitType)
    parent = models.ForeignKey('self', null=True, blank=True)
    contact = models.ForeignKey(
        Person, null=True, blank=True,
        verbose_name=_(u'Kontaktperson'),
        related_name="contactperson_for_units"
    )
    url = models.URLField(
        verbose_name=u'Hjemmeside',
        null=True,
        blank=True
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
        offspring = Unit.objects.filter(parent=self)
        all_children = Unit.objects.none()
        for u in offspring:
            all_children = all_children | u.get_descendants()
        return all_children | Unit.objects.filter(pk=self.pk)

    def get_faculty_queryset(self):
        u = self

        # Go through parent relations until we hit a "fakultet"
        while u and u.type and u.type.name != "Fakultet":
            u = u.parent

        if u:
            return Unit.objects.filter(Q(pk=u.pk) | Q(parent=u))
        else:
            return Unit.objects.none()

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.type.name)

    def get_users(self, role=None):
        if role is not None:
            profiles = self.userprofile_set.filter(user_role__role=role).all()
        else:
            profiles = self.userprofile_set.all()
        return [profile.user for profile in profiles]

    def get_hosts(self):
        from profile.models import HOST
        return self.get_users(HOST)

    def get_teachers(self):
        from profile.models import TEACHER
        return self.get_users(TEACHER)

    def get_recipients(self, template_key):
        recipients = []
        if template_key in EmailTemplate.unit_hosts_keys:
            recipients.extend(self.get_hosts())
        if template_key in EmailTemplate.unit_teachers_keys:
            recipients.extend(self.get_teachers())
        return recipients


# Master data related to bookable resources start here
class Subject(models.Model):
    """A relevant subject from primary or secondary education."""

    class Meta:
        verbose_name = _(u"fag")
        verbose_name_plural = _(u"fag")

    SUBJECT_TYPE_GYMNASIE = 2**0
    SUBJECT_TYPE_GRUNDSKOLE = 2**1
    # NEXT_VALUE = 2**2

    SUBJECT_TYPE_BOTH = SUBJECT_TYPE_GYMNASIE | SUBJECT_TYPE_GRUNDSKOLE

    type_choices = (
        (SUBJECT_TYPE_GYMNASIE, _(u'Gymnasie')),
        (SUBJECT_TYPE_GRUNDSKOLE, _(u'Grundskole')),
        (SUBJECT_TYPE_BOTH, _(u'Begge')),
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


class AdditionalService(models.Model):
    """Additional services, i.e. tour of the place, food and drink, etc."""

    class Meta:
        verbose_name = _(u'ekstra ydelse')
        verbose_name_plural = _(u'ekstra ydelser')

    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class SpecialRequirement(models.Model):
    """Special requirements for visit - e.g., driver's license."""

    class Meta:
        verbose_name = _(u'særligt krav')
        verbose_name_plural = _(u'særlige ydelser')

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
    resource = models.ForeignKey('Resource', null=True,
                                 on_delete=models.CASCADE,
                                 )

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

    name = models.CharField(max_length=256, verbose_name=_(u'Navn'))
    description = models.TextField(blank=True, verbose_name=_(u'Beskrivelse'))
    address_line = models.CharField(max_length=256, verbose_name=_(u'Adresse'))
    zip_city = models.CharField(
        max_length=256, verbose_name=_(u'Postnummer og by')
    )
    unit = models.ForeignKey(Unit, verbose_name=_(u'Enhed'), blank=True,
                             null=True)

    def __unicode__(self):
        return self.name


class EmailTemplate(models.Model):

    NOTIFY_GUEST__BOOKING_CREATED = 1  # ticket 13806
    NOTIFY_HOST__BOOKING_CREATED = 2  # ticket 13807
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

    # Choice labels
    key_choices = [
        (NOTIFY_GUEST__BOOKING_CREATED, _(u'Gæst: Booking oprettet')),
        (NOTIFY_GUEST__GENERAL_MSG, _(u'Gæst: Generel besked')),
        (NOTIFY_HOST__BOOKING_CREATED, _(u'Vært: Booking oprettet')),
        (NOTIFY_HOST__REQ_TEACHER_VOLUNTEER,
         _(u'Vært: Frivillige undervisere')),
        (NOTIFY_HOST__REQ_HOST_VOLUNTEER, _(u'Vært: Frivillige værter')),
        (NOTIFY_HOST__ASSOCIATED, _(u'Vært: Tilknyttet besøg')),
        (NOTIFY_HOST__REQ_ROOM, _(u'Vært: Forespørg lokale')),
        (NOTIFY_ALL__BOOKING_COMPLETE, _(u'Alle: Booking færdigplanlagt')),
        (NOTIFY_ALL__BOOKING_CANCELED, _(u'Alle: Booking aflyst')),
        (NOTITY_ALL__BOOKING_REMINDER, _(u'Alle: Reminder om booking')),
        (NOTIFY_HOST__HOSTROLE_IDLE, _(u'Vært: Ledig værtsrolle')),
        (SYSTEM__BASICMAIL_ENVELOPE, _(u'Forespørgsel fra bruger'))
    ]

    @staticmethod
    def get_name(template_key):
        for key, label in EmailTemplate.key_choices:
            if key == template_key:
                return label

    # Templates available for manual sending from visit occurrences
    visitoccurrence_manual_keys = [
        NOTIFY_GUEST__GENERAL_MSG,
        NOTIFY_HOST__ASSOCIATED,
        NOTIFY_HOST__REQ_TEACHER_VOLUNTEER,
        NOTIFY_HOST__REQ_HOST_VOLUNTEER,
        NOTIFY_HOST__REQ_ROOM,
        NOTIFY_ALL__BOOKING_COMPLETE,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER
    ]

    # Templates available for manual sending from bookings
    booking_manual_keys = [
        NOTIFY_GUEST__BOOKING_CREATED,
        NOTIFY_GUEST__GENERAL_MSG,
        NOTIFY_ALL__BOOKING_COMPLETE,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER
    ]

    # Templates that will be autosent to visit.contact_persons
    contact_person_keys = [
        NOTIFY_HOST__BOOKING_CREATED,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER,
        NOTIFY_HOST__HOSTROLE_IDLE
    ]
    # Templates that will be autosent to booker
    booker_keys = [
        NOTIFY_GUEST__BOOKING_CREATED,
        NOTIFY_ALL__BOOKING_COMPLETE,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER
    ]
    # Templates that will be autosent to hosts in the unit
    unit_hosts_keys = [
        NOTIFY_HOST__REQ_HOST_VOLUNTEER
    ]
    # Templates that will be autosent to teachers in the unit
    unit_teachers_keys = [
        NOTIFY_HOST__REQ_TEACHER_VOLUNTEER
    ]
    # Templates that will be autosent to room admins in the resource
    resource_roomadmin_keys = [
        NOTIFY_HOST__REQ_ROOM
    ]
    # Templates that will be autosent to hosts in the occurrence
    occurrence_hosts_keys = [
        NOTIFY_ALL__BOOKING_COMPLETE,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER
    ]
    # Templates that will be autosent to teachers in the occurrence
    occurrence_teachers_keys = [
        NOTIFY_ALL__BOOKING_COMPLETE,
        NOTIFY_ALL__BOOKING_CANCELED,
        NOTITY_ALL__BOOKING_REMINDER
    ]
    # Template that will be autosent to hosts
    # when they are added to an occurrence
    occurrence_added_host_key = NOTIFY_HOST__ASSOCIATED
    # Templates where the "days" field makes sense
    enable_days = [
        NOTITY_ALL__BOOKING_REMINDER,
        NOTIFY_HOST__HOSTROLE_IDLE
    ]

    key = models.IntegerField(
        verbose_name=u'Key',
        choices=key_choices,
        default=1
    )

    subject = models.CharField(
        max_length=77,
        verbose_name=u'Emne'
    )

    body = models.CharField(
        max_length=65584,
        verbose_name=u'Tekst'
    )

    unit = models.ForeignKey(
        Unit,
        verbose_name=u'Enhed',
        null=True,
        blank=True
    )

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

    @staticmethod
    def _expand(text, context, keep_placeholders=False):
        template = Template(unicode(text))
        if keep_placeholders:
            template.engine.string_if_invalid = "{{ %s }}"
        if isinstance(context, dict):
            context = make_context(context)
        return template.render(context)

    @staticmethod
    def get_template(template_key, unit, include_overridden=False):
        templates = []
        while unit is not None and (include_overridden or len(templates) == 0):
            try:
                templates.append(EmailTemplate.objects.filter(
                    key=template_key,
                    unit=unit
                ).all()[0])
            except:
                pass
            unit = unit.parent
        if include_overridden or len(templates) == 0:
            try:
                templates.append(
                    EmailTemplate.objects.filter(key=template_key,
                                                 unit__isnull=True)[0]
                )
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
                unit__isnull=True
            ).all()
        else:
            templates = list(EmailTemplate.objects.filter(
                unit=unit
            ).all())
        if include_inherited and unit is not None and unit.parent != unit:
            templates.extend(EmailTemplate.get_templates(unit.parent, True))
        return templates

    def get_template_variables(self):
        variables = []
        for item in [self.subject, self.body]:
            text = item.replace("%20", " ")
            template = Template(unicode(text))
            for node in template:
                if isinstance(node, VariableNode):
                    variables.append(unicode(node.filter_expression))
        return variables


class ObjectStatistics(models.Model):

    created_time = models.DateTimeField(
        blank=False,
        auto_now_add=True,
    )
    updated_time = models.DateTimeField(
        blank=False,
        default=datetime.now()
        # auto_now=True  # This would update the field on every save,
        # including when we just want to update the display counter
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
        self.visited_time = datetime.now()
        self.save()

    def on_update(self):
        self.updated_time = datetime.now()
        self.save()


# Bookable resources
class Resource(models.Model):
    """Abstract superclass for a bookable resource of any kind."""

    # Resource type.
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

    # Target audience choice - student or teacher.
    AUDIENCE_TEACHER = 2**0
    AUDIENCE_STUDENT = 2**1
    AUDIENCE_ALL = AUDIENCE_TEACHER | AUDIENCE_STUDENT

    audience_choices = (
        (AUDIENCE_TEACHER, _(u'Lærer')),
        (AUDIENCE_STUDENT, _(u'Elev')),
        (AUDIENCE_ALL, _(u'Alle'))
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

    # Resource state - created, active and discontinued.
    CREATED = 0
    ACTIVE = 1
    DISCONTINUED = 2

    state_choices = (
        (CREATED, _(u"Oprettet")),
        (ACTIVE, _(u"Aktivt")),
        (DISCONTINUED, _(u"Ophørt"))
    )

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    type = models.IntegerField(choices=resource_type_choices,
                               default=STUDY_MATERIAL)
    state = models.IntegerField(choices=state_choices, default=CREATED,
                                verbose_name=_(u"Tilstand"))
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
    unit = models.ForeignKey(Unit, null=True, blank=False,
                             verbose_name=_('Enhed'))
    links = models.ManyToManyField(Link, blank=True, verbose_name=_('Links'))
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'),
                                   default=AUDIENCE_ALL,
                                   blank=False)

    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY,
                                            blank=False)

    locality = models.ForeignKey(
        Locality,
        verbose_name=_(u'Lokalitet'),
        blank=True,
        null=True
    )

    recurrences = RecurrenceField(
        null=True,
        blank=True,
        verbose_name=_(u'Gentagelser')
    )

    contact_persons = models.ManyToManyField(
        Person,
        blank=True,
        verbose_name=_(u'Kontaktpersoner'),
        related_name='contact_visit'
    )

    room_responsible = models.ManyToManyField(
        Person,
        blank=True,
        verbose_name=_(u'Lokaleansvarlige'),
        related_name='roomadmin_visit'
    )

    preparation_time = models.IntegerField(
        default=0,
        null=True,
        verbose_name=_(u'Forberedelsestid (i timer)')
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
        through='ResourceGymnasieFag',
        related_name='gymnasie_resources'
    )

    grundskolefag = models.ManyToManyField(
        Subject, blank=True,
        verbose_name=_(u'Grundskolefag'),
        through='ResourceGrundskoleFag',
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
        verbose_name=_(u"Oprettet af")
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

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True
    )

    def __unicode__(self):
        return self.title + "(%s)" % str(self.id)

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
        if self.unit:
            texts.append(self.unit.name)

            # Unit's parent name
            if self.unit.parent:
                texts.append(self.unit.parent.name)

        # Url, name and description of all links
        for l in self.links.all():
            if l.url:
                texts.append(l.url)
            if l.name:
                texts.append(l.name)
            if l.description:
                texts.append(l.description)

        # Display-value for audience
        texts.append(self.get_audience_display() or "")

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

    def get_dates_display(self):
        if self.visit:
            return self.visit.get_dates_display()

        return "-"

    def all_subjects(self):
        return (
            [x for x in self.resourcegymnasiefag_set.all()] +
            [x for x in self.resourcegrundskolefag_set.all()]
        )

    def display_locality(self):
        try:
            return self.visit.locality
        except Visit.DoesNotExist:
            pass
        return "-"

    def get_absolute_url(self):
        return reverse('resource-view', args=[self.pk])

    def get_url(self):
        return settings.PUBLIC_URL + self.get_absolute_url()

    def url(self):
        return self.get_url()

    def get_occurrences(self):
        if not hasattr(self, "visit") or not self.visit:
            return VisitOccurrence.objects.none()
        else:
            return self.visit.visitoccurrence_set.all()

    def first_occurence(self):
        return self.get_occurrences().first()

    def get_state_class(self):
        if self.state == self.CREATED:
            return 'info'
        elif self.state == self.ACTIVE:
            return 'primary'
        else:
            return 'default'

    def get_recipients(self, template_key):
        recipients = self.unit.get_recipients(template_key)
        if template_key in EmailTemplate.contact_person_keys:
            recipients.extend(self.contact_persons.all())
        if template_key in EmailTemplate.resource_roomadmin_keys:
            recipients.extend(self.room_responsible.all())
        return recipients

    def get_view_url(self):
        if hasattr(self, 'visit') and self.visit:
            return reverse('visit-view', args=[self.visit.pk])
        if hasattr(self, 'otherresource') and self.otherresource:
            return reverse('otherresource-view', args=[self.otherresource.pk])
        return reverse('resource-view', args=[self.pk])

    @staticmethod
    def get_latest_created():
        return Resource.objects.filter(statistics__isnull=False).\
            order_by('-statistics__created_time')

    @staticmethod
    def get_latest_updated():
        return Resource.objects.filter(statistics__isnull=False).\
            order_by('-statistics__updated_time')

    @staticmethod
    def get_latest_displayed():
        return Resource.objects.filter(statistics__isnull=False).\
            order_by('-statistics__visited_time')

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()


class ResourceGymnasieFag(models.Model):
    class Meta:
        verbose_name = _(u"gymnasiefagtilknytning")
        verbose_name_plural = _(u"gymnasiefagtilknytninger")

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    resource = models.ForeignKey(Resource, blank=False, null=False)
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
    def create_from_submitvalue(cls, resource, value):
        f = ResourceGymnasieFag(resource=resource)

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
        return u"%s (for '%s')" % (self.display_value(), self.resource.title)

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
        return ResourceGymnasieFag.display(
            self.subject, self.ordered_levels()
        )

    def as_submitvalue(self):
        res = unicode(self.subject.pk)
        levels = ",".join([unicode(x.pk) for x in self.ordered_levels()])

        if levels:
            res = ",".join([res, levels])

        return res


class ResourceGrundskoleFag(models.Model):
    class Meta:
        verbose_name = _(u"grundskolefagtilknytning")
        verbose_name_plural = _(u"grundskolefagtilknytninger")

    class_level_choices = [(i, unicode(i)) for i in range(0, 11)]

    resource = models.ForeignKey(Resource, blank=False, null=False)
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
    def create_from_submitvalue(cls, resource, value):
        f = ResourceGrundskoleFag(resource=resource)

        values = value.split(",")

        # First element in value list is pk of subject
        f.subject = Subject.objects.get(pk=values.pop(0))

        f.class_level_min = values.pop(0) or 0
        f.class_level_max = values.pop(0) or 0

        f.save()

        return f

    def __unicode__(self):
        return u"%s (for '%s')" % (self.display_value(), self.resource.title)

    @classmethod
    def display(cls, subject, clevel_min, clevel_max):
        class_range = []
        if clevel_min:
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
        return ResourceGrundskoleFag.display(
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


class OtherResource(Resource):
    """A non-bookable, non-visit resource, basically material on the Web."""

    objects = SearchManager(
        fields=(
            'title',
            'description',
            'mouseover_description',
            'extra_search_text'
        ),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    applicable_types = []

    @ClassProperty
    def type_choices(self):
        return (type for type in
                Resource.resource_type_choices
                if type[0] in OtherResource.applicable_types)

    def save(self, *args, **kwargs):
        # Save once to store relations
        super(OtherResource, self).save(*args, **kwargs)

        # Update search_text
        self.extra_search_text = self.generate_extra_search_text()

        # Do the final save
        return super(OtherResource, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('otherresource-view', args=[self.pk])

    def clone_to_visit(self):
        save = []
        visit = Visit()
        visit.type = self.type
        visit.state = self.state
        visit.title = self.title
        visit.teaser = self.teaser
        visit.mouseover_description = self.mouseover_description
        visit.unit = self.unit
        visit.audience = self.audience
        visit.institution_level = self.institution_level
        visit.locality = self.locality
        visit.recurrences = self.recurrences
        visit.comment = self.comment
        visit.extra_search_text = self.extra_search_text
        visit.preparation_time = self.preparation_time
        visit.price = self.price
        visit.save()
        for link in self.links.all():
            visit.links.add(link)
        for contact_person in self.contact_persons.all():
            visit.contact_persons.add(contact_person)
        for intermediate in self.resourcegymnasiefag_set.all():
            values = [str(intermediate.subject.id)]
            for level in intermediate.level.all():
                values.append(str(level.id))
            clone = ResourceGymnasieFag.create_from_submitvalue(
                visit, ','.join(values)
            )
            save.append(clone)
        for intermediate in self.resourcegrundskolefag_set.all():
            clone = ResourceGrundskoleFag()
            clone.resource = visit
            clone.subject = intermediate.subject
            clone.class_level_max = intermediate.class_level_max
            clone.class_level_min = intermediate.class_level_min
            save.append(clone)
        for tag in self.tags.all():
            visit.tags.add(tag)
        for topic in self.topics.all():
            visit.topics.add(topic)
        for item in save:
            item.save()
        print "OtherResource %d cloned into Visit %d" % (self.id, visit.id)

    @staticmethod
    def migrate_to_visits():
        for otherresource in OtherResource.objects.all():
            otherresource.clone_to_visit()
            otherresource.delete()


# Have to do late import of this here or we will get problems
# with cyclic dependencies
from profile.models import TEACHER, HOST  # noqa


class Visit(Resource):
    """A bookable visit of any kind."""

    class Meta:
        verbose_name = _("tilbud")
        verbose_name_plural = _("tilbud")

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
        Resource.STUDENT_FOR_A_DAY, Resource.GROUP_VISIT,
        Resource.TEACHER_EVENT, Resource.OTHER_OFFERS, Resource.STUDY_MATERIAL,
        Resource.OPEN_HOUSE, Resource.ASSIGNMENT_HELP, Resource.STUDIEPRAKTIK,
        Resource.STUDY_PROJECT
    ]

    bookable_types = [
        Resource.STUDENT_FOR_A_DAY, Resource.GROUP_VISIT,
        Resource.TEACHER_EVENT
    ]

    @ClassProperty
    def type_choices(self):
        return (x for x in
                Resource.resource_type_choices
                if x[0] in Visit.applicable_types)

    rooms_needed = models.BooleanField(
        default=True,
        verbose_name=_(u"Tilbuddet kræver brug af et eller flere lokaler")
    )

    ROOMS_ASSIGNED_ON_VISIT = 0
    ROOMS_ASSIGNED_WHEN_BOOKING = 1

    rooms_assignment_choices = (
        (ROOMS_ASSIGNED_ON_VISIT, _(u"Lokaler tildeles på forhånd")),
        (ROOMS_ASSIGNED_WHEN_BOOKING, _(u"Lokaler tildeles ved booking")),
    )

    rooms_assignment = models.IntegerField(
        choices=rooms_assignment_choices,
        default=ROOMS_ASSIGNED_ON_VISIT,
        verbose_name=_(u"Tildeling af lokale(r)"),
        blank=True,
        null=True
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

    additional_services = models.ManyToManyField(
        AdditionalService,
        verbose_name=_(u'Ekstra ydelser'),
        blank=True
    )
    special_requirements = models.ManyToManyField(
        SpecialRequirement,
        verbose_name=_(u'Særlige krav'),
        blank=True
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
    do_create_waiting_list = models.BooleanField(
        default=False, verbose_name=_(u'Opret venteliste')
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

    NEEDED_NUMBER_NONE = 0
    NEEDED_NUMBER_MORE_THAN_TEN = -10

    needed_number_choices = (
        ((NEEDED_NUMBER_NONE, _(u'Ingen')),) +
        tuple((x, unicode(x)) for x in range(1, 11)) +
        ((NEEDED_NUMBER_MORE_THAN_TEN, _(u'Mere end 10')),)
    )

    needed_hosts = models.IntegerField(
        default=0,
        verbose_name=_(u'Nødvendigt antal værter'),
        choices=needed_number_choices
    )

    needed_teachers = models.IntegerField(
        default=0,
        verbose_name=_(u'Nødvendigt antal undervisere'),
        choices=needed_number_choices
    )

    default_hosts = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
        related_name="hosted_visits",
        verbose_name=_(u'Faste værter')
    )

    default_teachers = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
        related_name="taught_visits",
        verbose_name=_(u'Faste undervisere')
    )

    @property
    def bookable_occurrences(self):
        return self.visitoccurrence_set.filter(
            bookable=True,
            workflow_status__in=VisitOccurrence.BOOKABLE_STATES
        )

    @property
    def future_events(self):
        return self.bookable_occurrences.filter(
            start_datetime__gte=timezone.now()
        )

    @property
    def recurrences_description(self):
        if self.recurrences and self.recurrences.rrules:
            return [d.to_text() for d in self.recurrences.rrules]
        else:
            return []

    def get_dates_display(self):
        dates = [
            x.display_value for x in self.visitoccurrence_set.all()
        ]
        if len(dates) > 0:
            return ", ".join(dates)
        else:
            return "-"

    def num_of_participants_display(self):
        if self.minimum_number_of_visitors:
            return "%s-%s" % (
                self.minimum_number_of_visitors,
                self.maximum_number_of_visitors
            )
        elif self.maximum_number_of_visitors:
            return self.maximum_number_of_visitors
        return None

    def get_absolute_url(self):
        return reverse('visit-view', args=[self.pk])

    def make_occurrence(self, starttime=None, bookable=False, **kwargs):
        occ = VisitOccurrence(
            visit=self,
            start_datetime=starttime,
            bookable=bookable,
            **kwargs
        )
        occ.save()
        occ.create_inheriting_autosends()

        if self.default_hosts.exists() or self.default_teachers.exists():

            for x in self.default_hosts.all():
                occ.hosts.add(x)

            for x in self.default_teachers.all():
                occ.teachers.add(x)

        return occ

    def get_autosend(self, template_key):
        try:
            item = self.visitautosend_set.filter(
                template_key=template_key, enabled=True)[0]
            return item
        except:
            return None

    def autosend_enabled(self, template_key):
        return self.get_autosend(template_key) is not None

    @property
    def is_type_bookable(self):
        return self.type in self.bookable_types

    @property
    def has_bookable_occurrences(self):
        # If there are no bookable occurrences the booker is allowed to
        # suggest their own.
        if len(self.visitoccurrence_set.filter(bookable=True)) == 0:
            return True

        # Only bookable if there is a valid event in the future:
        return self.future_events.exists()

    @property
    def is_bookable(self):
        return self.is_type_bookable and \
            self.state == Resource.ACTIVE and \
            self.has_bookable_occurrences

    @property
    def duration_as_timedelta(self):
        if self.duration is not None and ':' in self.duration:
            (hours, minutes) = self.duration.split(":")
            return timedelta(
                hours=int(hours),
                minutes=int(minutes)
            )

    @staticmethod
    def get_latest_created():
        return Visit.objects.filter(statistics__isnull=False).\
            order_by('-statistics__created_time')

    @staticmethod
    def get_latest_updated():
        return Visit.objects.filter(statistics__isnull=False).\
            order_by('-statistics__updated_time')

    @staticmethod
    def get_latest_displayed():
        return Visit.objects.filter(statistics__isnull=False).\
            order_by('-statistics__visited_time')

    @staticmethod
    def get_latest_booked():
        bookings = Booking.objects.order_by(
            '-statistics__created_time'
        ).select_related('visitoccurrence__visit')
        visits = set()
        for booking in bookings:
            if booking.visitoccurrence is not None and \
                    booking.visitoccurrence.visit is not None:
                visits.add(booking.visitoccurrence.visit)
        return list(visits)


class VisitOccurrence(models.Model):

    class Meta:
        verbose_name = _(u"besøg")
        verbose_name_plural = _(u"besøg")
        ordering = ['start_datetime']

    objects = SearchManager(
        fields=('extra_search_text'),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE
    )

    start_datetime = models.DateTimeField(
        verbose_name=_(u'Starttidspunkt'),
        null=True,
        blank=True
    )

    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Whether the occurrence is publicly bookable
    bookable = models.BooleanField(
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
        null=True
    )

    hosts = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': HOST
        },
        related_name="hosted_bookings",
        verbose_name=_(u'Værter')
    )

    teachers = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={
            'userprofile__user_role__role': TEACHER
        },
        related_name="taught_bookings",
        verbose_name=_(u'Undervisere')
    )

    STATUS_NOT_NEEDED = 0
    STATUS_OK = 1
    STATUS_NOT_ASSIGNED = 2

    host_status_choices = (
        (STATUS_NOT_NEEDED, _(u'Tildeling af værter ikke påkrævet')),
        (STATUS_NOT_ASSIGNED, _(u'Afventer tildeling')),
        (STATUS_OK, _(u'Tildelt'))
    )

    host_status = models.IntegerField(
        choices=host_status_choices,
        default=STATUS_NOT_ASSIGNED,
        verbose_name=_(u'Status for tildeling af værter')
    )

    teacher_status_choices = (
        (STATUS_NOT_NEEDED, _(u'Tildeling af undervisere ikke påkrævet')),
        (STATUS_NOT_ASSIGNED, _(u'Afventer tildeling')),
        (STATUS_OK, _(u'Tildelt'))
    )

    teacher_status = models.IntegerField(
        choices=teacher_status_choices,
        default=STATUS_NOT_ASSIGNED,
        verbose_name=_(u'Status for tildeling af undervisere')
    )

    room_status_choices = (
        (STATUS_NOT_NEEDED, _(u'Tildeling af lokaler ikke påkrævet')),
        (STATUS_NOT_ASSIGNED, _(u'Afventer tildeling')),
        (STATUS_OK, _(u'Tildelt'))
    )

    room_status = models.IntegerField(
        choices=room_status_choices,
        default=STATUS_NOT_ASSIGNED,
        verbose_name=_(u'Status for tildeling af lokaler')
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True
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
    }

    BOOKABLE_STATES = set([
        WORKFLOW_STATUS_BEING_PLANNED,
        WORKFLOW_STATUS_PLANNED,
    ])

    workflow_status_choices = (
        (WORKFLOW_STATUS_BEING_PLANNED, _(BEING_PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_REJECTED, _(u'Afvist af undervisere eller værter')),
        (WORKFLOW_STATUS_PLANNED, _(PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_PLANNED_NO_BOOKING, _(PLANNED_NOBOOKING_TEXT)),
        (WORKFLOW_STATUS_CONFIRMED, _(u'Bekræftet af booker')),
        (WORKFLOW_STATUS_REMINDED, _(u'Påmindelse afsendt')),
        (WORKFLOW_STATUS_EXECUTED, _(u'Afviklet')),
        (WORKFLOW_STATUS_EVALUATED, _(u'Evalueret')),
        (WORKFLOW_STATUS_CANCELLED, _(u'Aflyst')),
        (WORKFLOW_STATUS_NOSHOW, _(u'Udeblevet')),
    )

    workflow_status = models.IntegerField(
        choices=workflow_status_choices,
        default=WORKFLOW_STATUS_BEING_PLANNED
    )

    comments = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Interne kommentarer')
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
            WORKFLOW_STATUS_PLANNED_NO_BOOKING,
            WORKFLOW_STATUS_CONFIRMED,
            WORKFLOW_STATUS_CANCELLED,
        ],
        WORKFLOW_STATUS_PLANNED_NO_BOOKING: [
            WORKFLOW_STATUS_PLANNED,
            WORKFLOW_STATUS_CONFIRMED,
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
            WORKFLOW_STATUS_EVALUATED,
            WORKFLOW_STATUS_CANCELLED
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
    }

    def can_assign_resources(self):
        being_planned = VisitOccurrence.WORKFLOW_STATUS_BEING_PLANNED
        return self.workflow_status == being_planned

    def planned_status_is_blocked(self):
        # We have to have a chosen starttime before we are planned
        if not self.start_datetime:
            return True

        # It's not blocked if we can't choose it
        ws_planned = VisitOccurrence.WORKFLOW_STATUS_PLANNED
        if ws_planned not in (x[0] for x in self.possible_status_choices()):
            return False

        statuses = (self.host_status, self.teacher_status, self.room_status)

        if VisitOccurrence.STATUS_NOT_ASSIGNED in statuses:
            return True

        return False

    def possible_status_choices(self):
        result = []

        allowed = self.valid_status_changes[self.workflow_status]

        for x in self.workflow_status_choices:
            if x[0] in allowed:
                result.append(x)

        return result

    def get_subjects(self):
        if hasattr(self, 'teacherbooking'):
            return self.teacherbooking.subjects.all()
        else:
            return None

    @property
    def display_value(self):
        if not self.start_datetime:
            return None

        result = self.start_datetime.strftime('%d. %m %Y %H:%M')

        if self.duration:
            try:
                (hours, mins) = self.duration.split(":", 2)
                endtime = self.start_datetime + timedelta(
                    hours=int(hours), minutes=int(mins)
                )
                result += endtime.strftime('-%H:%M')
            except Exception as e:
                print e

        return result

    @property
    def expired(self):
        if self.start_datetime and self.start_datetime <= timezone.now():
            return "expired"
        return ""

    @property
    def needs_teachers(self):
        return len(self.teachers.all()) < self.visit.needed_teachers

    @property
    def needs_hosts(self):
        return len(self.hosts.all()) < self.visit.needed_hosts

    def is_booked(self):
        """Has this VisitOccurrence instance been booked yet?"""
        return len(self.bookings.all()) > 0

    def date_display(self):
        return self.start_datetime or _(u'på ikke-fastlagt tidspunkt')

    def nr_bookers(self):
        nr = len(Booker.objects.filter(booking__visitoccurrence=self))
        nr += self.nr_additional_participants()
        return nr

    def nr_additional_participants(self):
        res = VisitOccurrence.objects.filter(pk=self.pk).aggregate(
            attendees=Sum('bookings__booker__attendee_count')
        )
        return res['attendees'] or 0

    def get_workflow_status_class(self):
        return self.status_to_class_map.get(self.workflow_status, 'default')

    def __unicode__(self):
        if self.start_datetime:
            return u'%s @ %s' % (self.visit.title, self.display_value)
        else:
            return u'%s (uden fastlagt tidspunkt)' % (self.visit.title)

    def get_override_attr(self, attrname):
        result = getattr(self, 'override_' + attrname, None)

        if result is None and self.visit:
            result = getattr(self.visit, attrname)

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

        if self.visit:
            result.append(self.visit.as_searchtext())

        if self.bookings:
            for booking in self.bookings.all():
                result.append(booking.as_searchtext())

        return " ".join(result)

    @classmethod
    def being_planned_queryset(cls, **kwargs):
        return cls.objects.filter(
            workflow_status=cls.WORKFLOW_STATUS_BEING_PLANNED,
            **kwargs
        )

    @classmethod
    def planned_queryset(cls, **kwargs):
        return cls.objects.exclude(
            workflow_status=cls.WORKFLOW_STATUS_BEING_PLANNED,
        ).filter(**kwargs)

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

        # Save once to store relations
        super(VisitOccurrence, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('visit-occ-view', args=[self.pk])

    def get_recipients(self, template_key):
        recipients = self.visit.get_recipients(template_key)
        if template_key in EmailTemplate.occurrence_hosts_keys:
            recipients.extend(self.hosts.all())
        if template_key in EmailTemplate.occurrence_teachers_keys:
            recipients.extend(self.teachers.all())
        return recipients

    def create_inheriting_autosends(self):
        for visitautosend in self.visit.visitautosend_set.all():
            if not self.get_autosend(visitautosend.template_key, False, False):
                occurrenceautosend = VisitOccurrenceAutosend(
                    visitoccurrence=self,
                    inherit=True,
                    template_key=visitautosend.template_key,
                    days=visitautosend.days,
                    enabled=visitautosend.enabled
                )
                occurrenceautosend.save()

    def autosend_inherits(self, template_key):
        s = self.visitoccurrenceautosend_set.\
            filter(template_key=template_key, inherit=True).\
            count() > 0
        return s

    def get_autosend(self, template_key, follow_inherit=True,
                     include_disabled=False):
        if follow_inherit and self.autosend_inherits(template_key):
            return self.visit.get_autosend(template_key)
        else:
            try:
                query = self.visitoccurrenceautosend_set.filter(
                    template_key=template_key)
                if not include_disabled:
                    query = query.filter(enabled=True)
                return query[0]
            except:
                return None

    def autosend_enabled(self, template_key):
        return self.get_autosend(template_key, True) is not None

    # Sends a message to defined recipients pertaining to the VisitOccurrence
    def autosend(self, template_key, recipients=None,
                 only_these_recipients=False):
        if self.autosend_enabled(template_key):
            visit = self.visit
            unit = visit.unit
            if recipients is None:
                recipients = set()
            else:
                recipients = set(recipients)
            if not only_these_recipients:
                recipients.update(self.get_recipients(template_key))

            KUEmailMessage.send_email(
                template_key,
                {'occurrence': self, 'visit': visit},
                list(recipients),
                unit
            )

            if not only_these_recipients and \
                    template_key in \
                    EmailTemplate.booker_keys:
                for booking in self.bookings.all():
                    KUEmailMessage.send_email(
                        template_key,
                        {
                            'occurrence': self,
                            'visit': visit,
                            'booking': booking,
                            'booker': booking.booker
                        },
                        booking.booker,
                        unit
                    )

    def get_autosend_display(self):
        autosends = self.visitoccurrenceautosend_set.filter(enabled=True)
        return ', '.join([autosend.get_name() for autosend in autosends])

    def update_endtime(self):
        if self.start_datetime is not None:
            duration = self.visit.duration_as_timedelta
            if duration is not None:
                self.end_datetime = self.start_datetime + duration

    @staticmethod
    def get_latest_created():
        return VisitOccurrence.objects.\
            order_by('-statistics__created_time')

    @staticmethod
    def get_latest_updated():
        return VisitOccurrence.objects.\
            order_by('-statistics__updated_time')

    @staticmethod
    def get_latest_displayed():
        return VisitOccurrence.objects.\
            order_by('-statistics__visited_time')

    @staticmethod
    def get_latest_booked():
        return VisitOccurrence.objects.filter(
            bookings__isnull=False
        ).order_by(
            '-bookings__statistics__created_time'
        )

    @staticmethod
    def get_todays_occurrences():
        return VisitOccurrence.get_occurring_on_date(datetime.today().date())

    @staticmethod
    def get_starting_on_date(date):
        return VisitOccurrence.objects.filter(
            start_datetime__year=date.year,
            start_datetime__month=date.month,
            start_datetime__day=date.day
        ).order_by('start_datetime')

    @staticmethod
    def get_occurring_at_time(time):
        # Return the occurrences that take place exactly at this time
        # Meaning they begin before the queried time and end after the time
        return VisitOccurrence.objects.filter(
            start_datetime__lte=time,
            end_datetime__gte=time
        )

    @staticmethod
    def get_occurring_on_date(date):
        # An occurrence happens on a date if it starts before the
        # end of the day and ends after the beginning of the day
        return VisitOccurrence.objects.filter(
            start_datetime__lte=date + timedelta(days=1),
            end_datetime__gte=date
        )

    @staticmethod
    def get_recently_held(time=datetime.now()):
        print time
        return VisitOccurrence.objects.filter(
            workflow_status__in=[
                VisitOccurrence.WORKFLOW_STATUS_EXECUTED,
                VisitOccurrence.WORKFLOW_STATUS_EVALUATED],
            start_datetime__isnull=False,
            end_datetime__lte=time
        ).order_by('-end_datetime')

    def ensure_statistics(self):
        if self.statistics is None:
            statistics = ObjectStatistics()
            statistics.save()
            self.statistics = statistics
            self.save()

    @staticmethod
    def set_endtime():
        for occurrence in VisitOccurrence.objects.all():
            occurrence.save()


VisitOccurrence.add_override_property('duration')
VisitOccurrence.add_override_property('locality')


class Autosend(models.Model):
    template_key = models.IntegerField(
        choices=EmailTemplate.key_choices,
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

    def get_name(self):
        return str(EmailTemplate.get_name(self.template_key))

    def __unicode__(self):
        return "[%d] %s (%s)" % (
            self.id,
            self.get_name(),
            "enabled" if self.enabled else "disabled"
        )


class VisitAutosend(Autosend):
    visit = models.ForeignKey(
        Visit,
        verbose_name=_(u'Besøg'),
        blank=False
    )

    def __unicode__(self):
        return "%s on %s" % (
            super(VisitAutosend, self).__unicode__(),
            self.visit.__unicode__()
        )


class VisitOccurrenceAutosend(Autosend):
    visitoccurrence = models.ForeignKey(
        VisitOccurrence,
        verbose_name=_(u'BesøgForekomst'),
        blank=False
    )
    inherit = models.BooleanField(
        verbose_name=_(u'Nedarv fra tilbud')
    )

    def get_inherited(self):
        if self.inherit:
            return self.visitoccurrence.visit.get_autosend(self.template_key)

    def __unicode__(self):
        return "%s on %s" % (
            super(VisitOccurrenceAutosend, self).__unicode__(),
            self.visitoccurrence.__unicode__()
        )


class Room(models.Model):

    class Meta:
        verbose_name = _(u"lokale for tilbud")
        verbose_name_plural = _(u"lokaler for tilbud")

    visit = models.ForeignKey(
        Visit, verbose_name=_(u'Besøg'), blank=False
    )
    name = models.CharField(
        max_length=64, verbose_name=_(u'Navn på lokale'), blank=False
    )

    def __unicode__(self):
        return self.name


# Represents a room as saved on a booking.
class BookedRoom(models.Model):

    class Meta:
        verbose_name = _(u'lokale for besøg')
        verbose_name_plural = _(u'lokaler for besøg')

    name = models.CharField(max_length=60, verbose_name=_(u'Navn'))

    booking = models.ForeignKey(
        'Booking',
        null=False,
        related_name='assigned_rooms'
    )


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
                    print "Unknown region '%s'. May be a typo, please fix in " \
                          "booking/data/postcodes.py" % region_name
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

    name = models.CharField(
        max_length=128,
    )
    postcode = models.ForeignKey(
        PostCode,
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
        from booking.data import schools
        for data, type in [
                (schools.elementary_schools, School.ELEMENTARY_SCHOOL),
                (schools.high_schools, School.GYMNASIE)]:
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
                        School(name=name, postcode=postcode, type=type).save()
                    except PostCode.DoesNotExist:
                        print "Warning: Postcode %d not found in database. " \
                              "Not adding school %s" % (postcode, name)


class Booker(models.Model):

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
        Subject.SUBJECT_TYPE_GRUNDSKOLE: [f1, f2, f3, f4, f5, f6, f7,
                                          f8, f9, f10, other],
        Subject.SUBJECT_TYPE_GYMNASIE: [g1, g2, g3, student, other],
        Subject.SUBJECT_TYPE_BOTH: [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10,
                                    g1, g2, g3, student, other]
    }

    level_choices = (
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

    school = models.ForeignKey(
        School,
        null=True,
        verbose_name=u'Skole'
    )

    attendee_count = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=u'Antal deltagere'
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

    def get_full_email(self):
        return full_email(self.email, self.get_name())


class Booking(models.Model):

    class Meta:
        verbose_name = _(u'booking')
        verbose_name_plural = _(u'bookinger')

    booker = models.ForeignKey(Booker)

    visitoccurrence = models.ForeignKey(
        VisitOccurrence,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name=_(u'Tidspunkt')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=u'Bemærkninger'
    )

    statistics = models.ForeignKey(
        ObjectStatistics,
        null=True
    )

    def get_occurrence_attr(self, attrname):
        if not self.visitoccurrence:
            return None
        return getattr(self.visitoccurrence, attrname, None)

    def raise_readonly_attr_error(self, attrname):
        raise Exception(
            _(u"Attribute %s on Booking is readonly.") % attrname +
            _(u"Set it on the VisitOccurance instead.")
        )

    @classmethod
    # Adds property to this class that will fetch the same attribute on
    # the associated visitoccorrence, if available. The property will raise
    # an exception on assignment.
    def add_occurrence_attr(cls, attrname):
        setattr(cls, attrname, property(
            lambda self: self.get_occurrence_attr(attrname),
            lambda self, val: self.raise_readonly_attr_error(attrname)
        ))

    @classmethod
    def queryset_for_user(cls, user, qs=None):
        if not user or not user.userprofile:
            return Booking.objects.none()

        if qs is None:
            qs = Booking.objects.all()

        return qs.filter(visit__unit=user.userprofile.get_unit_queryset())

    def get_absolute_url(self):
        return reverse('booking-view', args=[self.pk])

    def get_url(self):
        return settings.PUBLIC_URL + self.get_absolute_url()

    def get_recipients(self, template_key):
        recipients = self.visitoccurrence.get_recipients(template_key)
        if template_key in EmailTemplate.booker_keys:
            recipients.append(self.booker)
        return recipients

    def autosend(self, template_key, recipients=None,
                 only_these_recipients=False):
        if self.visitoccurrence.autosend_enabled(template_key):
            visit = self.visitoccurrence.visit
            unit = visit.unit
            if recipients is None:
                recipients = set()
            else:
                recipients = set(recipients)
            if not only_these_recipients:
                recipients.update(self.get_recipients(template_key))

            KUEmailMessage.send_email(
                template_key,
                {
                    'booking': self,
                    'visit': visit,
                    'booker': self.booker
                },
                list(recipients),
                unit
            )

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


Booking.add_occurrence_attr('visit')
Booking.add_occurrence_attr('hosts')
Booking.add_occurrence_attr('teachers')
Booking.add_occurrence_attr('host_status')
Booking.add_occurrence_attr('teacher_status')
Booking.add_occurrence_attr('room_status')
Booking.add_occurrence_attr('workflow_status')
Booking.add_occurrence_attr('comments')


class ClassBooking(Booking):

    class Meta:
        verbose_name = _(u'booking for klassebesøg')
        verbose_name_plural = _(u'bookinger for klassebesøg')

    tour_desired = models.BooleanField(
        verbose_name=u'Rundvisning ønsket'
    )


class TeacherBooking(Booking):

    class Meta:
        verbose_name = _(u'booking for lærerarrangement')
        verbose_name_plural = _(u'bookinger for lærerarrangementer')

    subjects = models.ManyToManyField(Subject)

    def as_searchtext(self):
        result = [super(TeacherBooking, self).as_searchtext()]

        for x in self.subjects.all():
            result.append(x.name)

        return " ".join(result)


class BookingSubjectLevel(models.Model):

    class Meta:
        verbose_name = _('fagniveau for booking')
        verbose_name_plural = _('fagniveauer for bookinger')

    booking = models.ForeignKey(Booking, blank=False, null=False)
    subject = models.ForeignKey(
        Subject, blank=False, null=False,
        limit_choices_to={
            'subject_type__in': [
                Subject.SUBJECT_TYPE_GYMNASIE,
                Subject.SUBJECT_TYPE_BOTH
            ]
        }
    )
    level = models.ForeignKey(GymnasieLevel, blank=False, null=False)

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
    from_email = models.TextField(blank=False, null=False)
    recipients = models.TextField(
        blank=False,
        null=False
    )
    content_type = models.ForeignKey(ContentType, null=True, default=None)
    object_id = models.PositiveIntegerField(null=True, default=None)
    content_object = GenericForeignKey('content_type', 'object_id')

    @staticmethod
    def save_email(email_message, instance):
        """
        :param email_message: An instance of
        django.core.mail.message.EmailMessage
        :param instance: The object that the message concerns i.e. Booking,
        Visit etc.
        :return: None
        """
        ctype = ContentType.objects.get_for_model(instance)
        ku_email_message = KUEmailMessage(
            subject=email_message.subject,
            body=email_message.body,
            from_email=email_message.from_email,
            recipients=', '.join(email_message.recipients()),
            content_type=ctype,
            object_id=instance.id
        )
        ku_email_message.save()

    @staticmethod
    def send_email(template, context, recipients, instance, unit=None,
                   **kwargs):
        if isinstance(template, int):
            template_key = template
            template = EmailTemplate.get_template(template_key, unit)
            if template is None:
                raise Exception(
                    u"Template with name %s does not exist!" % template_key
                )
        if not isinstance(template, EmailTemplate):
            raise Exception(
                u"Invalid template object '%s'" % str(template)
            )

        emails = {}
        if type(recipients) is not list:
            recipients = [recipients]

        for recipient in recipients:
            name = None
            address = None
            if isinstance(recipient, basestring):
                address = recipient
            elif isinstance(recipient, User):
                name = recipient.get_full_name()
                address = recipient.email
            else:
                try:
                    name = recipient.get_name()
                except:
                    pass
                try:
                    address = recipient.get_email()
                except:
                    pass
            if address is not None and address not in emails:
                email = {'address': address}
                if name is not None:
                    email['name'] = name
                    email['full'] = u"\"%s\" <%s>" % (name, address)
                else:
                    email['full'] = address
                emails[address] = email

        for email in emails.values():
            ctx = {
                'unit': unit,
                'recipient': email,
                'sender': settings.DEFAULT_FROM_EMAIL
            }
            ctx.update(context)
            subject = template.expand_subject(ctx)

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
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email['full']]
            )
            if htmlbody is not None:
                message.attach_alternative(htmlbody, 'text/html')
            message.send()

            KUEmailMessage.save_email(message, instance)
