# encoding: utf-8
import booking.models as booking_models
from django.http import Http404
from django.views.generic import CreateView
from django.views.generic import DetailView


class ManageTimesView(DetailView):
    model = booking_models.Product
    template_name = 'eventtime/list.html'


class CreateTimeView(CreateView):
    model = booking_models.EventTime
    template_name = 'eventtime/create.html'

    fields = ('product', 'has_specific_time', 'start', 'end', 'notes')

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()

        kwargs['initial']['product'] = self.kwargs.get('product_pk', -1)

        form = form_class(**kwargs)

        form.fields['has_specific_time'].coerce = lambda x: x == 'True'

        return form

    def get_context_data(self, **kwargs):
        try:
            product = booking_models.Product.objects.get(
                pk=self.kwargs.get('product_pk', -1)
            )
        except:
            raise Http404

        return super(CreateTimeView, self).get_context_data(
            product=product,
            **kwargs
        )
