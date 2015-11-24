# encoding: utf-8

from django.db import models
from django.utils.translation import ugettext_lazy as _


class UnitType(models.Model):
    """A type of organization, e.g. 'faculty' """
    name = models.CharField(max_length=20)


class Unit(models.Model):
    """A generic organizational unit, such as a faculty or an institute"""
    name = models.CharField(max_length=30)
    type = models.ForeignKey(UnitType)
    parent = models.ForeignKey('self', null=True, blank=True)


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
                               blank=True, null=True)
    description = models.TextField()


class Link(models.Model):
    """"An URL and relevant metadata."""
    url = models.URLField()
    name = models.CharField(max_length=256)
    # Note: "description" is intended as automatic text when linking in web
    # pages.
    description = models.CharField(max_length=256)


class Topic(models.Model):
    """Tag class, just name and description fields."""
    name = models.CharField(max_length=256)
    description = models.TextField()


class AdditionalService(models.Model):
    """Additional services, i.e. tour of the place, food and drink, etc."""
    name = models.CharField(max_length=256)
    description = models.TextField()


class SpecialRequirement(models.Model):
    """Special requirements for visit - e.g., driver's license."""
    name = models.CharField(max_length=256)
    description = models.TextField()


# Bookable resources
class Resource(models.Model):
    """A bookable resource of any kind."""

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
        (A, u'a'), (B, u'B'), (C, u'C')
    )

    type = models.IntegerField(choices=resource_type_choices)
    title = models.CharField(max_length=256)
    description = models.TextField()
    mouseover_description = models.CharField(max_length=512)
    unit = models.ForeignKey(Unit, null=True, blank=True)
    links = models.ManyToManyField(Link)
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'))
    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY)
    subjects = models.ManyToManyField(Subject)
    level = models.IntegerField(choices=level_choices,
                                verbose_name=_(u"Niveau"))
    # tags = <<choice list for tags>>
    topics = models.ManyToManyField(Topic)

    # Comment field for internal use in backend.
    comment = models.TextField()


class Visit(Resource):
    """A bookable visit of any kind."""
    # locality = <<suitable representation of locality.>>
    # room = <<representation of roomm, maybe free text field.>>
    do_send_evaluation = models.BooleanField(
        verbose_name=_(u"Udsend evaluering"), default=False
    )
    price = models.DecimalField(default=0)
    additional_services = models.ManyToManyField(AdditionalService)
    special_requirements = models.ManyToManyField(SpecialRequirement)
    is_group_visit = models.BooleanField(default=True)
    # Min/max number of visitors - only relevant for group visits.
    mininimum_number_of_visitors = models.IntegerField(null=True, blank=True)
    maximum_number_of_visitors = models.IntegerField(null=True, blank=True)
    do_create_waiting_list = models.BooleanField(default=False)
    do_show_countdown = models.BooleanField(default=False)
    # preparatory_material = <<< ... >>>
