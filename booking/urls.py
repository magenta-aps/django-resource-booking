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
from booking.views import BookingDetailView
from booking.views import SearchView

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

    url(r'^manage$', TemplateView.as_view(
        template_name='mockup_templates/manage-list.html'),
        name="mockup-manage-list"),
    url(r'^manage-item$', TemplateView.as_view(
        template_name='mockup_templates/manage-item.html'),
        name="mockup-manage-item"),
    url(r'^booking-list$', TemplateView.as_view(
        template_name='mockup_templates/booking-list.html'),
        name="mockup-booking-list"),
    url(r'^booking-details$', TemplateView.as_view(
        template_name='mockup_templates/booking-details.html'),
        name="mockup-booking-detail"),
    url(r'^new-item$', TemplateView.as_view(
        template_name='mockup_templates/new-item.html'),
        name="mockup-new-item"),
    url(r'^search-list$', TemplateView.as_view(
        template_name='mockup_templates/search-list.html'),
        name="mockup-search-list"),
    url(r'^item$', TemplateView.as_view(
        template_name='mockup_templates/item.html'),
        name="mockup-item"),
    url(r'^book-it$', TemplateView.as_view(
        template_name='mockup_templates/book-it.html'),
        name="mockup-book-it"),
    url(r'^thx-for-booking$', TemplateView.as_view(
        template_name='mockup_templates/thx-for-booking.html'),
        name="mockup-thx-for-booking"),

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

    url(r'^booking/(?P<pk>[0-9]+)/?$',
        BookingDetailView.as_view(),
        name='booking-view'),
    url(r'^booking/search$',
        BookingSearchView.as_view(),
        name='booking-search'),

    # Ajax api
    url(r'^jsapi/rrulestr$', RrulestrView.as_view(), name='jsapi_rrulestr'),

    url(r'^tinymce/', include('tinymce.urls')),


    url(r'^postcode/(?P<code>[0-9]{4})$',
        PostcodeView.as_view(),
        name='postcode'),
    url(r'^school',
        SchoolView.as_view(),
        name='school'),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
