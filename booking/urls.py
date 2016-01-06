from django.conf.urls import patterns, url, include
from django.conf.urls.static import static
from django.conf import settings

from .views import MainPageView
from booking.views import EditVisit, VisitDetailView, SearchView
from booking.views import AdminSearchView, AdminIndexView, AdminVisitDetailView
from django.views.generic import TemplateView

urlpatterns = patterns(

    '',
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

    url(r'^visit/create$',
        EditVisit.as_view(), name='visit_create'),
    url(r'^visit/(?P<pk>[0-9]+)/?$',
        VisitDetailView.as_view(), name='visit'),
    url(r'^visit/(?P<pk>[0-9]+)/edit$',
        EditVisit.as_view(), name='visit_edit'),
    url(r'^visit/(?P<pk>[0-9]+)/clone$',
        EditVisit.as_view(), {'clone': True}, name='visit_clone'),

    url(r'^tinymce/', include('tinymce.urls')),

    url(r'^fokusadmin/?$', AdminIndexView.as_view(), name='admin-index'),
    url(r'^fokusadmin/search/?$', AdminSearchView.as_view(),
        name='admin-search'),
    url(r'^fokusadmin/visit/(?P<pk>[0-9]+)/?$', AdminVisitDetailView.as_view(),
        name='admin-visit')

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
