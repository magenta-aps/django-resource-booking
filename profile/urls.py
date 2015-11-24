import django.contrib.auth.views as auth_views

from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns(

    '',
    url(r'^$', TemplateView.as_view(
        template_name='profile/profile.html')),
    url(r'^login/', auth_views.login,
        {'template_name': 'profile/login.html'}),
    url(r'^logout/', auth_views.logout,
        {'template_name': 'profile/logout.html'}),

)
