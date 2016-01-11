from django.conf.urls import patterns, url

from .views import MainPageView
from booking.views import SearchView, RrulestrView
from booking.views import EditVisit, VisitDetailView
from django.views.generic import TemplateView

js_info_dict = {
    'packages': ('recurrence', ),
}

urlpatterns = patterns(

    '',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    url(r'^$', MainPageView.as_view(), name='index'),

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

    url(r'^visit/create$',
        EditVisit.as_view(success_url='create'), name='visit_create'),
    url(r'^visit/(?P<pk>[0-9]+)/?',
        VisitDetailView.as_view(), name='visit'),
    url(r'^visit/(?P<pk>[0-9]+)/edit$',
        EditVisit.as_view(), name='visit_edit'),

    # Ajax api
    url(r'^jsapi/rrulestr$', RrulestrView.as_view(), name='jsapi_rrulestr')
)
