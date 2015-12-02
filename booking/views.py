# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


from .models import Unit, UnitType
from .forms import UnitForm, UnitTypeForm


i18n_test = _(u"Dette tester oversættelses-systemet")


# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes

class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


class Mixin(object):
    object_name = 'Object'
    url_base = 'object'

    # Get the view's topmost superclass that is not a Mixin
    def get_other_superclass(self):
        for superclass in self.__class__.__mro__:
            if not issubclass(superclass, Mixin):
                return superclass

    # Call the 'real' get_context_data() from the non-Mixin superclass
    # and apply the object_name to it.
    def get_context_data(self, **kwargs):
        superclass = super(self.get_other_superclass(), self)
        context = superclass.get_context_data(**kwargs)
        context['object_name'] = self.object_name
        return context


class LoginRequiredMixin(object):
    """Include this mixin to require login.

    Mainly useful for users who are not coordinators or administrators.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Check that user is logged in and dispatch."""
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class RoleRequiredMixin(object):
    """Require that user has any of a number of roles."""

    # Roles is a list of required roles - maybe only one.
    # Each user can have only one role, and the condition is fulfilled
    # if one is found.

    roles = []  # Specify in subclass.

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        current_user = self.request.user
        try:
            role = current_user.userprofile.get_role()
            if role in self.roles:
                return super(RoleRequiredMixin, self).dispatch(*args, **kwargs)
        except AttributeError:
            pass
        raise PermissionDenied


class ListMixin(Mixin):
    def __init__(self):
        self.template_name = "%s/list.html" % self.url_base


class CreateMixin(Mixin):
    pass


class EditMixin(Mixin):
    pass


class DeleteMixin(Mixin):

    def __init__(self):
        self.template_name = "%s/delete.html" % self.url_base

    def get_success_url(self):
        return reverse("%s_list" % self.url_base)


class UnitTypeMixin(Mixin):
    model = UnitType
    object_name = 'UnitType'
    url_base = 'unittype'
    form_class = UnitTypeForm
    template_name = 'unittype/form.html'
    success_url = '/unittype'


class ListUnitType(UnitTypeMixin, ListMixin, ListView):
    # Inherit from superclasses and leverage their methods
    pass


class CreateUnitType(UnitTypeMixin, CreateMixin, CreateView):
    # Inherit from superclasses and leverage their methods
    pass


class EditUnitType(UnitTypeMixin, EditMixin, UpdateView):
    # Inherit from superclasses and leverage their methods
    pass


class DeleteUnitType(UnitTypeMixin, DeleteMixin, DeleteView):
    # Inherit from superclasses and leverage their methods
    pass


class UnitMixin(Mixin):
    model = Unit
    object_name = 'Unit'
    url_base = 'unit'
    form_class = UnitForm
    template_name = 'unit/form.html'
    success_url = '/unit'


class ListUnit(UnitMixin, ListMixin, ListView):
    # Inherit from superclasses and leverage their methods
    pass


class CreateUnit(UnitMixin, CreateMixin, CreateView):
    # Inherit from superclasses and leverage their methods
    pass


class EditUnit(UnitMixin, EditMixin, UpdateView):
    # Inherit from superclasses and leverage their methods
    pass


class DeleteUnit(UnitMixin, DeleteMixin, DeleteView):
    # Inherit from superclasses and leverage their methods
    pass
