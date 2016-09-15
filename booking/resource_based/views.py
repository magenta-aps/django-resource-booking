# encoding: utf-8
import booking.models as booking_models
import booking.resource_based.forms as rb_forms
import datetime
from django import forms
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import CreateView, FormView, TemplateView, UpdateView
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


class CreateTimesFromRulesView(FormView):
    template_name = 'eventtime/create_from_rules.html'
    form_class = rb_forms.CreateTimesFromRulesForm
    product = None

    def get_product(self):
        if not self.product:
            try:
                self.product = booking_models.Product.objects.get(
                    pk=self.kwargs.get('product_pk', -1)
                )
            except:
                raise Http404

        return self.product

    def get_context_data(self, **kwargs):
        return super(CreateTimesFromRulesView, self).get_context_data(
            product=self.get_product(),
            use_product_duration=True,
            **kwargs
        )

    def get_success_url(self):
        return reverse(
            'manage-times', args=[self.kwargs.get('product_pk', -1)]
        )

    def form_valid(self, form):
        dates = self.request.POST.getlist('selecteddate', [])

        cls = booking_models.EventTime
        product = self.get_product()

        for dstr in dates:
            (start, end) = cls.parse_human_readable_interval(dstr)
            has_specific_time = True
            print (end - start).total_seconds()
            if (end - start).total_seconds() >= 24 * 60 * 60:
                has_specific_time = False
            d = cls(
                product=product,
                start=start,
                end=end,
                has_specific_time=has_specific_time,
                notes='',
            )
            d.save()

        return super(CreateTimesFromRulesView, self).form_valid(form)


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


class DeleteTimesView(TemplateView):
    template_name = 'eventtime/delete.html'
    items = []

    def get_queryset(self, request):
        ids = request.POST.getlist('selected_eventtimes', [-1])
        return booking_models.EventTime.objects.filter(
            pk__in=ids,
            product=self.kwargs['product_pk']
        )

    def get_context_data(self, **kwargs):
        try:
            product = booking_models.Product.objects.get(
                pk=self.kwargs.get('product_pk', -1)
            )
        except:
            raise Http404

        return super(DeleteTimesView, self).get_context_data(
            product=product,
            items=self.items or self.get_queryset(self.request),
            **kwargs
        )

    # Disable get requests
    def get(self, request, *args, **kwargs):
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return redirect(self.get_success_url())
        elif request.POST.get('confirm'):
            self.get_queryset(request).delete()
            return redirect(self.get_success_url())
        else:
            # Check that we actually want to delete something
            self.items = self.get_queryset(request)

            if len(self.items) == 0:
                return redirect(self.get_success_url())

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('manage-times', args=[self.kwargs['product_pk']])