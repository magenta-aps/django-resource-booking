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

from django.forms.widgets import TextInput, HiddenInput
from booking.models import OrganizationalUnit, Product, Visit
from booking.resource_based.forms import ResourceTypeForm, EditResourceForm
from booking.resource_based.forms import ResourcePoolTypeForm
from booking.resource_based.forms import EditResourcePoolForm
from booking.resource_based.forms import EditResourceRequirementForm
from booking.resource_based.forms import EditVisitResourcesForm
from booking.resource_based.models import Resource, ResourceType
from booking.resource_based.models import ItemResource, RoomResource
from booking.resource_based.models import TeacherResource, HostResource
from booking.resource_based.models import VehicleResource
from booking.resource_based.models import CustomResource
from booking.resource_based.models import ResourcePool
from booking.resource_based.models import ResourceRequirement
from booking.views import BackMixin, BreadcrumbMixin
from booking.views import LoginRequiredMixin, EditorRequriedMixin
from itertools import chain

import booking.models as booking_models
import booking.resource_based.forms as rb_forms


class ManageTimesView(DetailView):
    model = booking_models.Product
    template_name = 'eventtime/list.html'


class CreateTimeView(CreateView):
    model = booking_models.EventTime
    template_name = 'eventtime/create.html'
    _product = None

    fields = ('product', 'has_specific_time', 'start', 'end', 'notes')

    def get_product(self):
        if not self._product:
            try:
                self._product = booking_models.Product.objects.get(
                    pk=self.kwargs.get('product_pk', -1)
                )
            except:
                raise Http404
        return self._product

    def today_at_8_00(self):
        dt = timezone.datetime.combine(
            timezone.now().date(), datetime.time(8)
        )
        return timezone.make_aware(dt)

    def today_at_16_00(self):
        dt = timezone.datetime.combine(
            timezone.now().date(), datetime.time(16)
        )
        return timezone.make_aware(dt)

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()

        kwargs['initial']['product'] = self.kwargs.get('product_pk', -1)

        if 'start' not in kwargs['initial']:
            kwargs['initial']['start'] = self.today_at_8_00()

        if 'end' not in kwargs['initial']:
            duration = self.get_product().duration_in_minutes

            if duration > 0:
                end = kwargs['initial']['start'] + datetime.timedelta(
                    minutes=duration
                )
            else:
                end = self.today_at_16_00()

            kwargs['initial']['end'] = end

        form = form_class(**kwargs)

        form.fields['has_specific_time'].coerce = lambda x: x == 'True'

        return form

    def get_context_data(self, **kwargs):
        if self.request.method == "GET":
            if self.get_product().duration_in_minutes > 0:
                time_mode = "use_duration"
            else:
                time_mode = "time_and_date"
        else:
            time_mode = self.request.POST.get("time_mode")

        return super(CreateTimeView, self).get_context_data(
            product=self.get_product(),
            time_mode_value=time_mode,
            **kwargs
        )

    def form_valid(self, *args, **kwargs):
        response = super(CreateTimeView, self).form_valid(*args, **kwargs)
        self.object.update_availability()
        return response

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

    def get_form_kwargs(self):
        kwargs = super(CreateTimesFromRulesView, self).get_form_kwargs()

        if self.request.method == "GET":
            # Calculate end time from duration in minutes
            if self.get_product().duration_in_minutes > 0:
                # Duration is 8 am plus duration from product
                total_minutes = 8 * 60 + self.get_product().duration_in_minutes

                # Wrap if more than 24 hours
                if total_minutes > 24 * 60:
                    kwargs['initial']['extra_days'] = int(
                        total_minutes / (24 * 60)
                    )
                    total_minutes = total_minutes % (24 * 60)

                kwargs['initial']['end_time'] = '%02d:%02d' % (
                    int(total_minutes / 60),
                    total_minutes % 60
                )

        return kwargs

    def get_context_data(self, **kwargs):
        return super(CreateTimesFromRulesView, self).get_context_data(
            product=self.get_product(),
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

            if (
                start.hour == 0 and start.minute == 0 and
                end.hour == 0 and end.minute == 0
            ):
                has_specific_time = False
            else:
                has_specific_time = True

            d = cls(
                product=product,
                start=start,
                end=end,
                has_specific_time=has_specific_time,
                notes='',
            )
            d.save()
            d.update_availability()

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
        time_mode = self.request.POST.get("has_specific_time")
        if not time_mode:
            if not self.object.has_specific_time:
                time_mode = "full_days"
            elif self.object.duration_matches_product:
                time_mode = "use_duration"
            else:
                time_mode = "time_and_date"

        return super(EditTimeView, self).get_context_data(
            product=self.object.product,
            time_mode_value=time_mode,
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
            self.object.make_visit()

            booking_models.log_action(
                self.request.user,
                self.object.visit,
                booking_models.LOGACTION_CREATE,
                _(u'Besøg oprettet')
            )

            return redirect(self.get_success_url())
        else:
            # Do same thing as for get method
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)

    def get_success_url(self):
        return reverse('visit-view', args=[self.object.visit.pk])


class ResourceCreateView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                         FormView):
    template_name = "resource/typeform.html"
    form_class = ResourceTypeForm
    just_preserve_back = True

    def get_form_kwargs(self):
        kwargs = super(ResourceCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            typeId = int(form.cleaned_data['type'])
            unitId = int(form.cleaned_data['unit'].pk)

            return self.redirect(reverse(
                'resource-create-type',
                kwargs={'type': typeId, 'unit': unitId}
            ))

        return self.render_to_response(
            self.get_context_data(**context)
        )

    @staticmethod
    def build_breadcrumbs():
        breadcrumbs = ResourceListView.build_breadcrumbs()
        breadcrumbs.append({'text': _(u'Opret ressource')})
        return breadcrumbs


class ResourceDetailView(BreadcrumbMixin, EditorRequriedMixin, TemplateView):
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

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(resource):
        breadcrumbs = ResourceListView.build_breadcrumbs()
        breadcrumbs.append({
            'url': reverse('resource-view', args=[resource.id]),
            'text': unicode(resource)
        })
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context.update(kwargs)
        return super(ResourceDetailView, self).get_context_data(**context)


class ResourceListView(BreadcrumbMixin, EditorRequriedMixin, ListView):
    model = Resource
    template_name = "resource/list.html"

    def get_context_object_name(self, queryset):
        return "resources"

    def get_queryset(self):
        unit_qs = self.request.user.userprofile.get_unit_queryset()
        return chain(
            RoomResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('room__name'),
            ItemResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('name'),
            VehicleResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('name'),
            TeacherResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('user__first_name', 'user__last_name'),
            HostResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('user__first_name', 'user__last_name'),
            CustomResource.objects.filter(
                organizationalunit=unit_qs
            ).order_by('name')
        )

    @staticmethod
    def build_breadcrumbs():
        breadcrumbs = [
            {
                'url': reverse('resource-list'),
                'text': _(u'Administrér ressourcer')
            }
        ]
        return breadcrumbs


class ResourceUpdateView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                         UpdateView):
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

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(resource):
        if resource.pk:
            breadcrumbs = ResourceDetailView.build_breadcrumbs(resource)
            breadcrumbs.append({'text': _(u'Redigér')})
        else:
            breadcrumbs = ResourceListView.build_breadcrumbs()
            breadcrumbs.append({'text': _(u'Opret ressource')})
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = {}
        context['object'] = self.object
        context['ResourceType'] = ResourceType
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


