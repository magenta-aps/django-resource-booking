# encoding: utf-8
import datetime
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.edit import FormView, DeleteView
from booking.models import OrganizationalUnit, Product
from booking.resource_based.forms import ResourceTypeForm, EditResourceForm
from booking.resource_based.forms import ResourcePoolTypeForm
from booking.resource_based.forms import EditResourcePoolForm
from booking.resource_based.forms import EditResourceRequirementForm
from booking.resource_based.forms import EditVisitResourcesForm
from booking.resource_based.models import Resource, ResourceType
from booking.resource_based.models import ItemResource, RoomResource
from booking.resource_based.models import TeacherResource, HostResource
from booking.resource_based.models import VehicleResource
from booking.resource_based.models import ResourcePool
from booking.resource_based.models import ResourceRequirement
from booking.views import BackMixin, BreadcrumbMixin, LoginRequiredMixin
from itertools import chain

import booking.models as booking_models
import booking.resource_based.forms as rb_forms


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
        return super(EditTimeView, self).get_context_data(
            product=self.object.product,
            use_product_duration=self.object.duration_matches_product,
            **kwargs
        )

    def get_success_url(self):
        if 'visit_pk' in self.kwargs:
            return reverse('visit-view', args=[self.kwargs['visit_pk']])
        else:
            product_pk = self.kwargs.get('product_pk', -1)
            return reverse('manage-times', args=[product_pk])


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


class TimeDetailsView(DetailView):
    model = booking_models.EventTime
    template_name = 'eventtime/details.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # If object
        if self.object.visit:
            return redirect(self.get_success_url())

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if(request.POST.get("confirm")):
            self.object.make_visit(True)
            return redirect(self.get_success_url())
        else:
            # Do same thing as for get method
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.visit.pk])


class ResourceCreateView(BackMixin, BreadcrumbMixin, FormView):
    template_name = "resource/typeform.html"
    form_class = ResourceTypeForm
    just_preserve_back = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            typeId = int(form.cleaned_data['type'])
            unitId = int(form.cleaned_data['unit'])

            return self.redirect(reverse(
                'resource-create-type',
                kwargs={'type': typeId, 'unit': unitId}
            ))

        return self.render_to_response(
            self.get_context_data(**context)
        )

    def get_breadcrumbs(self):
        return [
            {'url': reverse('resource-list'), 'text': _(u'Ressourcer')},
            {'text': _(u'Opret ressource')},
        ]


class ResourceDetailView(BreadcrumbMixin, TemplateView):
    template_name = "resource/details.html"

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = None
        try:
            self.object = Resource.get_subclass_instance(pk)
        except Resource.DoesNotExist:
            raise Http404
        return super(ResourceDetailView, self).dispatch(
            request, *args, **kwargs
        )

    def get_breadcrumbs(self):
        return [
            {'url': reverse('resource-list'), 'text': _(u'Ressourcer')},
            {'text': unicode(self.object)}
        ]

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context.update(kwargs)
        return super(ResourceDetailView, self).get_context_data(**context)


class ResourceListView(BreadcrumbMixin, ListView):
    model = Resource
    template_name = "resource/list.html"

    def get_context_object_name(self, queryset):
        return "resources"

    def get_queryset(self):
        return chain(
            ItemResource.objects.all(),
            RoomResource.objects.all(),
            TeacherResource.objects.all(),
            HostResource.objects.all(),
            VehicleResource.objects.all()
        )

    def get_breadcrumbs(self):
        return [
            {'text': _(u'Ressourcer')}
        ]


