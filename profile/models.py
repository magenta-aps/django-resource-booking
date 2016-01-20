# encoding: utf-8
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from booking.models import Unit


# User roles

TEACHER = 0
HOST = 1
COORDINATOR = 2
ADMINISTRATOR = 3

user_role_choices = (
    (TEACHER, _(u"Underviser")),
    (HOST, _(u"Vært")),
    (COORDINATOR, _(u"Koordinator")),
    (ADMINISTRATOR, _(u"Administrator"))
)


def role_to_text(role):
    """Return text representation of role code."""
    for r, t in user_role_choices:
        if r == role:
            return unicode(t)
    return ""


class UserRole(models.Model):
    """"Superadmin, administrator, teacher, etc."""
    role = models.IntegerField(
        null=False,
        choices=user_role_choices,
        default=TEACHER
    )
    name = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class UserProfile(models.Model):
    """User profile associated with each user."""
    user = models.OneToOneField(User)
    user_role = models.ForeignKey(UserRole)
    # Unit must always be specified for coordinators,
    # possibly also for teachers and hosts.
    # Unit is not needed for administrators.
    unit = models.ForeignKey(Unit, null=True, blank=True)

    def __unicode__(self):
        return self.user.username

    def get_role(self):
        """Return the role code, i.e. TEACHER, HOST, etc."""
        return self.user_role.role

    def can_create(self):
        return self.get_role() in (COORDINATOR, ADMINISTRATOR)

    def can_edit(self, item):
        role = self.get_role()

        # Administrators can always edit
        if role == ADMINISTRATOR:
            return True

        # Coordinators can only edit stuff that belongs to their unit
        if role == COORDINATOR:
            if not self.unit or not item.unit:
                return False

            if item.unit.belongs_to(self.unit):
                return True

        return False
