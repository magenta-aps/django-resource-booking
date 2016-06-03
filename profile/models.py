# encoding: utf-8
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Aggregate
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
import booking.models
from booking.models import Unit, Resource, UserPerson
from booking.utils import get_related_content_types
import uuid

# User roles

TEACHER = 0
HOST = 1
COORDINATOR = 2
ADMINISTRATOR = 3
FACULTY_EDITOR = 4
NONE = 5

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
    (FACULTY_EDITOR, _(u"Fakultetsredaktør")),
    (NONE, _(u"Ingen"))
)

# Which roles are available for editing?
# E.g. a faculty editor can create, edit and delete coordinators but not admins
available_roles = {
    NONE: [],
    TEACHER: [],
    HOST: [],
    COORDINATOR: [NONE, TEACHER, HOST],
    FACULTY_EDITOR: [NONE, TEACHER, HOST, COORDINATOR],
    ADMINISTRATOR: [
        NONE, TEACHER, HOST, COORDINATOR, FACULTY_EDITOR, ADMINISTRATOR
    ]
}


def get_none_role():
    try:
        userrole = UserRole.objects.get(role=NONE)
    except UserRole.DoesNotExist:
        userrole = UserRole(
            role=NONE,
            name=role_to_text(NONE)
        )
        userrole.save()

    return userrole


def get_public_web_user():
    try:
        user = User.objects.get(username="public_web_user")
    except User.DoesNotExist:
        user = User.objects.create_user("public_web_user")
        profile = UserProfile(
            user=user,
            unit=None,
            user_role=get_none_role()
        )
        profile.save()

    return user


def role_to_text(role):
    """Return text representation of role code."""
    for r, t in user_role_choices:
        if r == role:
            return unicode(t)
    return ""


class AbsDateDist(Aggregate):
    template = 'ABS(EXTRACT(EPOCH FROM (%(expressions)s)))'

    def __init__(self, expression, **extra):

        super(AbsDateDist, self).__init__(
            expression,
            output_field=models.IntegerField(),
            **extra)


class UserRole(models.Model):
    """"Superadmin, administrator, teacher, etc."""

    class Meta:
        verbose_name = _(u'brugerrolle')
        verbose_name_plural = _(u'brugerroller')

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

    my_resources = models.ManyToManyField(
        Resource,
        blank=True,
        verbose_name=_(u"Mine tilbud")
    )

    availability_text = models.TextField(
        verbose_name=_(u"Mulige tidspunkter for vært/underviser"),
        blank=True,
        default=""
    )

    additional_information = models.TextField(
        verbose_name=_(u"Yderligere information"),
        blank=True,
        default=""
    )

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

    @property
    def is_host(self):
        return self.get_role() == HOST

    @property
    def is_teacher(self):
        return self.get_role() == TEACHER

    @property
    def is_coordinator(self):
        return self.get_role() == COORDINATOR

    @property
    def is_faculty_editor(self):
        return self.get_role() == FACULTY_EDITOR

    @property
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

    def can_edit_units(self):
        return self.get_role() in (ADMINISTRATOR, FACULTY_EDITOR)

    def get_unit_queryset(self):
        role = self.get_role()

        if role is None:
            return Unit.objects.none()

        if role == ADMINISTRATOR:
            return Unit.objects.all()

        unit = self.unit

        if not unit:
            return Unit.objects.none()

        # Faculty editors gets everything that has their unit as a parent
        # as well as the unit itself
        if role == FACULTY_EDITOR:
            return Unit.objects.filter(Q(parent=unit) | Q(pk=unit.pk))

        # Everyone else just get access to their own group
        return Unit.objects.filter(pk=unit.pk)

    def get_faculty(self):
        unit = self.unit

        while unit and unit.type.name != "Fakultet":
            unit = unit.parent

        return unit

    def get_admins(self):
        return User.objects.filter(
            userprofile__user_role__role=ADMINISTRATOR
        )

    def get_faculty_admins(self):
        faculty = self.get_faculty()

        if faculty:
            return User.objects.filter(
                userprofile__user_role__role=FACULTY_EDITOR,
                userprofile__unit=faculty
            )
        else:
            return User.objects.none()

    def requested_as_teacher_for_qs(self, exclude_accepted=False):
        bm = booking.models
        cts = get_related_content_types(bm.VisitOccurrence)
        template_key = bm.EmailTemplate.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER

        mail_qs = bm.KUEmailRecipient.objects.filter(
            user=self.user,
            email_message__template_key=template_key,
            email_message__content_type__in=cts,
        )

        if exclude_accepted:
            accepted_qs = self.user.taught_visitoccurrences.all()
            mail_qs = mail_qs.exclude(email_message__object_id__in=accepted_qs)

        qs = bm.VisitOccurrence.objects.filter(
            pk__in=mail_qs.values_list("email_message__object_id", flat=True)
        )

        return qs

    def is_available_as_teacher(self, from_datetime, to_datetime):
        return not self.taught_visitoccurrences.filter(
            start_datetime__lt=to_datetime,
            end_datetime__gt=from_datetime
        ).exists()

    def can_be_teacher_for(self, visit_occurrence):
        return self.is_available_as_teacher(
            visit_occurrence.start_datetime,
            visit_occurrence.end_datetime
        )

    def requested_as_host_for_qs(self, exclude_accepted=False):
        bm = booking.models
        cts = get_related_content_types(bm.VisitOccurrence)
        template_key = bm.EmailTemplate.NOTIFY_HOST__REQ_HOST_VOLUNTEER

        mail_qs = bm.KUEmailRecipient.objects.filter(
            user=self.user,
            email_message__template_key=template_key,
            email_message__content_type__in=cts,
        )

        if exclude_accepted:
            accepted_qs = self.user.hosted_visitoccurrences.all()
            mail_qs = mail_qs.exclude(email_message__object_id__in=accepted_qs)

        qs = bm.VisitOccurrence.objects.filter(
            pk__in=mail_qs.values_list("email_message__object_id", flat=True)
        )

        return qs

    def is_available_as_host(self, from_datetime, to_datetime):
        return not self.hosted_visitoccurrences.filter(
            Q(
                end_datetime__isnull=True,
                start_datetime__lt=to_datetime,
                start_datetime__gt=from_datetime
            ) | Q(
                start_datetime__lt=to_datetime,
                end_datetime__gt=from_datetime
            )
        ).exists()

    def can_be_host_for(self, visit_occurrence):
        return self.is_available_as_host(
            visit_occurrence.start_datetime,
            visit_occurrence.end_datetime
        )

    @property
    def available_roles(self):
        return available_roles[self.get_role()]

    def save(self, *args, **kwargs):
        result = super(UserProfile, self).save(*args, **kwargs)

        if self.user and not self.user.userperson_set.exists():
            UserPerson.create(self.user)

        return result


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
