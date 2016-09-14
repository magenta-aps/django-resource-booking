# encoding: utf-8
import booking.models as booking_models
from django.core.urlresolvers import reverse
from django.http import Http404
from django.views.generic import CreateView, UpdateView
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
            use_product_duration=True,
            **kwargs
        )

    def get_success_url(self):
        return reverse(
            'manage-times', args=[self.kwargs.get('product_pk', -1)]
        )


class EditTimeView(UpdateView):
    model = booking_models.EventTime
    template_name = 'eventtime/edit.html'

    fields = ('has_specific_time', 'start', 'end', 'notes')

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()

        form = form_class(**kwargs)

        form.fields['has_specific_time'].coerce = lambda x: x == 'True'

        return form

    def get_context_data(self, **kwargs):

        use_duration = False
        duration = self.object.product.duration_in_minutes

        if duration > 0 and duration == self.object.duration_in_minutes:
            use_duration = True

        return super(EditTimeView, self).get_context_data(
            product=self.object.product,
            use_product_duration=use_duration,
            **kwargs
        )

    def get_success_url(self):
        return reverse(
            'manage-times', args=[self.kwargs.get('product_pk', -1)]
        )
