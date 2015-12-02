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

from booking.models import Resource, Subject


i18n_test = _(u"Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes

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

# Class for handling main search

class SearchView(ListView):
    model = Resource
    template_name = "resource/searchresult.html"
    context_object_name = "results"
    paginate_by = 10

    def get_queryset(self):
        searchexpression = self.request.GET.get("q", "")
        filters = {}
        a = self.request.GET.getlist("a")
        if a:
            filters["audience__in"] = a
        t = self.request.GET.getlist("t")
        if t:
            filters["type__in"] = t
        f = set(self.request.GET.getlist("f"))
        for g in self.request.GET.getlist("g"):
            f.add(g)
        if f:
            filters["subjects__in"] = f
        print filters
        return self.model.objects.search(searchexpression).filter(
            **filters
        )

    def build_choices(self, choice_tuples, selected,
                      selected_value='checked="checked"'):

        selected = set(selected)
        choices = []

        for value,name in choice_tuples:
            if unicode(value) in selected:
                sel = selected_value
            else:
                sel = ''

            choices.append({
                'label': name,
                'value': value,
                'selected' : sel
            })

        return choices

    def get_context_data(self, **kwargs):
        context = {} 

        # Store the querystring without the page argument
        qdict = self.request.GET.copy()
        if "page" in qdict:
            qdict.pop("page")
        context["qstring"] = qdict.urlencode()

        context["audience_choices"] = self.build_choices(
            self.model.audience_choices,
            self.request.GET.getlist("a"),
        )
        
        context["type_choices"] = self.build_choices(
            self.model.resource_type_choices,
            self.request.GET.getlist("t"),
        )

        gym_selected = self.request.GET.getlist("f")
        context["gymnasie_selected"] = gym_selected
        context["gymnasie_choices"] = self.build_choices(
            [ (x.pk, x.name) for x in Subject.objects.all().order_by("name") ],
            gym_selected,
        )

        gs_selected = self.request.GET.getlist("g")
        context["grundskole_selected"] = gs_selected
        context["grundskole_choices"] = self.build_choices(
            [ (x.pk, x.name) for x in Subject.objects.all().order_by("name") ],
            gs_selected,
        )

        context.update(kwargs)
        return super(SearchView, self).get_context_data(**context)