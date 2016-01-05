# -*- coding: utf-8 -*-
from django.views.generic import TemplateView, ListView, DetailView
from django.utils.translation import ugettext as _
from django.views.generic.edit import UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from profile.models import COORDINATOR, ADMINISTRATOR
from profile.models import role_to_text

from booking.models import Visit, StudyMaterial
from booking.models import Resource, Subject
from booking.forms import VisitForm
from booking.forms import VisitStudyMaterialForm

i18n_test = _(u"Dette tester oversættelses-systemet")


# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes

class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


class LoginRequiredMixin(object):
    """Include this mixin to require login.

    Mainly useful for users who are not coordinators or administrators.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Check that user is logged in and dispatch."""
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class AccessDenied(PermissionDenied):
    def __init__(self, text, *args, **kwargs):
        _text = text
        print _text
        return super(AccessDenied, self).__init__(text, *args, **kwargs)

    def __unicode__(self):
        print self._text
        return unicode(self._text)


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
        txts = map(role_to_text, self.roles)
        # TODO: Render this with the error message!
        raise AccessDenied(
            u"Kun brugere med disse roller kan logge ind: " +
            u",".join(txts)
        )


class SearchView(ListView):
    """Class for handling main search."""
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
        filters["state__in"] = [Resource.ACTIVE]
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


class EditVisit(RoleRequiredMixin, UpdateView):

    template_name = 'visit/form.html'
    form_class = VisitForm
    model = Visit

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload

    roles = COORDINATOR, ADMINISTRATOR

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.object = Visit() if pk is None else Visit.objects.get(id=pk)
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(None, instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else Visit.objects.get(id=pk)
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(request.POST)
        if form.is_valid():
            visit = form.save()
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
            return self.form_invalid(form, fileformset)

    def get_success_url(self):
        try:
            return "/visit/%d" % self.object.id
        except:
            return '/'

    def form_invalid(self, form, fileformset=None):
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # First, check all is well in superclass
        result = super(RoleRequiredMixin, self).__dispatch(*args, **kwargs)
        # Now, check that the user belongs to the correct unit.
        current_user = self.request.user
        pk = kwargs.get("pk")
        if self.object is None:
            self.object = None if pk is None else Visit.objects.get(id=pk)
        if self.object is not None:
            role = current_user.userprofile.get_role()
            if role == COORDINATOR:
                users_unit = current_user.userprofile.unit
                visits_unit = self.object.unit
                if not visits_unit.belongs_to(users_unit):
                    raise AccessDenied(
                        u"Du må kun redigere enheder,som du selv er "
                        "koordinator for."
                    )
        return result


class VisitDetailView(DetailView):
    """Display Visit details"""
    model = Visit
    template_name = 'visit/details.html'

    def get_queryset(self):
        """Get queryset, only include active visits."""
        qs = super(VisitDetailView, self).get_queryset()
        # Dismiss visits that are not active.
        if not self.request.user.is_authenticated():
            qs = qs.filter(state=Resource.ACTIVE)
        return qs
