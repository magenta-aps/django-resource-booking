# encoding: utf-8
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from recurrence.fields import RecurrenceField
from booking.utils import ClassProperty


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
        (ASSIGNMENT_HELP, _(u"Opgavehjælp")),
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

    # Resource state - created, active and discontinued.
    CREATED = 0
    ACTIVE = 1
    DISCONTINUED = 2

    state_choices = (
        (CREATED, _(u"Oprettet")),
        (ACTIVE, _(u"Aktivt")),
        (DISCONTINUED, _(u"Ophørt"))
    )

    enabled = models.BooleanField(verbose_name=_(u'Aktiv'), default=True)
    type = models.IntegerField(choices=resource_type_choices,
                               default=STUDY_MATERIAL)
    state = models.IntegerField(choices=state_choices, default=CREATED,
                                verbose_name=_(u"Tilstand"))
    title = models.CharField(max_length=60, verbose_name=_(u'Titel'))
    teaser = models.TextField(
        max_length=210,
        blank=True,
        verbose_name=_(u'Teaser')
    )
    description = models.TextField(blank=True, verbose_name=_(u'Beskrivelse'))
    mouseover_description = models.CharField(
        max_length=512, blank=True, verbose_name=_(u'Mouseover-tekst')
    )
    unit = models.ForeignKey(Unit, null=True, blank=True,
                             verbose_name=_('Enhed'))
    links = models.ManyToManyField(Link, blank=True, verbose_name=_('Links'))
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'),
                                   default=AUDIENCE_ALL)

    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY)

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

    # ts_vector field for fulltext search
    search_index = VectorField()

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Tekst-værdier til fritekstsøgning')
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
        return self.title + "(%s)" % str(self.id)

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
            self.title,
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


class ResourceGymnasieFag(models.Model):
    class Meta:
        verbose_name = _(u"Gymnasiefagtilknytning")
        verbose_name_plural = _(u"Gymnasiefagtilknytninger")

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
        verbose_name = _(u"Grundskolefagtilknytning")
        verbose_name_plural = _(u"Grundskolefagtilknytninger")

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

    applicable_types = [Resource.OTHER_OFFERS, Resource.STUDY_MATERIAL,
                        Resource.OPEN_HOUSE, Resource.ASSIGNMENT_HELP,
                        Resource.STUDIEPRAKTIK]

    @ClassProperty
    def type_choices(self):
        return (type for type in
                Resource.resource_type_choices
                if type[0] in OtherResource.applicable_types)

    link = models.URLField(
        verbose_name=u'Link',
        max_length=256,
        blank=True,
        null=True
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

    applicable_types = [Resource.STUDENT_FOR_A_DAY, Resource.GROUP_VISIT,
                        Resource.STUDY_PROJECT, Resource.TEACHER_EVENT]

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

    locality = models.ForeignKey(
        Locality,
        verbose_name=_(u'Lokalitet'),
        blank=True,
        null=True
    )
    duration = models.CharField(
        max_length=8,
        verbose_name=_(u'Varighed'),
        blank=True,
        null=True,
    )
    contact_persons = models.ManyToManyField(
        Person,
        blank=True,
        verbose_name=_(u'Kontaktpersoner')
    )
    do_send_evaluation = models.BooleanField(
        verbose_name=_(u"Udsend evaluering"),
        default=False
    )
    price = models.DecimalField(
        default=0,
        null=True,
        blank=True,
        max_digits=10,
        decimal_places=2,
        verbose_name=_(u'Pris')
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
    preparation_time = models.IntegerField(
        default=0,
        null=True,
        verbose_name=_(u'Forberedelsestid (i timer)')
    )
    recurrences = RecurrenceField(
        null=True,
        blank=True,
        verbose_name=_(u'Gentagelser')
    )
    tour_available = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_(u'Mulighed for rundvisning')
    )

    def save(self, *args, **kwargs):
        # Save once to store relations
        super(Visit, self).save(*args, **kwargs)

        # Update search_text
        self.extra_search_text = self.generate_extra_search_text()

        # Do the final save
        return super(Visit, self).save(*args, **kwargs)

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


class VisitOccurrence(models.Model):
    start_datetime = models.DateTimeField(
        verbose_name=_(u'Starttidspunkt')
    )
    end_datetime1 = models.DateTimeField(
        verbose_name=_(u'Sluttidspunkt')
    )
    end_datetime2 = models.DateTimeField(
        verbose_name=_(u'Alternativt sluttidspunkt'),
        blank=True,
        null=True
    )
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE
    )

    @property
    def display_value(self):
        if not self.start_datetime or not self.end_datetime1:
            return None

        result = self.start_datetime.strftime('%d. %m %Y %H:%M')

        endtime = self.end_datetime2 or self.end_datetime1
        if endtime:
            result += endtime.strftime(' %H:%M')

        return result