class ResourceUpdateView(BackMixin, BreadcrumbMixin, UpdateView):
    template_name = "resource/form.html"
    object = None

    def dispatch(self, request, *args, **kwargs):
        self.set_object(kwargs.get("pk"), request)
        return super(ResourceUpdateView, self).dispatch(
            request, *args, **kwargs
        )

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            self.get_context_data(form=self.get_form())
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if 'unit' in self.kwargs:
                unitId = int(self.kwargs['unit'])
                self.object = form.save()
                self.object.organizationalunit = \
                    booking_models.OrganizationalUnit.objects.get(id=unitId)
                self.object.save()
            else:
                self.object = form.save(commit=True)
            return self.redirect(
                reverse('resource-view', args=[self.object.id])
            )
        else:
            return self.render_to_response(
                self.get_context_data(form=form)
            )

    def get_form_class(self):
        if 'type' in self.kwargs:
            type = int(self.kwargs['type'])
        else:
            type = self.object.resource_type.id
        return EditResourceForm.get_resource_form_class(type)

    def get_breadcrumbs(self):
        breadcrumbs = [{
            'url': reverse('resource-list'),
            'text': _(u'Ressourcer')
        }]
        if self.object.pk:
            breadcrumbs.append({
                'url': reverse('resource-view', args=[self.object.id]),
                'text': unicode(self.object)
            })
            breadcrumbs.append({'text': _(u'Redigér')})
        else:
            breadcrumbs.append({'text': _(u'Opret ressource')})
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context.update(kwargs)
        return super(ResourceUpdateView, self).get_context_data(**context)

    def set_object(self, pk, request, is_cloning=False):
        if is_cloning or not hasattr(self, 'object') or self.object is None:
            if pk is None:
                try:
                    self.object = Resource.create_subclass_instance(
                        self.kwargs['type']
                    )
                    self.object.organizationalunit = \
                        booking_models.OrganizationalUnit.objects.get(
                            id=self.kwargs['unit']
                        )
                except Exception as e:
                    print e
                    pass
            else:
                try:
                    self.object = Resource.get_subclass_instance(pk)
                    if is_cloning:
                        self.object.pk = None
                        self.object.id = None
                except Resource.DoesNotExist:
                    raise Http404

        if self.object.pk:
            self.is_creating = False
        else:
            self.is_creating = True
            self.object.created_by = self.request.user


class ResourceDeleteView(BackMixin, BreadcrumbMixin, DeleteView):
    success_url = reverse_lazy('resource-list')
    back_on_success = False

    def get_template_names(self):
        return ['resource/delete.html']

    def get_object(self):
        return Resource.get_subclass_instance(self.kwargs.get("pk"))

    def get_breadcrumbs(self):
        return [
            {'url': reverse('resource-list'), 'text': _(u'Ressourcer')},
            {'url': reverse('resource-view', args=[self.object.id]),
             'text': self.object},
            {'text': _(u'Slet')}
        ]


class ResourcePoolCreateView(BackMixin, BreadcrumbMixin, FormView):
    template_name = "resourcepool/typeform.html"
    form_class = ResourcePoolTypeForm
    just_preserve_back = True

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            typeId = int(form.cleaned_data['type'])
            unitId = int(form.cleaned_data['unit'])

            return self.redirect(
                reverse(
                    'resourcepool-create-type',
                    kwargs={'type': typeId, 'unit': unitId}
                )
            )

        return self.render_to_response(
            self.get_context_data(**context)
        )

    def get_breadcrumbs(self):
        return [
            {
                'url': reverse('resourcepool-list'),
                'text': _(u'Ressourcegrupper')
            },
            {'text': _(u'Opret ressourcegruppe')},
        ]


class ResourcePoolDetailView(BreadcrumbMixin, DetailView):
    template_name = "resourcepool/details.html"
    model = ResourcePool

    def get_breadcrumbs(self):
        return [
            {
                'url': reverse('resourcepool-list'),
                'text': _(u'Ressourcegrupper')
            },
            {'text': unicode(self.object)}
        ]


class ResourcePoolListView(BreadcrumbMixin, ListView):
    model = ResourcePool
    template_name = "resourcepool/list.html"

    def get_context_object_name(self, queryset):
        return "resourcepools"

    def get_breadcrumbs(self):
        return [
            {'text': _(u'Ressourcegrupper')}
        ]


