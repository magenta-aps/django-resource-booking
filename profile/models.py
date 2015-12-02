# encoding: utf-8
from django.db import models
from django.contrib.auth.models import User as AuthUser
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


class User(AuthUser):
    """Proxy class for User to ensure it's possible to check user's role."""

    class Meta:
        proxy = True

    def has_role(self, role):
        result = False
        if hasattr(self, 'userprofile'):
            result = (self.userprofile.user_role.role == role)
        return result


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
