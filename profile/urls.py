import django.contrib.auth.views as auth_views

from django.conf.urls import patterns, url
from profile.views import ProfileView, CreateUserView, UnitListView
from profile.views import DeleteUserView, UserListView
from profile.views import EmailLoginView
from profile.views import EditMyResourcesView

urlpatterns = patterns(

    '',
    url(r'^$', ProfileView.as_view(
        template_name='profile/profile.html'),
        name='user_profile'),
    url(r'^login/', auth_views.login,
        {'template_name': 'profile/login.html'},
        name='standard_login'),
    url(r'^email-login/(?P<slug>[a-f0-9-]+)(?P<dest_url>.*)',
        EmailLoginView.as_view(),
        name='email-login'
        ),
    url(r'^logout/',
        auth_views.logout,
        {'template_name': 'profile/logout.html'},
        name='logout'
        ),
    url(r'^user/create$',
        CreateUserView.as_view(
            template_name='profile/create_user.html',
            success_url='create'
        ),
        name='user_create'),
    url(r'^users/?$',
        UserListView.as_view(),
        name='user_list'),
    url(r'^user/(?P<pk>[0-9]+)/?$',
        CreateUserView.as_view(),
        name='user_edit'),
    url(r'^user/(?P<pk>[0-9]+)/delete/?$',
        DeleteUserView.as_view(),
        name='user_delete'),
    url(r'^units/$', UnitListView.as_view(
        template_name='profile/unit_list.html'
    ), name='unit_list'),

    url(r'^my_resources/?$',
        EditMyResourcesView.as_view(),
        name='my-resources'),
)
