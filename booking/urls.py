from django.conf.urls import patterns, url

from .views import MainPageView
from booking.views import CreateUnitType, ListUnitType
from booking.views import EditUnitType, DeleteUnitType
from booking.views import CreateUnit, ListUnit, EditUnit, DeleteUnit

from django.views.generic import TemplateView

urlpatterns = patterns(

    '',
    url(r'^$', MainPageView.as_view(), name='index'),

    url(r'^unittype/$',
        ListUnitType.as_view(), name='unittype_list'),
    url(r'^unittype/create$',
        CreateUnitType.as_view(), name='unittype_create'),
    url(r'^unittype/(?P<pk>[0-9]+)/?$',
        EditUnitType.as_view(), name='unittype_update'),
    url(r'^unittype/(?P<pk>[0-9]+)/edit$',
        EditUnitType.as_view(), name='unittype_update'),
    url(r'^unittype/(?P<pk>[0-9]+)/delete$',
        DeleteUnitType.as_view(), name='unittype_delete'),

    url(r'^unit/$',
        ListUnit.as_view(), name='unit_list'),
    url(r'^unit/create$',
        CreateUnit.as_view(), name='unit_create'),
    url(r'^unit/(?P<pk>[0-9]+)/?$',
        EditUnit.as_view(), name='unit_update'),
    url(r'^unit/(?P<pk>[0-9]+)/edit$',
        EditUnit.as_view(), name='unit_update'),
    url(r'^unit/(?P<pk>[0-9]+)/delete$',
        DeleteUnit.as_view(), name='unit_delete'),

    url(r'^manage$', TemplateView.as_view(
        template_name='mockup_templates/manage-list.html')),
    url(r'^manage-item$', TemplateView.as_view(
        template_name='mockup_templates/manage-item.html')),
    url(r'^booking-list$', TemplateView.as_view(
        template_name='mockup_templates/booking-list.html')),
    url(r'^booking-details$', TemplateView.as_view(
        template_name='mockup_templates/booking-details.html')),
    url(r'^new-item$', TemplateView.as_view(
        template_name='mockup_templates/new-item.html')),
    url(r'^search-list$', TemplateView.as_view(
        template_name='mockup_templates/search-list.html')),
    url(r'^item$', TemplateView.as_view(
        template_name='mockup_templates/item.html')),
    url(r'^book-it$', TemplateView.as_view(
        template_name='mockup_templates/book-it.html')),
    url(r'^thx-for-booking$', TemplateView.as_view(
        template_name='mockup_templates/thx-for-booking.html'))

)
