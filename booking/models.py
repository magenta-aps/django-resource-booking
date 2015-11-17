# encoding: utf-8

from django.db import models
from django.utils.translation import ugettext_lazy as _


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
    # unit = models.ForeignKey(unit)
    audience = models.IntegerField(choices=audience_choices,
                                   verbose_name=_(u'Målgruppe'))
    institution_level = models.IntegerField(choices=institution_choices,
                                            verbose_name=_(u'Institution'))
    # TODO: Level and subjects are still to be defined
    # level = <<suitable choice list for levels>>
    # subjects = << Suitable link to yet-to-be-defined Subject class >>

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

