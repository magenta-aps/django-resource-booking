# -*- coding: utf-8 -*-
import json

from datetime import datetime, timedelta

from dateutil import parser
from dateutil.rrule import rrulestr
from django.http import HttpResponse
from django.views.generic import TemplateView, ListView, DetailView, View
from django.utils.translation import ugettext as _
from django.views.generic.edit import UpdateView

from booking.models import Visit, VisitOccurrence
from booking.forms import VisitForm
from booking.forms import VisitStudyMaterialForm
from booking.models import StudyMaterial

from booking.models import Resource, Subject


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


class VisitMixin(object):

    model = Visit
    object_name = 'Visit'
    url_base = 'visit'
    form_class = VisitForm

    template_name = 'visit/form.html'
    success_url = '/visit'


class EditVisit(VisitMixin, UpdateView):

    # Display a view with two form objects; one for the regular model,
    # and one for the file upload
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.object = None if pk is None else Visit.objects.get(id=pk)
        form = self.get_form()
        fileformset = VisitStudyMaterialForm(instance=Visit())
        return self.render_to_response(
            self.get_context_data(form=form, fileformset=fileformset)
        )

    # Handle both forms, creating a Visit and a number of StudyMaterials
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        self.object = None if pk is None else Visit.objects.get(id=pk)
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
            dates = request.POST.getlist(u'occurrences')

            datetimes = []
            if dates is not None:
                for date in dates:
                    datetimes.append(parser.parse(date, dayfirst=True))
            for date_t in datetimes:
                duration = request.POST[u'duration']
                hours = int(duration[0:2])
                minutes = int(duration[3:5])
                end_datetime = date_t
                if duration is not None:
                    end_datetime = date_t + timedelta(
                        hours=hours,
                        minutes=minutes
                    )
                instance = VisitOccurrence(
                    start_datetime=date_t,
                    end_datetime1=end_datetime,
                    visit=visit
                )
                instance.save()

            return super(EditVisit, self).form_valid(form)
        else:
            return self.form_invalid(form)


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


class RrulestrView(View):

    def post(self, request):
        """
        Handle Ajax requests: Essentially, dateutil.rrule.rrulestr function
        exposed as a web service, expanding RRULEs to a list of datetimes.
        In addition, we add RRDATEs and return the sorted list in danish
        date format. If the string doesn't contain an UNTIL clause, we set it
        to 90 days in the future from datetime.now().
        If multiple start_times are present, the Cartesian product of
        dates x start_times is returned.
        """
        rrulestring = request.POST['rrulestr']
        now = datetime.now()
        dates = []
        lines = rrulestring.split("\n")
        times_list = request.POST[u'start_times'].split(',')

        for line in lines:
            # When handling RRULEs, we don't want to send all dates until
            # 9999-12-31 to the client, which apparently is rrulestr() default
            # behaviour. Hence, we set a default UNTIL clause to 90 days in
            # the future from datetime.now()
            # Todo: This should probably be handled more elegantly
            if u'RRULE' in line and u'UNTIL=' not in line:
                line += u';UNTIL=%s' % (now + timedelta(90))\
                    .strftime('%Y%m%dT%H%M%SZ')
                dates = [x for x in rrulestr(line, ignoretz=True)]
            # RRDATEs are appended to the dates list
            elif u'RDATE' in line:
                dates.append(datetime.strptime(line[6:], '%Y%m%dT%H%M%SZ'))
        # sort the list while still in ISO 8601 format,
        dates.sort()
        # Cartesian product: AxB
        # ['2016-01-01','2016-01-02'] x ['10:00','12:00'] ->
        # ['2016-01-01 10:00','2016-01-01 12:00',
        # '2016-01-02 10:00','2016-01-02 12:00']
        dates_to_return = \
            [val.replace(  # parse time format: '00:00'
                hour=int(_[0:2]),
                minute=int(_[4:6])
            ) for val in dates for _ in times_list]

        # convert to danish date format and off we go...
        date_strings = [x.strftime('%d-%m-%Y %H:%M') for x in dates_to_return]
        return HttpResponse(
            json.dumps(date_strings),
            content_type='application/json'
        )
