# encoding: utf-8
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from booking.models import Unit
import uuid

# User roles

TEACHER = 0
HOST = 1
COORDINATOR = 2
ADMINISTRATOR = 3
FACULTY_EDITOR = 4

EDIT_ROLES = set([
    ADMINISTRATOR,
    FACULTY_EDITOR,
    COORDINATOR
])

user_role_choices = (
    (TEACHER, _(u"Underviser")),
    (HOST, _(u"Vært")),
    (COORDINATOR, _(u"Koordinator")),
    (ADMINISTRATOR, _(u"Administrator")),
    (FACULTY_EDITOR, _(u"Fakultetsredaktør"))
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

    def get_role_name(self):
        return self.user_role.name

    def can_create(self):
        return self.has_edit_role()

    def has_edit_role(self):
        return self.get_role() in EDIT_ROLES

    def is_administrator(self):
        return self.get_role() == ADMINISTRATOR

    def can_notify(self, item=None):
        # Return whether the user can send email notifications
        # (for the given item)
        return self.get_role() in EDIT_ROLES

    def can_edit(self, item):
        role = self.get_role()

        if role == ADMINISTRATOR:
            return True

        if not hasattr(item, "unit") or not item.unit:
            return False

        if role in EDIT_ROLES:
            qs = self.get_unit_queryset().filter(pk=item.unit.pk)
            return len(qs) > 0

        return False

    def unit_access(self, unit):
        role = self.get_role()

        if role == ADMINISTRATOR:
            return True

        if role in EDIT_ROLES:
            qs = self.get_unit_queryset().filter(pk=unit.pk)
            return len(qs) > 0

        return False

    def get_unit_queryset(self):
        role = self.get_role()

        if not role:
            return Unit.objects.none()

        if role == ADMINISTRATOR:
            return Unit.objects.all()

        unit = self.unit

        if not unit:
            return Unit.objects.none()

        # Faculty editos gets everything that has their unit as a parent
        # as well as the unit itself
        if role == FACULTY_EDITOR:
            return Unit.objects.filter(Q(parent=unit) | Q(pk=unit.pk))

        # Everyone else just get access to their own group
        return Unit.objects.filter(pk=unit.pk)


class EmailLoginEntry(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    success_url = models.CharField(max_length=2024)
    user = models.ForeignKey(User)
    created = models.DateTimeField(default=timezone.now)
    expires_in = models.DurationField(default=timedelta(hours=48))

    def as_url(self):
        return reverse('email-login', args=[self.uuid, self.success_url])

    def as_full_url(self, request):
        return request.build_absolute_uri(self.as_url())

    def as_public_url(self):
        return settings.PUBLIC_URL + self.as_url()

    def is_expired(self):
        return (self.created + self.expires_in) < timezone.now()

    def __unicode__(self):
        return unicode(self.as_public_url())

    @classmethod
    def create_from_url(cls, user, url, **kwargs):
        attrs = {
            'user': user,
            'success_url': url,
        }
        attrs.update(kwargs)

        return cls.objects.create(**attrs)

    @classmethod
    def create_from_reverse(cls, user, rev_tag, *args, **kwargs):
        if len(args) > 0:
            url = reverse(rev_tag, args=args)
        else:
            url = reverse(rev_tag)

        return cls.create_from_url(user, url, **kwargs)
