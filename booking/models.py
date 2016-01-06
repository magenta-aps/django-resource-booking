# encoding: utf-8

from django.db import models
from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.utils.translation import ugettext_lazy as _

from .fields import DurationField


LOGACTION_CREATE = ADDITION
LOGACTION_CHANGE = CHANGE
LOGACTION_DELETE = DELETION
# If we need to add additional values make sure they do not conflict with
# system defined ones by adding 128 to the value.
LOGACTION_CUSTOM1 = 128 + 1
LOGACTION_CUSTOM2 = 128 + 2


def log_action(user, obj, action_flag, change_message=''):
    user_id = user.pk if user else None
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

    # Eventually this could just be a pointer to AD
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=14, null=True, blank=True)

    def __unicode__(self):
        return self.name


# Units (faculties, institutes etc)
class UnitType(models.Model):
    """A type of organization, e.g. 'faculty' """
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    """A generic organizational unit, such as a faculty or an institute"""
    name = models.CharField(max_length=100)
    type = models.ForeignKey(UnitType)
    parent = models.ForeignKey('self', null=True, blank=True)
    contact = models.ForeignKey(Person, null=True, blank=True)

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

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.type.name)


# Master data related to bookable resources start here
class Subject(models.Model):
    """A relevant subject from primary or secondary education."""
    stx = 0
    hf = 1
    htx = 2
    eux = 3
    valgfag = 4

    line_choices = (
        (stx, _(u'stx')),
        (hf, _(u'hf')),
        (htx, _(u'htx')),
        (eux, _(u'eux')),
        (valgfag, _(u'valgfag')),
    )

    name = models.CharField(max_length=256)
    line = models.IntegerField(choices=line_choices, verbose_name=u'Linje',
                               blank=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


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
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class AdditionalService(models.Model):
    """Additional services, i.e. tour of the place, food and drink, etc."""
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class SpecialRequirement(models.Model):
    """Special requirements for visit - e.g., driver's license."""
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class StudyMaterial(models.Model):
    """Material for the students to study before visiting."""
    URL = 0
    ATTACHMENT = 1
    study_material_choices = (
        (URL, _(u"URL")),
        (ATTACHMENT, _(u"Vedhæftet fil"))
    )
    type = models.IntegerField(choices=study_material_choices, default=URL)
    url = models.URLField(null=True, blank=True)
    file = models.FileField(upload_to='material', null=True, blank=True)
    visit = models.ForeignKey('Visit', on_delete=models.CASCADE)

    def __unicode__(self):
        s = u"{0}: {1}".format(
            u'URL' if self.type == self.URL else _(u"Vedhæftet fil"),
            self.url if self.type == self.URL else self.file
        )
        return s


class Locality(models.Model):
    """A locality where a visit may take place."""
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


# Bookable resources
class Resource(models.Model):
    """Abstract superclass for a bookable resource of any kind."""

    # Resource type.
    STUDENT_FOR_A_DAY = 0
    FIXED_SCHEDULE_GROUP_VISIT = 1
    FREELY_SCHEDULED_GROUP_VISIT = 2
    STUDY_PROJECT = 3
    SINGLE_EVENT = 4
    OTHER_RESOURCES = 5

    resource_type_choices = (
        (STUDENT_FOR_A_DAY, _(u"Studerende for en dag")),
        (FIXED_SCHEDULE_GROUP_VISIT, _(u"Gruppebesøg med faste tider")),
        (FREELY_SCHEDULED_GROUP_VISIT, _(u"Gruppebesøg uden faste tider")),
        (STUDY_PROJECT, _(u"Studieretningsprojekt - SRP")),
        (SINGLE_EVENT,  _(u"Enkeltstående event")),
        (OTHER_RESOURCES, _(u"Andre tilbud"))
    )

    # Target audience choice - student or teacher.
    TEACHER = 0
    STUDENT = 1

    audience_choices = (
        (TEACHER, _(u'Lærer')),
        (STUDENT, _(u'Elev'))
    )

    # Institution choice - primary or secondary school.
    PRIMARY = 0
    SECONDARY = 1

    institution_choices = (
        (PRIMARY, _(u'Grundskole')),
        (SECONDARY, _(u'Gymnasium'))
    )

    # Level choices - A, B or C
    A = 0
    B = 0
    C = 0

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

    enabled = models.BooleanField(verbose_name=_(u'Aktiv'), default=True)
    type = models.IntegerField(choices=resource_type_choices,
                               default=OTHER_RESOURCES)
    state = models.IntegerField(choices=state_choices, default=CREATED,
                                verbose_name=_(u"Tilstand"))
    title = models.CharField(max_length=256, verbose_name=_(u'Titel'))
    teaser = models.TextField(blank=True, verbose_name=_(u'Teaser'))
    description = models.TextField(blank=True, verbose_name=_(u'Beskrivelse'))
    mouseover_description = models.CharField(
        max_length=512, blank=True, verbose_name=_(u'Mouseover-tekst')
    )
    unit = models.ForeignKey(Unit, null=True, blank=True,
                             verbose_name=_('Enhed'))
    links = models.ManyToManyField(Link, blank=True, verbose_name=_('Links'))
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'),
                                   default=TEACHER)
    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY)
    subjects = models.ManyToManyField(Subject, blank=True,
                                      verbose_name=_(u'Fag'))
    level = models.IntegerField(choices=level_choices,
                                verbose_name=_(u"Niveau"),
                                blank=True,
                                null=True)
    # TODO: We should validate that min <= max here.
    class_level_min = models.IntegerField(choices=class_level_choices,
                                          default=0,
                                          verbose_name=_(u'Klassetrin fra'))
    class_level_max = models.IntegerField(choices=class_level_choices,
                                          default=10,
                                          verbose_name=_(u'Klassetrin til'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_(u'Tags'))
    topics = models.ManyToManyField(
        Topic, blank=True, verbose_name=_(u'Emner')
    )

    # Comment field for internal use in backend.
    comment = models.TextField(blank=True, verbose_name=_(u'Kommentar'))

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
            'description',
            'mouseover_description',
            'extra_search_text'
        ),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    def __unicode__(self):
        return self.title

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

        # Name of all subjects
        for s in self.subjects.all():
            texts.append(s.name)

        # Display-value for level
        texts.append(self.get_level_display() or "")

        # Name of all tags
        for t in self.tags.all():
            texts.append(t.name)

        # Name of all topocs
        for t in self.topics.all():
            texts.append(t.name)

        return "\n".join(texts)


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

    def save(self, *args, **kwargs):
        # Save once to store relations
        super(OtherResource, self).save(*args, **kwargs)

        # Update search_text
        self.extra_search_text = self.generate_extra_search_text()

        # Do the final save
        return super(OtherResource, self).save(*args, **kwargs)