class ResourceDeleteView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                         DeleteView):
    success_url = reverse_lazy('resource-list')
    back_on_success = False

    def get_template_names(self):
        return ['resource/delete.html']

    def get_object(self):
        return Resource.get_subclass_instance(self.kwargs.get("pk"))

    def get_breadcrumb_args(self):
        return [self.object]

    @staticmethod
    def build_breadcrumbs(resource):
        breadcrumbs = ResourceDetailView.build_breadcrumbs(resource)
        breadcrumbs.append({'text': _(u'Slet')})
        return breadcrumbs


class ResourcePoolCreateView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                             FormView):
    template_name = "resourcepool/typeform.html"
    form_class = ResourcePoolTypeForm
    just_preserve_back = True

    def get_form_kwargs(self):
        kwargs = super(ResourcePoolCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        context = {'form': form}
        context.update(kwargs)
        if form.is_valid():
            typeId = int(form.cleaned_data['type'])
            unitId = int(form.cleaned_data['unit'].pk)

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


class ResourcePoolDetailView(BreadcrumbMixin, EditorRequriedMixin, DetailView):
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


class ResourcePoolListView(BreadcrumbMixin, EditorRequriedMixin, ListView):
    model = ResourcePool
    template_name = "resourcepool/list.html"

    def get_queryset(self):
        qs = super(ResourcePoolListView, self).get_queryset()
        unit_qs = self.request.user.userprofile.get_unit_queryset()
        return qs.filter(organizationalunit=unit_qs).order_by(
            'resource_type__name', 'name'
        )

    def get_context_object_name(self, queryset):
        return "resourcepools"

    def get_breadcrumbs(self):
        return [
            {'text': _(u'Ressourcegrupper')}
        ]


class ResourcePoolUpdateView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                             UpdateView):
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
            breadcrumbs.append({'text': _(u'Opret ressourcegruppe')})
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


