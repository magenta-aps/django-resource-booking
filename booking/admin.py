from django.contrib import admin
from django.db import models as django_models
from django.db.models import Q

from . import models as booking_models
from profile.models import COORDINATOR, FACULTY_EDITOR, EDIT_ROLES

EXCLUDE_MODELS = set([
    booking_models.Resource,
    booking_models.GymnasieLevel,
])

CLASSES_BY_ROLE = {}
CLASSES_BY_ROLE[COORDINATOR] = set([
    booking_models.Locality,
    booking_models.Person,
])

CLASSES_BY_ROLE[FACULTY_EDITOR] = set([
    booking_models.Unit
])

# Faculty editors will always have access to the same things as
# coordinators.
CLASSES_BY_ROLE[FACULTY_EDITOR].update(CLASSES_BY_ROLE[COORDINATOR])

# Dict for registering custom admin classes for certain models
CUSTOM_ADMIN_CLASSES = {}


class KUBookingModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.userprofile.get_role() in EDIT_ROLES

    def has_change_permission(self, request, obj=None):
        if request.user.userprofile.is_administrator():
            return True

        role = request.user.userprofile.get_role()
        print role
        if role in CLASSES_BY_ROLE:
            return self.model in CLASSES_BY_ROLE[role]

        return False

    def has_add_permission(self, request):
        return self.has_change_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request)

    def get_queryset(self, request):
        qs = super(KUBookingModelAdmin, self).get_queryset(request)

        if request.user.userprofile.is_administrator():
            return qs

        # Filter anything that has a unit to the units the user has access to
        if hasattr(self.model, 'unit'):
            unit_qs = request.user.userprofile.get_unit_queryset()
            if getattr(self.model, 'allow_null_unit_editing', False):
                qs = qs.filter(Q(unit=None) | Q(unit=unit_qs))
            else:
                qs = qs.filter(unit=unit_qs)

        print qs.query
        return qs

    def get_form(self, request, obj=None, **kwargs):
        form = super(KUBookingModelAdmin, self).get_form(
            request, obj, **kwargs
        )

        if request.user.userprofile.is_administrator():
            return form

        if hasattr(self.model, 'unit') and 'unit' in form.base_fields:
            # Limit choices to the unit the user has access to
            unit_qs = request.user.userprofile.get_unit_queryset()
            form.base_fields['unit'].queryset = unit_qs

            if not getattr(self.model, 'allow_null_unit_editing', False):
                # Do not allow selecting the blank option
                form.base_fields['unit'].empty_label = None

        return form


class KUBookingUnitAdmin(KUBookingModelAdmin):
    def get_queryset(self, request):
        return request.user.userprofile.get_unit_queryset()

    def get_form(self, request, obj=None, **kwargs):
        form = super(KUBookingUnitAdmin, self).get_form(
            request, obj, **kwargs
        )

        profile = request.user.userprofile

        # Limit parent choices to faculties the user has access to
        unit_qs = profile.get_unit_queryset().filter(type__name="Fakultet")
        form.base_fields['parent'].queryset = unit_qs
        if not profile.is_administrator():
            # All units must have faculty parent
            form.base_fields['parent'].empty_label = None

            # Only allow "Institut" choice
            type_field = form.base_fields['type']
            type_field.queryset = type_field.queryset.filter(
                name="Institut"
            )
            type_field.empty_label = None

        return form


CUSTOM_ADMIN_CLASSES[booking_models.Unit] = KUBookingUnitAdmin

# Register your models here.
for name, value in booking_models.__dict__.iteritems():
    # Skip stuff that is not classes
    if not isinstance(value, type):
        continue

    # Skip stuff that is not models
    if not issubclass(value, django_models.Model):
        continue

    # Skip stuff that is not native to the booking.models module
    if not value.__module__ == 'booking.models':
        continue

    if value in EXCLUDE_MODELS:
        continue

    cls = CUSTOM_ADMIN_CLASSES.get(value, KUBookingModelAdmin)
    admin.site.register(value, cls)