class Visit(Resource):
    """A bookable visit of any kind."""
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
        choices=rooms_assignment_choices, default=ROOMS_ASSIGNED_ON_VISIT,
        verbose_name=_(u"Tildeling af lokale(r)")
    )

    locality = models.ForeignKey(
        Locality, verbose_name=_(u'Lokalitet'), blank=True
    )
    time = models.DateTimeField(
        verbose_name=_(u'Tid')
    )
    duration = DurationField(
        verbose_name=_(u'Varighed'),
        blank=True,
        null=True,
        labels={'day': _(u'Dage:'), 'hour': _(u'Timer:'),
                'minute': _(u'Minutter:')}
    )
    contact_persons = models.ManyToManyField(
        Person,
        blank=True,
        verbose_name=_(u'Kontaktpersoner')
    )
    do_send_evaluation = models.BooleanField(
        verbose_name=_(u"Udsend evaluering"), default=False
    )
    price = models.DecimalField(default=0, max_digits=10, decimal_places=2,
                                verbose_name=_(u'Pris'))
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
    is_group_visit = models.BooleanField(default=True,
                                         verbose_name=_(u'Gruppebesøg'))
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
    preparation_time = models.IntegerField(
        default=0,
        verbose_name=_(u'Forberedelsestid (i timer)')
    )

    def save(self, *args, **kwargs):
        # Save once to store relations
        super(Visit, self).save(*args, **kwargs)

        # Update search_text
        self.extra_search_text = self.generate_extra_search_text()

        # Do the final save
        return super(Visit, self).save(*args, **kwargs)


class Room(models.Model):
    visit = models.ForeignKey(
        Visit, verbose_name=_(u'Besøg'), blank=False
    )
    name = models.CharField(
        max_length=64, verbose_name=_(u'Navn på lokale'), blank=False
    )

    def __unicode__(self):
        return self.name
