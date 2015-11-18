from django.conf.urls import patterns, url

from .views import MainPageView
from booking.views import CreateUnitType, ListUnitType, EditUnitType, DeleteUnitType


urlpatterns = patterns(

    '',
    url(r'^$', MainPageView.as_view(), name='index'),

    url(r'^unittype/$', ListUnitType.as_view(), name='unittype_list'),
    url(r'^unittype/create$', CreateUnitType.as_view(), name='unittype_create'),
    url(r'^unittype/(?P<pk>[0-9]+)/?$', EditUnitType.as_view(), name='unittype_update'),
    url(r'^unittype/(?P<pk>[0-9]+)/edit$', EditUnitType.as_view(), name='unittype_update'),
    url(r'^unittype/(?P<pk>[0-9]+)/delete$', DeleteUnitType.as_view(), name='unittype_delete'),
)
