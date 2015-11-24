from django.conf.urls import patterns, url

from .views import MainPageView
from booking.views import CreateUnitType, ListUnitType
from booking.views import EditUnitType, DeleteUnitType
from booking.views import CreateUnit, ListUnit, EditUnit, DeleteUnit


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
)
