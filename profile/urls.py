import django.contrib.auth.views as auth_views

from django.conf.urls import patterns, url
from profile.views import ProfileView, CreateUserView

urlpatterns = patterns(

    '',
    url(r'^$', ProfileView.as_view(
        template_name='profile/profile.html')),
    url(r'^login/', auth_views.login,
        {'template_name': 'profile/login.html'}),
    url(r'^logout/', auth_views.logout,
        {'template_name': 'profile/logout.html'}),
    url(r'^user/create$', CreateUserView.as_view(
        template_name='profile/create_user.html',
        success_url='create'
    )),
    url(r'^user/(?P<pk>[0-9]+)/?$',
        CreateUserView.as_view(),
        name='user_edit'),

)