class Room(models.Model):
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
    name = models.CharField(max_length=60, verbose_name=_(u'Navn'))

    booking = models.ForeignKey(
        'Booking',
        null=False,
        related_name='assigned_rooms'
    )


class Region(models.Model):
    name = models.CharField(
        max_length=16
    )

    def __unicode__(self):
        return self.name


class PostCode(models.Model):
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


class School(models.Model):
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
                except ObjectDoesNotExist:
                    try:
                        postcode = PostCode.get(postnr)
                        School(name=name, postcode=postcode, type=type).save()
                    except ObjectDoesNotExist:
                        print "Warning: Postcode %d not found in database. " \
                              "Not adding school %s" % (postcode, name)


class Booker(models.Model):
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
    notes = models.TextField(
        blank=True,
        verbose_name=u'Bemærkninger'
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


class Booking(models.Model):
    objects = SearchManager(
        fields=('extra_search_text'),
        config='pg_catalog.danish',
        auto_update_search_field=True
    )

    visit = models.ForeignKey(Visit, null=True)
    booker = models.ForeignKey(Booker)

    # Have to do late import of this here or we will get problems
    # with cyclic dependencies
    from profile.models import TEACHER, HOST

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

    # ts_vector field for fulltext search
    search_index = VectorField()

    # Field for concatenating search data from relations
    extra_search_text = models.TextField(
        blank=True,
        default='',
        verbose_name=_(u'Tekst-værdier til fritekstsøgning'),
        editable=False
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

    WORKFLOW_STATUS_BEING_PLANNED = 0
    WORKFLOW_STATUS_REJECTED = 1
    WORKFLOW_STATUS_PLANNED = 2
    WORKFLOW_STATUS_CONFIRMED = 3
    WORKFLOW_STATUS_REMINDED = 4
    WORKFLOW_STATUS_EXECUTED = 5
    WORKFLOW_STATUS_EVALUATED = 6
    WORKFLOW_STATUS_CANCELLED = 7
    WORKFLOW_STATUS_NOSHOW = 8

    BEING_PLANNED_STATUS_TEXT = u'Under planlægning'
    PLANNED_STATUS_TEXT = u'Planlagt (ressourcer tildelt)'

    workflow_status_choices = (
        (WORKFLOW_STATUS_BEING_PLANNED, _(BEING_PLANNED_STATUS_TEXT)),
        (WORKFLOW_STATUS_REJECTED, _(u'Afvist af undervisere eller værter')),
        (WORKFLOW_STATUS_PLANNED, _(PLANNED_STATUS_TEXT)),
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
        return self.workflow_status == Booking.WORKFLOW_STATUS_BEING_PLANNED

    def planned_status_is_blocked(self):
        # It's not blocked if we can't choose it
        ws_planned = Booking.WORKFLOW_STATUS_PLANNED
        if ws_planned not in (x[0] for x in self.possible_status_choices()):
            return False

        statuses = (self.host_status, self.teacher_status, self.room_status)

        if Booking.STATUS_NOT_ASSIGNED in statuses:
            return True

        return False

    # TODO: Huske at logge status-skift via log_action

    def possible_status_choices(self):
        result = []

        allowed = self.valid_status_changes[self.workflow_status]

        for x in self.workflow_status_choices:
            if x[0] in allowed:
                result.append(x)

        return result

    @classmethod
    def queryset_for_user(cls, user, qs=None):
        if not user or not user.userprofile:
            return Booking.objects.none()

        if qs is None:
            qs = Booking.objects.all()

        return qs.filter(visit__unit=user.userprofile.get_unit_queryset())

    def as_searchtext(self):
        result = []

        if self.visit:
            result.append(self.visit.as_searchtext())

        if self.booker:
            result.append(self.booker.as_searchtext())

        return " ".join(result)

    def save(self, *args, **kwargs):

        # Save once to store relations
        super(Booking, self).save(*args, **kwargs)

        # Update search_text
        self.extra_search_text = self.as_searchtext()

        # Do the final save
        super(Booking, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('booking-view', args=[self.pk])


class ClassBooking(Booking):

    time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=u'Tidspunkt'
    )
    desired_time = models.CharField(
        null=True,
        blank=True,
        max_length=2000,
        verbose_name=u'Ønsket tidspunkt'
    )
    tour_desired = models.BooleanField(
        verbose_name=u'Rundvisning ønsket'
    )


class TeacherBooking(Booking):

    subjects = models.ManyToManyField(Subject)

    def as_searchtext(self):
        result = [super(TeacherBooking, self).as_searchtext()]

        for x in self.subjects.all():
            result.append(x.name)

        return " ".join(result)


class BookingSubjectLevel(models.Model):

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