class ResourcePoolUpdateView(BackMixin, BreadcrumbMixin, UpdateView):
    template_name = "resourcepool/form.html"
    object = None
    form_class = EditResourcePoolForm
    model = ResourcePool

    def dispatch(self, request, *args, **kwargs):
        self.set_object(kwargs.get("pk"), request)
        return super(ResourcePoolUpdateView, self).dispatch(
            request, *args, **kwargs
        )

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            self.get_context_data(form=self.get_form())
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if 'unit' in self.kwargs and 'type' in self.kwargs:
                unitId = int(self.kwargs['unit'])
                typeId = int(self.kwargs['type'])
                self.object = form.save()
                self.object.organizationalunit = \
                    booking_models.OrganizationalUnit.objects.get(id=unitId)
                self.object.resource_type = ResourceType.objects.get(id=typeId)
                self.object.save()
            else:
                self.object = form.save(commit=True)
            return self.redirect(
                reverse('resource-view', args=[self.object.id])
            )
        else:
            return self.render_to_response(
                self.get_context_data(form=form)
            )

    def get_breadcrumbs(self):
        breadcrumbs = [{
            'url': reverse('resourcepool-list'),
            'text': _(u'Ressourcegrupper')
        }]
        if self.object.pk:
            breadcrumbs.append({
                'url': reverse('resourcepool-view', args=[self.object.id]),
                'text': unicode(self.object)
            })
            breadcrumbs.append({'text': _(u'Redigér')})
        else:
            breadcrumbs.append({'text': _(u'Opret ressource')})
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context.update(kwargs)
        return super(ResourcePoolUpdateView, self).get_context_data(**context)

    def set_object(self, pk, request, is_cloning=False):
        if is_cloning or not hasattr(self, 'object') or self.object is None:
            if pk is None:
                self.object = ResourcePool()
                if 'type' in self.kwargs:
                    self.object.resource_type = ResourceType.objects.get(
                        id=self.kwargs['type']
                    )
                if 'unit' in self.kwargs:
                    self.object.organizationalunit = \
                        OrganizationalUnit.objects.get(id=self.kwargs['unit'])
            else:
                try:
                    self.object = ResourcePool.objects.get(pk=pk)
                    if is_cloning:
                        self.object.pk = None
                        self.object.id = None
                except Resource.DoesNotExist:
                    raise Http404

        if self.object.pk:
            self.is_creating = False
        else:
            self.is_creating = True
            self.object.created_by = self.request.user


class ResourcePoolDeleteView(BackMixin, BreadcrumbMixin, DeleteView):
    success_url = reverse_lazy('resourcepool-list')
    model = ResourcePool
    back_on_success = False

    def delete(self, request, *args, **kwargs):
        if request.POST.get('delete_members') == 'delete':
            for member in self.get_object().resources.all():
                member.delete()
        return super(ResourcePoolDeleteView, self).delete(
            request, *args, **kwargs
        )

    def get_template_names(self):
        return ['resourcepool/delete.html']

    def get_breadcrumbs(self):
        return [
            {
                'url': reverse('resourcepool-list'),
                'text': _(u'Ressourcegrupper')
            },
            {
                'url': reverse('resourcepool-view', args=[self.object.id]),
                'text': self.object
            },
            {'text': _(u'Slet')}
        ]


class ResourceRequirementCreateView(BackMixin, BreadcrumbMixin, CreateView):
    model = ResourceRequirement
    form_class = EditResourceRequirementForm

    def get_template_names(self):
        return ['resourcerequirement/form.html']

    def dispatch(self, request, *args, **kwargs):
        self.product = Product.objects.get(id=self.kwargs['product'])
        return super(ResourceRequirementCreateView, self).dispatch(
            request, *args, **kwargs
        )

    def get_form_kwargs(self):
        kwargs = super(ResourceRequirementCreateView, self).get_form_kwargs()
        kwargs['product'] = self.product
        kwargs['initial']['required_amount'] = 1
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        return self.redirect(
            reverse('product-view', args=[self.product.id])
        )

    def get_breadcrumbs(self):
        return [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {
                'url': self.request.GET.get("search", reverse('search')),
                'text': _(u'Søgeresultat')
            },
            {
                'url': reverse('product-view', args=[self.product.id]),
                'text': unicode(self.product)
            },
            {'text': _(u'Opret ressourcebehov')}
        ]


