# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.views.generic.edit import UpdateView

from booking.models import Visit
from booking.forms import VisitForm
from booking.forms import VisitStudyMaterialForm
from booking.models import StudyMaterial


i18n_test = _(u"Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


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

            return super(EditVisit, self).form_valid(form)
        else:
            return self.form_invalid(form)
