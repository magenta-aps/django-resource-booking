# encoding: utf-8
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView
from booking.models import OrganizationalUnit
from booking.resource_based.forms import ResourceTypeForm, EditResourceForm
from booking.resource_based.forms import ResourcePoolTypeForm
from booking.resource_based.forms import EditResourcePoolForm
from booking.resource_based.models import Resource, ResourceType
from booking.resource_based.models import ItemResource, RoomResource
from booking.resource_based.models import TeacherResource, VehicleResource
from booking.resource_based.models import ResourcePool
from booking.views import BackMixin, BreadcrumbMixin
from itertools import chain

import booking.models as booking_models


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

            return self.redirect(reverse(
                'resourcepool-create-type',
                kwargs={'type': typeId, 'unit': unitId}
            ))

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
                self.object = form.save(commit=False)
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