class ResourceRequirementUpdateView(BackMixin, BreadcrumbMixin, UpdateView):
    model = ResourceRequirement
    form_class = EditResourceRequirementForm

    def get_template_names(self):
        return ['resourcerequirement/form.html']

    def get_form_kwargs(self):
        kwargs = super(ResourceRequirementUpdateView, self).get_form_kwargs()
        kwargs['product'] = self.object.product
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        return self.redirect(
            reverse('product-view', args=[self.object.product.id])
        )

    def get_breadcrumbs(self):
        return [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {
                'url': self.request.GET.get("search", reverse('search')),
                'text': _(u'Søgeresultat')
            },
            {
                'url': reverse('product-view', args=[self.object.product.id]),
                'text': unicode(self.object.product)
            },
            {'text': _(u'Redigér ressourcebehov')}
        ]


class ResourceRequirementListView(BreadcrumbMixin, ListView):
    model = ResourceRequirement
    template_name = "resourcerequirement/list.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = Product.objects.get(id=self.kwargs['product'])
        return super(ResourceRequirementListView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_object_name(self, queryset):
        return "resourcerequirements"

    def get_context_data(self, **kwargs):
        context = {}
        context['product'] = self.product
        context.update(kwargs)
        return super(ResourceRequirementListView, self).get_context_data(
            **context
        )

    def get_queryset(self):
        return self.product.resourcerequirement_set

    def get_breadcrumbs(self):
        return [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {
                'url': self.request.GET.get("search", reverse('search')),
                'text': _(u'Søgeresultat')
            },
            {
                'url': reverse('product-view', args=[self.product.id]),
                'text': unicode(self.product)
            },
            {'text': _(u'Ressourcebehov')}
        ]


class ResourceRequirementDeleteView(BackMixin, BreadcrumbMixin, DeleteView):
    model = ResourceRequirement
    success_url = reverse_lazy('resourcerequirement-list')
    back_on_success = False

    def get_success_url(self, regular=None):
        return reverse(
            'resourcerequirement-list',
            args=[self.object.product.id]
        )

    def get_template_names(self):
        return ['resourcerequirement/delete.html']

    def get_breadcrumbs(self):
        return [
            {'url': reverse('search'), 'text': _(u'Søgning')},
            {
                'url': self.request.GET.get("search", reverse('search')),
                'text': _(u'Søgeresultat')
            },
            {
                'url': reverse('product-view', args=[self.object.product.id]),
                'text': unicode(self.object.product)
            },
            {'text': _(u'Slet ressourcebehov')}
        ]


class VisitResourceEditView(FormView):
    template_name = "visit/resources.html"
    form_class = EditVisitResourcesForm

    def dispatch(self, request, *args, **kwargs):
        self.visit = booking_models.Visit.objects.get(id=kwargs['pk'])
        return super(VisitResourceEditView, self).dispatch(
            request, *args, **kwargs
        )

    def get_form_kwargs(self):
        kwargs = super(VisitResourceEditView, self).get_form_kwargs()
        kwargs['visit'] = self.visit
        kwargs['initial'] = [
            {
                'resources': [
                    resource.id
                    for resource in self.visit.resources.filter(
                        visitresource__resource_requirement=requirement
                    )
                ]
            }
            for requirement in self.visit.product.resourcerequirement_set.all()
        ]
        return kwargs

    def get_context_data(self, **kwargs):
        context = {}
        context['visit'] = self.visit
        context.update(kwargs)
        return super(VisitResourceEditView, self).get_context_data(**context)

    def form_valid(self, form):
        form.save()
        return super(VisitResourceEditView, self).form_valid(form)

    def get_success_url(self):
        return reverse('visit-view', args=[self.visit.id])


class CalendarView(LoginRequiredMixin, DetailView):
    template_name = 'calendar/calendar.html'

    def get_object(self, queryset=None):
        queryset = booking_models.Calendar.objects.filter(
            resource__pk=self.kwargs['pk']
        )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return obj

    def get_context_data(self, **kwargs):
        calendar = self.object

        input_month = self.request.GET.get("month")
        if input_month and len(input_month) == 6:
            start_year = int(input_month[:4])
            start_month = int(input_month[4:])
        else:
            now = timezone.now()
            start_year = now.year
            start_month = now.month

        first_of_the_month = datetime.date(start_year, start_month, 1)

        start_date = first_of_the_month

        # Make start date the monday before the first in the month
        if start_date.isoweekday() != 1:
            start_date = start_date - datetime.timedelta(
                days=start_date.isoweekday() - 1
            )

        # Make end date in next month
        end_date = first_of_the_month + datetime.timedelta(31)
        # And subtract the number of days within that month so we get last
        # day of current month
        end_date = end_date - datetime.timedelta(days=end_date.day)
        # And then add days to get the next sunday
        if end_date.isoweekday() != 7:
            end_date = end_date + datetime.timedelta(
                days=7 - end_date.isoweekday()
            )

        events_by_date = {}

        current_date = start_date
        week = []
        weeks = []
        while current_date <= end_date:
            events = []

            week.append({
                'date': current_date,
                'events': events
            })

            events_by_date[current_date.isoformat()] = events

            if len(week) == 7:
                weeks.append(week)
                week = []

            current_date = current_date + datetime.timedelta(days=1)

        start_dt = timezone.make_aware(
            timezone.datetime.combine(start_date, datetime.time())
        )
        end_dt = timezone.make_aware(
            timezone.datetime.combine(end_date, datetime.time())
        )

        available = [x for x in calendar.available_list(start_dt, end_dt)]
        unavailable = [x for x in calendar.unavailable_list(start_dt, end_dt)]

        for x in available + unavailable:
            date = x.start.date()
            # Add event to all the days it spans
            for y in range(0, (x.end - x.start).days + 1):
                events_by_date[date.isoformat()].append(x.day_marker(date))
                date = date + datetime.timedelta(days=1)

        return super(CalendarView, self).get_context_data(
            calendar=calendar,
            resource=calendar.resource,
            month=first_of_the_month,
            next_month=first_of_the_month + datetime.timedelta(days=31),
            prev_month=first_of_the_month - datetime.timedelta(days=1),
            calendar_weeks=weeks,
            available=calendar.calendarevent_set.filter(
                availability=booking_models.CalendarEvent.AVAILABLE
            ),
            unavailable=calendar.calendarevent_set.filter(
                availability=booking_models.CalendarEvent.NOT_AVAILABLE
            ),
            **kwargs
        )


class CalendarCreateView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        queryset = booking_models.Resource.objects.filter(
            pk=self.kwargs['pk']
        )
        try:
            # Get the single item from the filtered queryset
            resource = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        # Create empty calendar if one does not exist
        print resource.calendar
        resource.make_calendar()
        print resource.calendar

        return reverse('calendar', args=[resource.pk])


class CalendarDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'calendar/delete.html'

    def get_object(self, queryset=None):
        queryset = booking_models.Resource.objects.filter(
            pk=self.kwargs['pk']
        )
        try:
            # Get the single item from the filtered queryset
            self.resource = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})


        return self.resource.calendar

    def get_success_url(self):
        return reverse('resource-view', args=[self.resource.pk])


class CalendarEventView(CreateView):
    model = booking_models.CalendarEvent
    template_name = 'calendar/calendar_event.html'

    fields = (
        'title',
        'start',
        'end',
        'recurrences',
        'availability',
        'calendar'
    )

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        resource_pk = self.kwargs.get('pk', -1)
        try:
            calendar = booking_models.Calendar.objects.get(
                resource__pk=resource_pk
            )
        except:
            raise Http404
        kwargs['initial']['calendar'] = calendar.pk
        form = form_class(**kwargs)
        return form

    def get_context_data(self, **kwargs):
        return super(CalendarEventView, self).get_context_data(
            **kwargs
        )

    def get_success_url(self):
        return reverse('calendar', args=[self.kwargs.get('pk')])


class CalendarEventDeleteView(DeleteView):
    model = booking_models.CalendarEvent
    template_name = 'calendar_event_confirm_delete.html'

    def get_success_url(self):
        resource_pk = self.object.calendar.resource.pk
        return '/resource/%d/calendar/' % resource_pk
