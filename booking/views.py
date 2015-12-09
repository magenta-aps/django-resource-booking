# -*- coding: utf-8 -*-
from django.views.generic import TemplateView, ListView, DetailView
from django.utils.translation import ugettext as _
from django.views.generic.edit import UpdateView

from booking.models import Visit
from booking.forms import VisitForm
from booking.forms import VisitStudyMaterialForm
from booking.models import StudyMaterial

from booking.models import Resource, Subject

from pprint import pprint
from inspect import getmembers

i18n_test = _(u"Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


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
        return self.model.objects.search(searchexpression).filter(
            **filters
        )

    def build_choices(self, choice_tuples, selected,
                      selected_value='checked="checked"'):

        selected = set(selected)
        choices = []

        for value, name in choice_tuples:
            if unicode(value) in selected:
                sel = selected_value
            else:
                sel = ''

            choices.append({
                'label': name,
                'value': value,
                'selected': sel
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
            [(x.pk, x.name) for x in Subject.objects.all().order_by("name")],
            gym_selected,
        )

        gs_selected = self.request.GET.getlist("g")
        context["grundskole_selected"] = gs_selected
        context["grundskole_choices"] = self.build_choices(
            [(x.pk, x.name) for x in Subject.objects.all().order_by("name")],
            gs_selected,
        )

        context.update(kwargs)
        return super(SearchView, self).get_context_data(**context)


class VisitMixin(object):

    model = Visit
    object_name = 'Visit'
    url_base = 'visit'
    form_class = VisitForm

    template_name = 'visit/form.html'

    def get_success_url(self):
        try:
            return "/visit/%d" % self.object.id
        except:
            return '/'


class EditVisit(VisitMixin, UpdateView):

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.object = Visit() if pk is None else Visit.objects.get(id=pk)
        if kwargs.get("clone") and self.object:
            self.object.pk = None
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(None, instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk is None or kwargs.get("clone"):
            self.object = None
        else:
            Visit.objects.get(id=pk)
        form = self.get_form()
        if form.is_valid():
            visit = form.save()
            fileformset = VisitStudyMaterialForm(request.POST, instance=visit)
            if fileformset.is_valid():
                visit.save()
                for fileform in fileformset:
                    try:
                        instance = StudyMaterial(
                            visit=visit,
                            file=request.FILES["%s-file" % fileform.prefix]
                        )
                        instance.save()
                    except:
                        pass

            return super(EditVisit, self).form_valid(form)
        else:
            return self.form_invalid(form)


class VisitDetailView(DetailView):
    """Display Visit details"""
    model = Visit
    template_name = 'visit/details.html'
