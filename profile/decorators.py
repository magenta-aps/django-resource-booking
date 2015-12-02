"""Decorator to control access to views."""

from django.core.exceptions import PermissionDenied


def role_required(role, raise_exception=False):
    """Check if user has at least one of one or more roles.
       This function is inspired by the permission_required decorator in
       django.contrib.auth.decorators.
    """
    def check_roles(user):
        if not isinstance(role, (list, tuple)):
            roles = (role, )
        else:
            roles = role
        # Check if user has this role.
        has_role = any(map(user.has_role, roles))
        if raise_exception and not has_role:
            raise PermissionDenied
        return has_role
