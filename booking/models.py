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


class Resource(models.Model):
    """A bookable resource of any kind."""

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
        (PRIMARY, _(u'Folkeskole')),
        (SECONDARY, _(u'Gymnasium'))
    )

    title = models.CharField(max_length=256)
    description = models.TextField()
    mouseover_description = models.CharField(max_length=512)
    unit = models.ForeignKey(Unit, null=True, blank=True)
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'))
    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'),
                                            default=SECONDARY)
    subjects = models.ManyToManyField(Subject)
    # level = <<suitable choice list for levels>>
    # class_year = <<suitable representation, maybe free text.>>
    # tags = <<choice list for tags>>
    # topics = <<choice list for topics>>

    # Comment field for internal use in backend.
    comment = models.TextField()


class Visit(Resource):
    """A bookable visit of any kind."""

    # Visit type choice - TBS
    # TODO: Find out what types we want here!
    VISIT_TYPE_1 = 0
    VISIT_TYPE_2 = 1

    visit_type_choices = (
        (VISIT_TYPE_1, _("Type 1")),
        (VISIT_TYPE_2, _("Type 2"))
    )

#
# Units (faculties, institutes etc)
#

