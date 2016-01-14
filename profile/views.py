# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from booking.views import LoginRequiredMixin
from profile.forms import UserCreateForm


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the user's profile."""
    pass


class CreateUserView(CreateView):
    model = User
    form_class = UserCreateForm

    def get(self, request, *args, **kwargs):
        if request.user.userprofile.get_role() in [
            3,  # Administrator
            4   # Fakultetsredaktør
        ]:
            return super(CreateUserView, self).get(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def post(self, request, *args, **kwargs):
        if request.user.userprofile.get_role() in [
            3,  # Administrator
            4   # Fakultetsredaktør
        ]:
            return super(CreateUserView, self).post(request, *args, **kwargs)
        else:
            raise PermissionDenied
