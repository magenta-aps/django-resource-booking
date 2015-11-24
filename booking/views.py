# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse

from booking.models import UnitType
from booking.forms import UnitTypeForm

from booking.models import Unit
from booking.forms import UnitForm


i18n_test = _(u"Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'



# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes

class Mixin(object):
    object_name = 'Object'
    url_base = 'object'

    def get_other_superclass(self):
        for superclass in self.__class__.__mro__:
            if not issubclass(superclass, Mixin):
                return superclass

    def get_context_data(self, **kwargs):
        context = super(self.get_other_superclass(), self).get_context_data(**kwargs)
        context.update({
            'object_name': self.object_name
        })
        return context

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

