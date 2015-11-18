from django.conf.urls import patterns, url

from .views import MainPageView
from django.views.generic import TemplateView

urlpatterns = patterns(

    '',
    url(r'^$', MainPageView.as_view(), name='index'),

    url(r'^manage$', TemplateView.as_view(
        template_name='mockup_templates/manage-list.html')),
    url(r'^manage-item$', TemplateView.as_view(
        template_name='mockup_templates/manage-item.html')),
    url(r'^booking-list$', TemplateView.as_view(
        template_name='mockup_templates/booking-list.html')),
    url(r'^booking-details$', TemplateView.as_view(
        template_name='mockup_templates/booking-details.html')),
    url(r'^new-item$', TemplateView.as_view(
        template_name='mockup_templates/new-item.html')),
    url(r'^search-list$', TemplateView.as_view(
        template_name='mockup_templates/search-list.html')),
    url(r'^item$', TemplateView.as_view(
        template_name='mockup_templates/item.html')),
    url(r'^book-it$', TemplateView.as_view(
        template_name='mockup_templates/book-it.html')),
    url(r'^thx-for-booking$', TemplateView.as_view(
        template_name='mockup_templates/thx-for-booking.html'))

)
