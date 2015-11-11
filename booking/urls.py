from django.conf import settings
from django.conf.urls import patterns, url

from .views import MainPageView


urlpatterns = patterns(

    '',
    url(r'^$', MainPageView.as_view(), name='index'),
)
