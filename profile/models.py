# encoding: utf-8
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Aggregate
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import booking.models

from booking.models import OrganizationalUnit, Product
from booking.utils import get_related_content_types

# User roles
from profile.constants import TEACHER, HOST, COORDINATOR, ADMINISTRATOR
from profile.constants import FACULTY_EDITOR, NONE
from profile.constants import EDIT_ROLES, user_role_choices, available_roles

import uuid


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
            organizationalunit=None,
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
    template = (
        "ABS(EXTRACT(EPOCH FROM MAX(%(expressions)s)) - " +
        "EXTRACT(EPOCH FROM STATEMENT_TIMESTAMP()))"
    )
    name = "AbsDateDist"

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
    organizationalunit = models.ForeignKey(
        OrganizationalUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    my_resources = models.ManyToManyField(
        Product,
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
        role = self.get_role()
        if role == ADMINISTRATOR:
            return True

        if item is not None:
            if not hasattr(item, "organizationalunit") \
                    or not item.organizationalunit:
                return False

            if role in EDIT_ROLES:
                qs = self.get_unit_queryset().filter(
                    pk=item.organizationalunit.pk
                )
                return len(qs) > 0

        return False

    def can_edit(self, item):
        role = self.get_role()

        if role == ADMINISTRATOR:
            return True

        if not hasattr(item, "organizationalunit") or not \
                item.organizationalunit:
            return False

        if role in EDIT_ROLES:
            qs = self.get_unit_queryset().filter(pk=item.organizationalunit.pk)
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
            return OrganizationalUnit.objects.none()

        if role == ADMINISTRATOR:
            return OrganizationalUnit.objects.all()

        unit = self.organizationalunit

        if not unit:
            return OrganizationalUnit.objects.none()

        # Faculty editors gets everything that has their unit as a parent
        # as well as the unit itself
        if role == FACULTY_EDITOR:
            return OrganizationalUnit.objects.filter(Q(parent=unit) |
                                                     Q(pk=unit.pk))

        # Everyone else just get access to their own group
        return OrganizationalUnit.objects.filter(pk=unit.pk)

    def get_faculty(self):
        unit = self.organizationalunit

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
                userprofile__organizationalunit=faculty
            )
        else:
            return User.objects.none()

    def requested_as_teacher_for_qs(self, exclude_accepted=False):
        bm = booking.models
        cts = get_related_content_types(bm.Visit)
        template_key = bm.EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER

        mail_qs = bm.KUEmailRecipient.objects.filter(
            user=self.user,
            email_message__template_key=template_key,
            email_message__content_type__in=cts,
        )

        if exclude_accepted:
            accepted_qs = self.user.taught_visits.all()
            mail_qs = mail_qs.exclude(email_message__object_id__in=accepted_qs)

        qs = bm.Visit.objects.filter(
            pk__in=mail_qs.values_list("email_message__object_id", flat=True)
        )

        return qs

    def get_resource(self):
        role = self.get_role()
        if role == TEACHER:
            return booking.models.TeacherResource.objects.filter(
                user=self.user
            ).first()
        elif role == HOST:
            return booking.models.HostResource.objects.filter(
                user=self.user
            ).first()
        else:
            return None

    def is_available_as_teacher(self, from_datetime, to_datetime):
        res = self.get_resource()
        if res:
            return res.is_available_between(from_datetime, to_datetime)

        return not self.user.taught_visits.filter(
            eventtime__start__lt=to_datetime,
            eventtime__end__gt=from_datetime
        ).exists()

    def can_be_teacher_for(self, visit):
        return self.is_available_as_teacher(
            visit.eventtime.start,
            visit.eventtime.end
        )

    def requested_as_host_for_qs(self, exclude_accepted=False):
        bm = booking.models
        cts = get_related_content_types(bm.Visit)
        template_key = bm.EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER

        mail_qs = bm.KUEmailRecipient.objects.filter(
            user=self.user,
            email_message__template_key=template_key,
            email_message__content_type__in=cts,
        )

        if exclude_accepted:
            accepted_qs = self.user.hosted_visits.all()
            mail_qs = mail_qs.exclude(email_message__object_id__in=accepted_qs)

        qs = bm.Visit.objects.filter(
            pk__in=mail_qs.values_list("email_message__object_id", flat=True)
        )

        return qs

    def is_available_as_host(self, from_datetime, to_datetime):
        res = self.get_resource()
        if res:
            return res.is_available_between(from_datetime, to_datetime)

        return not self.user.hosted_visits.filter(
            Q(
                eventtime__start__lt=to_datetime,
                eventtime__end__gt=from_datetime
            )
        ).exists()

    def can_be_host_for(self, visit):
        return self.is_available_as_host(
            visit.start_datetime,
            visit.end_datetime
        )

    @property
    def assigned_to_visits(self):
        role = self.get_role()
        if role == TEACHER:
            return self.user.taught_visits.all()
        elif role == HOST:
            return self.user.hosted_visits.all()
        else:
            return booking.models.Visit.objects.none()

    @property
    def resource_for_visits(self):
        res = self.get_resource()
        if res:
            return booking.models.Visit.objects.filter(
                resources=res
            )
        else:
            return booking.models.Visit.objects.none()

    def all_assigned_visits(self):
        qs = self.assigned_to_visits | self.resource_for_visits
        return qs

    @property
    def available_roles(self):
        return available_roles[self.get_role()]

    @property
    def can_be_assigned_to_qs(self):
        resource = self.get_resource()
        if resource:
            qs1 = booking.models.Visit.objects.raw('''
                SELECT DISTINCT
                    "booking_visit"."id"
                FROM
                    "booking_visit"
                    INNER JOIN "booking_eventtime" ON (
                        "booking_visit"."id" = "booking_eventtime"."visit_id"
                    )
                    INNER JOIN "booking_product" ON (
                        "booking_eventtime"."product_id" =
                            "booking_product"."id"
                    )
                    INNER JOIN "booking_resourcerequirement" ON (
                        "booking_product"."id" =
                            "booking_resourcerequirement"."product_id"
                    )
                    INNER JOIN "booking_resourcepool" ON (
                        "booking_resourcerequirement"."resource_pool_id" =
                            "booking_resourcepool"."id"
                    )
                    INNER JOIN "booking_resourcepool_resources" ON (
                        "booking_resourcepool"."id" =
                        "booking_resourcepool_resources"."resourcepool_id"
                    )
                    LEFT OUTER JOIN "booking_visitresource" ON (
                        "booking_visit"."id" =
                            "booking_visitresource"."visit_id"
                        AND
                        "booking_visitresource"."resource_requirement_id" =
                            "booking_resourcerequirement"."id"
                    )
                    LEFT OUTER JOIN "booking_visitresource" "vr2" ON (
                        "booking_visit"."id" = "vr2"."visit_id"
                        AND
                        "vr2"."resource_requirement_id" =
                            "booking_resourcerequirement"."id"
                        AND
                        "vr2"."resource_id" = %s
                    )
                WHERE (
                    "booking_resourcepool_resources"."resource_id" = %s
                    AND
                    "vr2"."id" IS NULL
                    AND
                    "booking_eventtime"."start" > %s
                )
                GROUP BY
                    "booking_visit"."id",
                    "booking_resourcerequirement"."id"
                HAVING
                    COUNT("booking_visitresource"."id") <
                        "booking_resourcerequirement"."required_amount"
            ''', [resource.pk, resource.pk, timezone.now()])
            # Turn it into a Django query
            qs1 = booking.models.Visit.objects.filter(
                pk__in=[x.pk for x in qs1],
                is_multi_sub=False
            )
        else:
            qs1 = booking.models.Visit.objects.none()

        unit_qs = self.get_unit_queryset()

        if self.is_teacher:
            qs2 = booking.models.Visit.objects.annotate(
                num_assigned=Count('teachers')
            ).filter(
                eventtime__product__time_mode=Product.TIME_MODE_SPECIFIC,
                eventtime__start__gt=timezone.now(),
                eventtime__product__organizationalunit=unit_qs,
                num_assigned__lt=Coalesce(
                    'override_needed_teachers',
                    'eventtime__product__needed_teachers'
                ),
                is_multi_sub=False
            ).exclude(
                teachers=self.user
            )
        elif self.is_host:
            qs2 = booking.models.Visit.objects.annotate(
                num_assigned=Count('hosts')
            ).filter(
                eventtime__product__time_mode=Product.TIME_MODE_SPECIFIC,
                eventtime__start__gt=timezone.now(),
                eventtime__product__organizationalunit=unit_qs,
                num_assigned__lt=Coalesce(
                    'override_needed_hosts',
                    'eventtime__product__needed_hosts'
                ),
                is_multi_sub=False
            ).exclude(
                hosts=self.user
            )
        else:
            qs2 = booking.models.Visit.objects.none()

        return qs1 | qs2

    @property
    def potentially_assigned_visits(self):
        resource = self.get_resource()
        if resource:
            qs = booking.models.Visit.objects.filter(**{
                ('eventtime__product__resourcerequirement__' +
                 'resource_pool__resources'): resource
            })
        else:
            qs = booking.models.Visit.objects.none()

        if self.is_teacher:
            qs = qs | booking.models.Visit.objects.filter(
                eventtime__product__potentielle_undervisere=self.user
            )
        elif self.is_host:
            qs = qs | booking.models.Visit.objects.filter(
                eventtime__product__potentielle_vaerter=self.user
            )

        return qs

    def save(self, *args, **kwargs):

        result = super(UserProfile, self).save(*args, **kwargs)

        # Create a resource for the user
        if self.is_teacher and self.organizationalunit:
            if self.user.teacherresource_set.exists():
                resource = self.user.teacherresource_set.first()
                resource.organizationalunit = self.organizationalunit
            else:
                resource = booking.models.TeacherResource(
                    user=self.user,
                    organizationalunit=self.organizationalunit
                )
                resource.make_calendar()
            resource.save()

        # Create a resource for the user
        if self.is_host and self.organizationalunit:
            if self.user.hostresource_set.exists():
                resource = self.user.hostresource_set.first()
                resource.organizationalunit = self.organizationalunit
            else:
                resource = booking.models.HostResource(
                    user=self.user,
                    organizationalunit=self.organizationalunit
                )
                resource.make_calendar()
            resource.save()

        return result


class EmailLoginURL(models.Model):
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
