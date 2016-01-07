import django.contrib.auth.views as auth_views

from django.conf.urls import patterns, url
from profile.views import ProfileView

urlpatterns = patterns(

    '',
    url(r'^$', ProfileView.as_view(
        template_name='profile/profile.html')),
    url(r'^login/', auth_views.login,
        {'template_name': 'profile/login.html'}),
    url(r'^logout/', auth_views.logout,
        {'template_name': 'profile/logout.html'}),

)
