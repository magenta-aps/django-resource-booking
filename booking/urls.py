from django.conf.urls import patterns, url, include
from django.conf.urls.static import static
from django.conf import settings

from .views import MainPageView

from booking.views import PostcodeView, SchoolView
from booking.views import RrulestrView
from booking.views import EditResourceInitialView, ResourceDetailView
from booking.views import BookingView, BookingSuccessView, BookingSearchView
from booking.views import EditOtherResourceView, OtherResourceDetailView
from booking.views import EditVisitView, VisitDetailView
from booking.views import VisitNotifyView, VisitNotifySuccessView
from booking.views import SearchView, EmbedcodesView
from booking.views import EmailTemplateListView, EmailTemplateEditView
from booking.views import EmailTemplateDetailView, EmailTemplateDeleteView
from booking.views import BookingDetailView, BookingNotifyView
from booking.views import BookingNotifySuccessView
from booking.views import ChangeBookingStatusView
from booking.views import ChangeBookingTeachersView, ChangeBookingHostsView
from booking.views import ChangeBookingRoomsView, ChangeBookingCommentsView
from booking.views import BookingAddLogEntryView

from django.views.generic import TemplateView

js_info_dict = {
    'packages': ('recurrence', ),
}

urlpatterns = patterns(

    '',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    url(r'^$', MainPageView.as_view(), name='index'),

    # Djangosaml2
    (r'^saml2/', include('djangosaml2.urls')),

    # Main search page
    url(r'^search', SearchView.as_view(), name='search'),

    # iframe-friendly main page with search bar
    url(r'^iframe$', TemplateView.as_view(
        template_name='iframe-index.html'),
        name='iframe_search'),

    url(r'^resource/create$',
        EditResourceInitialView.as_view(),
        name='resource-create'),
    url(r'^resource/(?P<pk>[0-9]+)/$',
        ResourceDetailView.as_view(),
        name='resource-view'),
    url(r'^resource/(?P<pk>[0-9]+)/edit$',
        EditResourceInitialView.as_view(),
        name='resource-edit'),

    url(r'^otherresource/create$',
        EditOtherResourceView.as_view(success_url='create'),
        name='otherresource-create'),
    url(r'^otherresource/(?P<pk>[0-9]+)/?$',
        OtherResourceDetailView.as_view(),
        name='otherresource-view'),
    url(r'^otherresource/(?P<pk>[0-9]+)/edit$',
        EditOtherResourceView.as_view(), name='otherresource-edit'),
    url(r'^otherresource/(?P<pk>[0-9]+)/clone$',
        EditOtherResourceView.as_view(), {'clone': True},
        name='otherresource-clone'),

    url(r'^visit/create$',
        EditVisitView.as_view(success_url='create'),
        name='visit-create'),
    url(r'^visit/(?P<pk>[0-9]+)/?$',
        VisitDetailView.as_view(),
        name='visit-view'),
    url(r'^visit/(?P<pk>[0-9]+)/edit$',
        EditVisitView.as_view(),
        name='visit-edit'),
    url(r'^visit/(?P<pk>[0-9]+)/clone$',
        EditVisitView.as_view(),
        {'clone': True},
        name='visit-clone'),
    url(r'^visit/(?P<visit>[0-9]+)/book$',
        BookingView.as_view(),
        name='visit-book'),
    url(r'^visit/(?P<visit>[0-9]+)/book/success$',
        BookingSuccessView.as_view(),
        name='visit-book-success'),
    url(r'^visit/(?P<visit>[0-9]+)/notify$',
        VisitNotifyView.as_view(),
        name='visit-notify'),
    url(r'^visit/(?P<visit>[0-9]+)/notify/success$',
        VisitNotifySuccessView.as_view(),
        name='visit-notify-success'),

    url(r'^booking/(?P<pk>[0-9]+)/?$',
        BookingDetailView.as_view(),
        name='booking-view'),
    url(r'^booking/(?P<pk>[0-9]+)/change_status/?$',
        ChangeBookingStatusView.as_view(),
        name='change-booking-status'),
    url(r'^booking/(?P<pk>[0-9]+)/change_teachers/?$',
        ChangeBookingTeachersView.as_view(),
        name='change-booking-teachers'),
    url(r'^booking/(?P<pk>[0-9]+)/change_hosts/?$',
        ChangeBookingHostsView.as_view(),
        name='change-booking-hosts'),
    url(r'^booking/(?P<pk>[0-9]+)/change_rooms/?$',
        ChangeBookingRoomsView.as_view(),
        name='change-booking-rooms'),
    url(r'^booking/(?P<pk>[0-9]+)/change_comments/?$',
        ChangeBookingCommentsView.as_view(),
        name='change-booking-comments'),
    url(r'^booking/(?P<pk>[0-9]+)/add_logentry/?$',
        BookingAddLogEntryView.as_view(),
        name='booking-add-logentry'),
    url(r'^booking/search$',
        BookingSearchView.as_view(),
        name='booking-search'),

    url(r'^booking/(?P<pk>[0-9]+)/notify$',
        BookingNotifyView.as_view(),
        name='booking-notify'),
    url(r'^booking/(?P<visit>[0-9]+)/notify/success$',
        BookingNotifySuccessView.as_view(),
        name='booking-notify-success'),

    # Ajax api
    url(r'^jsapi/rrulestr$', RrulestrView.as_view(), name='jsapi_rrulestr'),

    url(r'^tinymce/', include('tinymce.urls')),


    url(r'^postcode/(?P<code>[0-9]{4})$',
        PostcodeView.as_view(),
        name='postcode'),
    url(r'^school',
        SchoolView.as_view(),
        name='school'),

    url(r'^embedcodes/(?P<embed_url>.*)$',
        EmbedcodesView.as_view(),
        name='embedcodes'),

    url(r'^emailtemplate/?$',
        EmailTemplateListView.as_view(),
        name='emailtemplate-list'),
    url(r'^emailtemplate/create$',
        EmailTemplateEditView.as_view(),
        name='emailtemplate-create'),
    url(r'^emailtemplate/(?P<pk>[0-9]+)/edit$',
        EmailTemplateEditView.as_view(),
        name='emailtemplate-edit'),
    url(r'^emailtemplate/(?P<pk>[0-9]+)/clone$',
        EmailTemplateEditView.as_view(), {'clone': True},
        name='emailtemplate-clone'),
    url(r'^emailtemplate/(?P<pk>[0-9]+)/?$',
        EmailTemplateDetailView.as_view(),
        name='emailtemplate-view'),
    url(r'^emailtemplate/(?P<pk>[0-9]+)/delete$',
        EmailTemplateDeleteView.as_view(),
        name='emailtemplate-delete')

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

embed_views = [
    'index',
    'visit-view',
    'otherresource-view',
    'search',
]

embedpatterns = []
for x in urlpatterns:
    if hasattr(x, 'name') and x.name in embed_views:
        # Tell template system that these URLs can be embedded
        x.default_args['can_be_embedded'] = True

        # Add a corresponding embed URL
        embedpatterns.append(
            url(
                '^(?P<embed>embed/)' + x.regex.pattern[1:],
                x._callback,
                name=x.name + '-embed'
            )
        )

urlpatterns += embedpatterns