class ResourcePoolDeleteView(BackMixin, BreadcrumbMixin, EditorRequriedMixin,
                             DeleteView):
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

    def get_context_data(self, **kwargs):
        context = {}
        context['affected_visits'] = Visit.objects.filter(
            visitresource__resource_requirement__resource_pool=self.object
        ).distinct()
        context.update(kwargs)
        return super(ResourcePoolDeleteView, self).get_context_data(
            **context
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


class ResourceRequirementConfirmMixin(object):
    template_name = 'resourcerequirement/confirm.html'

    def get_form(self, form_class=None):
        form = super(ResourceRequirementConfirmMixin, self).\
            get_form(form_class)
        for name, field in form.fields.iteritems():
            field.widget = HiddenInput()
        return form

    def get_form_kwargs(self):
        kwargs = super(ResourceRequirementConfirmMixin, self).\
            get_form_kwargs()
        kwargs['product'] = self.product
        kwargs['initial'].update({
            'resource_pool': self.request.GET.get('resource_pool'),
            'required_amount': self.request.GET.get('required_amount')
        })
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        for eventtime in self.product.booked_eventtimes():
            eventtime.visit.autoassign_resources()
        return redirect(
            reverse('resourcerequirement-list', args=[self.object.product.id])
        )

    def get_context_data(self, **kwargs):
        resource_pool = ResourcePool.objects.get(
            id=self.request.GET.get('resource_pool')
        )
        required_amount = int(self.request.GET.get('required_amount'))
        old_amount = self.get_old_amount()
        visit_data = []
        for eventtime in self.product.booked_eventtimes():
            data = {
                'visit': eventtime.visit,
                'eventtime': eventtime,
                'assigned_count': self.get_assigned_count(eventtime.visit),
                'available': eventtime.visit.
                resources_available_for_autoassign(resource_pool)
            }
            data['insufficient'] = len(data['available']) + old_amount < \
                required_amount
            visit_data.append(data)

        context = {
            'resource_pool': resource_pool,
            'required_amount': required_amount,
            'old_amount': old_amount,
            'delta': required_amount - old_amount,
            'visit_data': visit_data
        }
        context.update(kwargs)
        return super(ResourceRequirementConfirmMixin, self).get_context_data(
            **context
        )

    def get_old_amount(self):
        return 0

    def get_assigned_count(self, visit):
        return 0


class ResourceRequirementCreateView(BackMixin, BreadcrumbMixin,
                                    EditorRequriedMixin, CreateView):
    model = ResourceRequirement
    form_class = EditResourceRequirementForm
    just_preserve_back = True
    template_name = 'resourcerequirement/form.html'

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

    def get_context_data(self, **kwargs):
        context = {}
        context['product'] = self.product
        context.update(kwargs)
        return super(ResourceRequirementCreateView, self).get_context_data(
            **context
        )

    def form_valid(self, form):
        if self.product.booked_eventtimes().count() > 0:
            return self.redirect(
                reverse(
                    'resourcerequirement-create-confirm',
                    args=[self.product.id]
                ) + "?resource_pool=%s&required_amount=%d" % (
                    form.cleaned_data['resource_pool'].id,
                    form.cleaned_data['required_amount']
                )
            )
        else:
            self.object = form.save()
            return redirect(
                reverse(
                    'resourcerequirement-list',
                    args=[self.object.product.id]
                )
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


class ResourceRequirementCreateConfirmView(
    ResourceRequirementConfirmMixin, ResourceRequirementCreateView
):
    pass


class ResourceRequirementUpdateView(BackMixin, BreadcrumbMixin,
                                    EditorRequriedMixin, UpdateView):
    model = ResourceRequirement
    form_class = EditResourceRequirementForm
    just_preserve_back = True
    template_name = 'resourcerequirement/form.html'
    required_amount = None

    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        self.required_amount = self.object.required_amount
        return super(ResourceRequirementUpdateView, self).dispatch(
            *args, **kwargs
        )

    def get_form_kwargs(self):
        kwargs = super(ResourceRequirementUpdateView, self).get_form_kwargs()
        kwargs['product'] = self.object.product
        return kwargs

    @property
    def product(self):
        return self.object.product

    def get_context_data(self, **kwargs):
        context = {}
        context['product'] = self.object.product
        context.update(kwargs)
        return super(ResourceRequirementUpdateView, self).get_context_data(
            **context
        )

    def form_valid(self, form):
        new_required_amount = int(form.cleaned_data['required_amount'])
        if new_required_amount > self.required_amount and \
                self.product.booked_eventtimes().count() > 0:
            return self.redirect(
                reverse(
                    'resourcerequirement-edit-confirm',
                    args=[self.product.id, self.object.id]
                ) + "?resource_pool=%s&required_amount=%d" % (
                    form.cleaned_data['resource_pool'].id,
                    new_required_amount
                )
            )
        else:
            self.object = form.save()
            for eventtime in self.product.booked_eventtimes():
                eventtime.visit.resources_updated()
            return redirect(
                reverse(
                    'resourcerequirement-list',
                    args=[self.object.product.id]
                )
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
                'text': unicode(self.product)
            },
            {'text': _(u'Redigér ressourcebehov')}
        ]


class ResourceRequirementUpdateConfirmView(
    ResourceRequirementConfirmMixin, ResourceRequirementUpdateView
):
    def get_old_amount(self):
        return self.object.required_amount

    def get_assigned_count(self, visit):
        return visit.resources_assigned(self.object).count()


class ResourceRequirementListView(BreadcrumbMixin, EditorRequriedMixin,
                                  ListView):
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


class ResourceRequirementDeleteView(BackMixin, BreadcrumbMixin,
                                    EditorRequriedMixin, DeleteView):
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

    def delete(self, *args, **kwargs):
        product = self.get_object().product
        response = super(ResourceRequirementDeleteView, self).delete(
            *args, **kwargs
        )
        for eventtime in product.booked_eventtimes():
            eventtime.visit.resources_updated()
        return response


class VisitResourceEditView(EditorRequriedMixin, FormView):
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
        self.visit.resources_updated()
        return super(VisitResourceEditView, self).form_valid(form)

    def get_success_url(self):
        return reverse('visit-view', args=[self.visit.id])


class CalRelatedMixin(object):
    rel_obj = None

    def get_calendar(self):
        rel_obj = self.get_calendar_rel_object()

        if not rel_obj.calendar:
            raise Http404(_("Ingen kalender fundet for %s") % rel_obj)

        return rel_obj.calendar

    def get_calendar_rel_object(self):
        related_kwargs_name = self.kwargs.get('related_kwargs_name', 'pk')
        related_model = self.kwargs.get(
            'related_model', booking_models.Resource
        )
        pk = self.kwargs.get(related_kwargs_name)
        queryset = related_model.objects.filter(pk=pk)
        try:
            # Get the single item from the filtered queryset
            self.rel_obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return self.rel_obj

    def get_context_data(self, **kwargs):
        prefix = self.kwargs.get('reverse_prefix', '')

        return super(CalRelatedMixin, self).get_context_data(
            reverses={
                x.replace('-', '_'): prefix + x for x in (
                    'calendar',
                    'calendar-create',
                    'calendar-delete',
                    'calendar-event-create',
                    'calendar-event-edit',
                    'calendar-event-delete',
                )
            },
            **kwargs
        )


class CalendarView(LoginRequiredMixin, CalRelatedMixin, DetailView):
    template_name = 'calendar/calendar.html'
    rel_model_class = booking_models.Resource

    def get_object(self, queryset=None):
        return self.get_calendar()

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
            date = x.start.astimezone(
                timezone.get_current_timezone()
            ).date()
            # Add event to all the days it spans
            delta = x.end - x.start + datetime.timedelta(hours=24, seconds=-1)
            for y in range(0, delta.days):
                key = date.isoformat()
                if key in events_by_date:
                    events_by_date[key].append(x.day_marker(date))
                date = date + datetime.timedelta(days=1)

        res = calendar.resource if hasattr(calendar, 'resource') else None
        prod = calendar.product if hasattr(calendar, 'product') else None

        if hasattr(calendar, 'resource'):
            bt = calendar.resource.occupied_eventtimes(start_dt, end_dt)
        elif hasattr(calendar, 'product'):
            bt = calendar.product.occupied_eventtimes(start_dt, end_dt)
        else:
            bt = None

        return super(CalendarView, self).get_context_data(
            calendar=calendar,
            resource=res,
            product=prod,
            month=first_of_the_month,
            next_month=first_of_the_month + datetime.timedelta(days=31),
            prev_month=first_of_the_month - datetime.timedelta(days=1),
            calendar_weeks=weeks,
            available=calendar.calendarevent_set.filter(
                availability=booking_models.CalendarEvent.AVAILABLE
            ).order_by("start", "end"),
            unavailable=calendar.calendarevent_set.filter(
                availability=booking_models.CalendarEvent.NOT_AVAILABLE
            ).order_by("start", "end"),
            booked_times=bt,
            **kwargs
        )


class CalendarCreateView(LoginRequiredMixin, CalRelatedMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        rel_obj = self.get_calendar_rel_object()

        # Create empty calendar if one does not exist
        rel_obj.make_calendar()

        return reverse(
            self.kwargs.get('reverse_prefix', '') + 'calendar',
            args=[rel_obj.pk]
        )


class CalendarDeleteView(LoginRequiredMixin, CalRelatedMixin, DeleteView):
    template_name = 'calendar/delete.html'

    def get_object(self, queryset=None):
        rel_obj = self.get_calendar_rel_object()
        return rel_obj.calendar

    def get_success_url(self):
        if self.kwargs.get('reverse_prefix'):
            reverse_name = 'product-view'
        else:
            reverse_name = 'resource-view'

        return reverse(reverse_name, args=[self.rel_obj.pk])


class CalendarEventCreateView(LoginRequiredMixin, CalRelatedMixin, CreateView):
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

    labels = {
        'start': "Blahblah"
    }

    widgets = {
        'title': TextInput(attrs={'class': 'form-control input-sm'})
    }

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        try:
            calendar = self.get_calendar()
        except:
            raise Http404

        if self.request.method == "GET":
            kwargs['initial']['calendar'] = calendar.pk

            midnight = timezone.make_aware(
                timezone.datetime.combine(
                    timezone.now().date(),
                    datetime.time()
                )
            )

            kwargs['initial']['start'] = midnight + datetime.timedelta(
                hours=8
            )
            kwargs['initial']['end'] = midnight + datetime.timedelta(
                hours=16
            )
        form = form_class(**kwargs)
        for fieldname, widget in self.widgets.iteritems():
            form.fields[fieldname].widget = widget

        return form

    def get_context_data(self, **kwargs):
        time_choices = []
        for x in range(0, 24):
            time_choices.append("%02d:00" % x)
            time_choices.append("%02d:30" % x)
        time_choices.append("24:00")
        return super(CalendarEventCreateView, self).get_context_data(
            time_choices=time_choices,
            default_all_day=self.request.method == "GET",
            **kwargs
        )

    def get_success_url(self):
        return reverse(
            self.kwargs.get('reverse_prefix', '') + 'calendar',
            args=[self.rel_obj.pk]
        )


class CalendarEventUpdateView(LoginRequiredMixin, CalRelatedMixin, UpdateView):
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

    start_str = ""
    end_str = ""

    def get_object(self, *args, **kwargs):
        self.rel_obj = self.get_calendar_rel_object()

        return super(CalendarEventUpdateView, self).get_object(*args, **kwargs)

    def get_context_data(self, **kwargs):
        return super(CalendarEventUpdateView, self).get_context_data(
            start_time=self.start_str,
            end_time=self.end_str,
            **kwargs
        )

    def get_success_url(self):
        return reverse(
            self.kwargs.get('reverse_prefix', '') + 'calendar',
            args=[self.rel_obj.pk]
        )


class CalendarEventDeleteView(LoginRequiredMixin, CalRelatedMixin, DeleteView):
    model = booking_models.CalendarEvent
    template_name = 'calendar_event_confirm_delete.html'

    def get_object(self, *args, **kwargs):
        self.rel_obj = self.get_calendar_rel_object()

        return super(CalendarEventDeleteView, self).get_object(*args, **kwargs)

    def get_success_url(self):
        return reverse(
            self.kwargs.get('reverse_prefix', '') + 'calendar',
            args=[self.rel_obj.pk]
        )
