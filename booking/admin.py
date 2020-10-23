# -*- coding: utf-8 -*-

from django.contrib import admin
from django.db import models as django_models
from django.db.models import Q
from django.db.models.fields.related_descriptors import \
    ForwardManyToOneDescriptor

from booking.resource_based import models as resource_models
from userprofile.constants import COORDINATOR, FACULTY_EDITOR, EDIT_ROLES
from . import models as booking_models

EXCLUDE_MODELS = set([
    booking_models.GymnasieLevel,
])

# Important: when changing this, be sure to run the
# following in a shell on the server:
#
# from profile.models import UserProfile
# for userprofile in UserProfile.objects.all():
#     userprofile.update_user_permissions()

CLASSES_BY_ROLE = {}
CLASSES_BY_ROLE[COORDINATOR] = set([
    booking_models.Locality,
    booking_models.Room,
    booking_models.Resource,
    booking_models.RoomResource,
    booking_models.RoomResponsible,
])

CLASSES_BY_ROLE[FACULTY_EDITOR] = set([
    booking_models.OrganizationalUnit,
    booking_models.Booking,
    booking_models.ClassBooking,
    booking_models.TeacherBooking,
    booking_models.Visit,
    booking_models.Product,
    booking_models.Autosend,
    booking_models.VisitAutosend,
    booking_models.ProductAutosend,
    booking_models.EventTime,
    booking_models.BookingGrundskoleSubjectLevel,
    booking_models.BookingGymnasieSubjectLevel,
    booking_models.ProductGymnasieFag,
    booking_models.ProductGrundskoleFag,
    booking_models.SurveyXactEvaluation,
    booking_models.SurveyXactEvaluationGuest,
    booking_models.VisitComment,
    booking_models.ResourceRequirement,
    booking_models.VisitResource
])

# Faculty editors will always have access to the same things as
# coordinators.
CLASSES_BY_ROLE[FACULTY_EDITOR].update(CLASSES_BY_ROLE[COORDINATOR])

# Dict for registering custom admin classes for certain models
CUSTOM_ADMIN_CLASSES = {}

MODEL_UNIT_FILTER_MAP = {
    'Room': 'locality__organizationalunit',
    'Visit': 'eventtime__product__organizationalunit'
}


class KUBookingModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.userprofile.get_role() in EDIT_ROLES

    def has_change_permission(self, request, obj=None):
        if request.user.userprofile.is_administrator:
            return True

        role = request.user.userprofile.get_role()
        if role in CLASSES_BY_ROLE:
            return self.model in CLASSES_BY_ROLE[role]

        return False

    def has_add_permission(self, request):
        return self.has_change_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request)

    def get_queryset(self, request):
        qs = super(KUBookingModelAdmin, self).get_queryset(request)

        if request.user.userprofile.is_administrator:
            return qs

        # Filter anything that has a unit to the units the user has access to
        model_name = self.model._meta.object_name
        unit_filter_match = None
        if hasattr(self.model, 'organizationalunit') and isinstance(
                self.model.organizationalunit,
                ForwardManyToOneDescriptor
        ):
            unit_filter_match = 'organizationalunit'
        elif model_name in MODEL_UNIT_FILTER_MAP:
            unit_filter_match = MODEL_UNIT_FILTER_MAP[model_name]

        if unit_filter_match is not None:
            unit_qs = request.user.userprofile.get_unit_queryset()
            match1 = {"%s__in" % unit_filter_match: unit_qs}
            if getattr(self.model, 'allow_null_unit_editing', False):
                match2 = {unit_filter_match: None}
                qs = qs.filter(Q(**match1) | Q(**match2))
            else:
                qs = qs.filter(**match1)

        return qs

    def get_form(self, request, obj=None, **kwargs):
        form = super(KUBookingModelAdmin, self).get_form(
            request, obj, **kwargs
        )

        if request.user.userprofile.is_administrator:
            return form

        model_name = self.model._meta.object_name
        if hasattr(self.model, 'organizationalunit') and 'organizationalunit' \
                in form.base_fields:
            # Limit choices to the unit the user has access to
            unit_qs = request.user.userprofile.get_unit_queryset()
            form.base_fields['organizationalunit'].queryset = unit_qs

            if not getattr(self.model, 'allow_null_unit_editing', False):
                # Do not allow selecting the blank option
                form.base_fields['organizationalunit'].empty_label = None
        elif model_name in MODEL_UNIT_FILTER_MAP:
            match_str = MODEL_UNIT_FILTER_MAP[model_name]

            (fieldname, match) = match_str.split("__", 1)

            field = form.base_fields[fieldname]
            unit_qs = request.user.userprofile.get_unit_queryset()
            field.queryset = field.queryset.filter(
                **{match: unit_qs}
            )

        return form


class KUBookingUnitAdmin(KUBookingModelAdmin):
    def get_queryset(self, request):
        return request.user.userprofile.get_unit_queryset()

    def get_form(self, request, obj=None, **kwargs):
        form = super(KUBookingUnitAdmin, self).get_form(
            request, obj, **kwargs
        )

        profile = request.user.userprofile

        allowed_parent_types = [u"Fakultet"]

        if profile.is_administrator:
            # Administrators are allowed to select the root as a parent
            allowed_parent_types.append(u"Københavns Universitet")

            # Remove root type choice option unless a root does not exist
            # or we're currently editing an existing one.
            if (
                self.model.root_unit_id() and
                not (
                    obj and obj.type and
                    obj.type.name == u"Københavns Universitet"
                )
            ):
                type_field = form.base_fields['type']
                type_field.queryset = type_field.queryset.exclude(
                    name=u"Københavns Universitet"
                )
        else:
            # All units must have faculty parent
            form.base_fields['parent'].empty_label = None

            # Only allow "Institut" choice
            type_field = form.base_fields['type']
            type_field.queryset = type_field.queryset.filter(
                name=u"Institut"
            )
            type_field.empty_label = None

        # Limit parent choices to types the user has access to
        unit_qs = profile.get_unit_queryset().filter(
            type__name__in=allowed_parent_types
        )

        form.base_fields['parent'].queryset = unit_qs

        return form


CUSTOM_ADMIN_CLASSES[booking_models.OrganizationalUnit] = KUBookingUnitAdmin


class KUBookingRoomResponsibleAdmin(KUBookingModelAdmin):
    list_display = ['__unicode__', 'admin_delete_button']


CUSTOM_ADMIN_CLASSES[booking_models.RoomResponsible] = (
    KUBookingRoomResponsibleAdmin
)


def register_models(models, namespace=None):
    for name, value in models:
        # Skip stuff that is not classes
        if not isinstance(value, type):
            continue

        # Skip stuff that is not models
        if not issubclass(value, django_models.Model):
            continue

        if value._meta.abstract:
            continue

        # Skip stuff that is not native to the booking.models module
        if namespace is not None and not value.__module__ == namespace:
            continue

        if value in EXCLUDE_MODELS:
            continue

        cls = CUSTOM_ADMIN_CLASSES.get(value, KUBookingModelAdmin)
        admin.site.register(value, cls)

register_models(
    booking_models.__dict__.items(),
    'booking.models'
)
register_models(
    resource_models.__dict__.items(),
    'booking.resource_based.models'
)
