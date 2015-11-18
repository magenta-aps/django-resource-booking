# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.views.generic.base import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse

from booking.models import UnitType
from booking.forms import UnitTypeForm

from pprint import pprint

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




class UnitTypeMixin(Mixin):
    model = UnitType
    object_name = 'UnitType'
    url_base = 'unittype'

class UnitTypeFormMixin(UnitTypeMixin):
    form_class = UnitTypeForm
    template_name = 'unittype/form.html'
    success_url = '/unittype'


class ListUnitType(UnitTypeMixin, ListView):
    # Inherit from superclasses and leverage their methods
    template_name = 'unittype/list.html'

class NewUnitType(UnitTypeFormMixin, CreateView):
    # Inherit from superclasses and leverage their methods
    pass

class EditUnitType(UnitTypeFormMixin, UpdateView):
    # Inherit from superclasses and leverage their methods
    pass

class DeleteUnitType(UnitTypeMixin, DeleteView):
    # Inherit from superclasses and leverage their methods
    template_name = 'unittype/delete.html'
    def get_success_url(self):
        return reverse('unittype_list')

