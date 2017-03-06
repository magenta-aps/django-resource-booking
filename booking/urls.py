from django.conf.urls import patterns, url, include
from django.conf.urls.static import static
from django.conf import settings
from django.core.urlresolvers import RegexURLPattern
from django.views.decorators.clickjacking import xframe_options_exempt

from booking.views import MainPageView, VisitNotifyView

from booking.views import PostcodeView, SchoolView, ProductInquireView
from booking.views import RrulestrView
from booking.views import ProductCustomListView
from booking.views import EditProductInitialView
from booking.views import BookingView, BookingSuccessView
from booking.views import VisitSearchView
from booking.views import EditProductView, ProductDetailView
from booking.views import EmailSuccessView, ProductInquireSuccessView
from booking.views import SearchView, EmbedcodesView

from booking.views import BookingNotifyView, BookingDetailView
from booking.views import BookingAcceptView
from booking.views import EmailTemplateListView, EmailTemplateEditView
from booking.views import EmailTemplateDetailView, EmailTemplateDeleteView
from booking.views import ChangeVisitEvalView
from booking.views import ChangeVisitStatusView
from booking.views import ChangeVisitStartTimeView
from booking.views import ChangeVisitResponsibleView
from booking.views import ChangeVisitTeachersView
from booking.views import ChangeVisitHostsView
from booking.views import ChangeVisitRoomsView
from booking.views import ChangeVisitCommentsView
from booking.views import ChangeVisitAutosendView
from booking.views import ResetVisitChangesView
from booking.views import BecomeTeacherView
from booking.views import DeclineTeacherView
from booking.views import BecomeHostView
from booking.views import DeclineHostView
from booking.views import EmailReplyView
from booking.views import VisitAddLogEntryView
from booking.views import VisitAddCommentView
from booking.views import VisitDetailView
from booking.views import VisitCustomListView
from booking.views import EvaluationOverviewView
from booking.views import VisitBookingCreateView
from booking.views import MultiProductVisitPromptView
from booking.views import MultiProductVisitTempCreateView
from booking.views import MultiProductVisitTempUpdateView
from booking.views import MultiProductVisitTempProductsView
from booking.views import MultiProductVisitTempConfirmView

from booking.resource_based.views import ResourceCreateView, ResourceDetailView
from booking.resource_based.views import ResourceListView, ResourceUpdateView
from booking.resource_based.views import ResourceDeleteView

from booking.resource_based.views import ResourcePoolCreateView
from booking.resource_based.views import ResourcePoolDetailView
from booking.resource_based.views import ResourcePoolListView
from booking.resource_based.views import ResourcePoolUpdateView
from booking.resource_based.views import ResourcePoolDeleteView

from booking.resource_based.views import ResourceRequirementCreateView
from booking.resource_based.views import ResourceRequirementUpdateView
from booking.resource_based.views import ResourceRequirementListView
from booking.resource_based.views import ResourceRequirementDeleteView

from booking.resource_based.views import VisitResourceEditView

import booking.views
import booking.models

from django.views.generic import TemplateView

js_info_dict = {
    'packages': ('recurrence', ),
}

calendarevent_kwargs = {'related_kwargs_name': 'res'}
product_calendar_kwargs = {
    'related_model': booking.models.Product,
    'reverse_prefix': 'product-'
}
product_calendarevent_kwargs = product_calendar_kwargs.copy()
product_calendarevent_kwargs['related_kwargs_name'] = 'prod'

urlpatterns = patterns(

    '',
    (r'^jsi18n$', 'django.views.i18n.javascript_catalog', js_info_dict),
    url(r'^$', MainPageView.as_view(), name='index'),

    # Main search page
    url(r'^search', SearchView.as_view(), name='search'),

    # iframe-friendly main page with search bar
    url(r'^iframe$', TemplateView.as_view(
        template_name='iframe-index.html'),
        name='iframe_search'),

    url(r'^product/create/?$',
        EditProductInitialView.as_view(),
        name='product-create'),
    url(r'^product/create/(?P<type>[0-9]+)/?$',
        EditProductView.as_view(success_url='create'),
        name='product-create-type'),
    url(r'^product/(?P<pk>[0-9]+)/?$',
        ProductDetailView.as_view(),
        name='product-view'),
    url(r'^product/(?P<pk>[0-9]+)/edit$',
        EditProductView.as_view(),
        name='product-edit'),
    url(r'^product/(?P<pk>[0-9]+)/clone$',
        EditProductView.as_view(),
        {'clone': True},
        name='product-clone'),
    url(r'^product/(?P<pk>[0-9]+)/simple_ressources$',
        booking.views.SimpleRessourcesView.as_view(),
        name='product-simple-ressources'),
    url(r'^product/(?P<pk>[0-9]+)/manage_times$',
        booking.views.ManageTimesView.as_view(),
        name='manage-times'),
    url(r'^product/(?P<product_pk>[0-9]+)/manage_times/create$',
        booking.views.CreateTimeView.as_view(),
        name='create-time'),
    url(r'^product/(?P<product_pk>[0-9]+)/time/(?P<pk>[0-9]+)$',
        booking.views.TimeDetailsView.as_view(),
        name='time-view'),
    url(r'^product/(?P<product_pk>[0-9]+)/manage_times/(?P<pk>[0-9]+)$',
        booking.views.EditTimeView.as_view(),
        name='edit-time'),
    url(r'^product/(?P<product_pk>[0-9]+)/manage_times/delete$',
        booking.views.DeleteTimesView.as_view(),
        name='delete-times'),
    url(r'^product/(?P<product_pk>[0-9]+)/manage_times/from_rules$',
        booking.views.CreateTimesFromRulesView.as_view(),
        name='times-from-rules'),
    url(r'^product/(?P<product>[0-9]+)/book$',
        BookingView.as_view(),
        name='product-book'),
    url(r'^product/(?P<pk>[0-9]+)/book/success$',
        BookingSuccessView.as_view(),
        name='product-book-success'),
    url(r'^product/(?P<product>[0-9]+)/inquire$',
        ProductInquireView.as_view(),
        name='product-inquire'),
    url(r'^product/(?P<product>[0-9]+)/inquire/success$',
        ProductInquireSuccessView.as_view(),
        name='product-inquire-success'),
    url(r'^product/customlist/?$',
        ProductCustomListView.as_view(),
        name='product-customlist'),
    url(r'^product/(?P<pk>[0-9]+)/notime/?$',
        MultiProductVisitPromptView.as_view(),
        name='product-book-notime'),

    url(r'^visit/(?P<pk>[0-9]+)/notify/?$',
        VisitNotifyView.as_view(),
        name='visit-notify'),
    url(r'^visit/(?P<pk>[0-9]+)/notify/success/?$',
        EmailSuccessView.as_view(),
        name='visit-notify-success'),

    url(r'^visit/(?P<pk>[0-9]+)/(?P<usertype>teacher|host+)?/?$',
        VisitDetailView.as_view(),
        name='visit-view'),
    url(r'visit/(?P<visit>[0-9]+)/book/?$',
        VisitBookingCreateView.as_view(),
        name='visit-booking-create'),
    url(r'^visit/(?P<pk>[0-9]+)/book/success$',
        BookingSuccessView.as_view(modal=False),
        name='visit-booking-success'),

    url(r'^booking/(?P<pk>[0-9]+)/?$',
        BookingDetailView.as_view(),
        name='booking-view'),
    url(r'^booking/accept/(?P<token>[0-9a-f-]+)/?$',
        BookingAcceptView.as_view(),
        name='booking-accept-view'),

    url(r'^visit/(?P<pk>[0-9]+)/change_status/?$',
        ChangeVisitStatusView.as_view(),
        name='change-visit-status'),
    url(r'^visit/(?P<visit_pk>[0-9]+)/change_starttime/?$',
        ChangeVisitStartTimeView.as_view(),
        name='change-visit-starttime'),
    url(r'^visit/(?P<pk>[0-9]+)/change_responsible/?$',
        ChangeVisitResponsibleView.as_view(),
        name='change-visit-responsible'),
    url(r'^visit/(?P<pk>[0-9]+)/change_teachers/?$',
        ChangeVisitTeachersView.as_view(),
        name='change-visit-teachers'),
    url(r'^visit/(?P<pk>[0-9]+)/change_hosts/?$',
        ChangeVisitHostsView.as_view(),
        name='change-visit-hosts'),
    url(r'^visit/(?P<pk>[0-9]+)/change_rooms/?$',
        ChangeVisitRoomsView.as_view(),
        name='change-visit-rooms'),
    url(r'^visit/(?P<pk>[0-9]+)/change_comments/?$',
        ChangeVisitCommentsView.as_view(),
        name='change-visit-comments'),
    url(r'^visit/(?P<pk>[0-9]+)/change_evaluation_link/?$',
        ChangeVisitEvalView.as_view(),
        name='change-visit-eval'),
    url(r'^visit/(?P<pk>[0-9]+)/add_logentry/?$',
        VisitAddLogEntryView.as_view(),
        name='visit-add-logentry'),
    url(r'^visit/(?P<pk>[0-9]+)/add_comment/?$',
        VisitAddCommentView.as_view(),
        name='visit-add-comment'),
    url(r'^visit/(?P<pk>[0-9]+)/become_teacher/?$',
        BecomeTeacherView.as_view(),
        name='become-teacher'),
    url(r'^visit/(?P<pk>[0-9]+)/decline_teacher/?$',
        DeclineTeacherView.as_view(),
        name='decline-teacher'),
    url(r'^visit/(?P<pk>[0-9]+)/become_host/?$',
        BecomeHostView.as_view(),
        name='become-host'),
    url(r'^visit/(?P<pk>[0-9]+)/decline_host/?$',
        DeclineHostView.as_view(),
        name='decline-host'),
    url(r'^visit/(?P<pk>[0-9]+)/reset_changes_marker/?$',
        ResetVisitChangesView.as_view(),
        name='visit-reset-changes-marker'),
    url(r'^visit/search$',
        VisitSearchView.as_view(),
        name='visit-search'),
    url(r'^visit/(?P<pk>[0-9]+)/change_autosend/?$',
        ChangeVisitAutosendView.as_view(),
        name='change-visit-autosend'),
    url(r'^visit/customlist/?$',
        VisitCustomListView.as_view(),
        name='visit-customlist'),

    url(r'^booking/(?P<pk>[0-9]+)/notify$',
        BookingNotifyView.as_view(),
        name='booking-notify'),
    url(r'^booking/(?P<product>[0-9]+)/notify/success$',
        EmailSuccessView.as_view(),
        name='booking-notify-success'),


    url(r'^mpv/create/?$',
        MultiProductVisitTempCreateView.as_view(),
        name='mpv-create'),
    url(r'^mpv/(?P<pk>[0-9]+)/date/?$',
        MultiProductVisitTempUpdateView.as_view(),
        name='mpv-edit-date'),
    url(r'^mpv/(?P<pk>[0-9]+)/products/?$',
        MultiProductVisitTempProductsView.as_view(),
        name='mpv-edit-products'),
    url(r'^mpv/(?P<pk>[0-9]+)/confirm/?$',
        MultiProductVisitTempConfirmView.as_view(),
        name='mpv-confirm'),

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
        name='emailtemplate-delete'),

    url(r'^reply-to-email/(?P<reply_nonce>[0-9a-f-]{36})',
        EmailReplyView.as_view(),
        name='reply-to-email'),

    url(r'^evaluations/?',
        EvaluationOverviewView.as_view(),
        name='evaluations'),

    url(r'^resource/create/?$',
        ResourceCreateView.as_view(),
        name='resource-create'),
    url(r'^resource/create/(?P<type>[0-9]+)/(?P<unit>[0-9]+)/?$',
        ResourceUpdateView.as_view(success_url='create'),
        name='resource-create-type'),
    url(r'^resource/(?P<pk>[0-9]+)/?$',
        ResourceDetailView.as_view(),
        name='resource-view'),

    url(r'^resource/(?P<pk>[0-9]+)/calendar/?$',
        booking.views.CalendarView.as_view(),
        name='calendar'),
    url(r'^resource/(?P<pk>[0-9]+)/create_calendar/?$',
        booking.views.CalendarCreateView.as_view(),
        name='calendar-create'),
    url(r'^resource/(?P<pk>[0-9]+)/delete_calendar/?$',
        booking.views.CalendarDeleteView.as_view(),
        name='calendar-delete'),
    url(r'^resource/(?P<res>[0-9]+)/calendar/calendar-event/?$',
        booking.views.CalendarEventCreateView.as_view(),
        calendarevent_kwargs,
        name='calendar-event-create'),
    url(r'^resource/(?P<res>[0-9]+)/calendar/edit-event/(?P<pk>[0-9]+)/?$',
        booking.views.CalendarEventUpdateView.as_view(),
        calendarevent_kwargs,
        name='calendar-event-edit'),
    url(r'^resource/(?P<res>[0-9]+)/calendar/delete-event/(?P<pk>[0-9]+)/?$',
        booking.views.CalendarEventDeleteView.as_view(),
        calendarevent_kwargs,
        name='calendar-event-delete'),

    url(r'^product/(?P<pk>[0-9]+)/calendar/?$',
        booking.views.CalendarView.as_view(),
        product_calendar_kwargs,
        name='product-calendar'),
    url(r'^product/(?P<pk>[0-9]+)/calendar-create/?$',
        booking.views.CalendarCreateView.as_view(),
        product_calendar_kwargs,
        name='product-calendar-create'),
    url(r'^product/(?P<pk>[0-9]+)/delete_calendar/?$',
        booking.views.CalendarDeleteView.as_view(),
        product_calendar_kwargs,
        name='product-calendar-delete'),
    url(r'^product/(?P<prod>[0-9]+)/calendar/calendar-event/?$',
        booking.views.CalendarEventCreateView.as_view(),
        product_calendarevent_kwargs,
        name='product-calendar-event-create'),
    url(r'^product/(?P<prod>[0-9]+)/calendar/edit-event/(?P<pk>[0-9]+)/?$',
        booking.views.CalendarEventUpdateView.as_view(),
        product_calendarevent_kwargs,
        name='product-calendar-event-edit'),
    url(r'^product/(?P<prod>[0-9]+)/calendar/delete-event/(?P<pk>[0-9]+)/?$',
        booking.views.CalendarEventDeleteView.as_view(),
        product_calendarevent_kwargs,
        name='product-calendar-event-delete'),

    url(r'^resource/?$',
        ResourceListView.as_view(),
        name='resource-list'),
    url(r'^resource/(?P<pk>[0-9]+)/edit/?$',
        ResourceUpdateView.as_view(),
        name='resource-edit'),
    url(r'^resource/(?P<pk>[0-9]+)/delete/?$',
        ResourceDeleteView.as_view(),
        name='resource-delete'),

    url(r'^resourcepool/create/?$',
        ResourcePoolCreateView.as_view(),
        name='resourcepool-create'),
    url(r'^resourcepool/create/(?P<type>[0-9]+)/(?P<unit>[0-9]+)/?$',
        ResourcePoolUpdateView.as_view(success_url='create'),
        name='resourcepool-create-type'),
    url(r'^resourcepool/(?P<pk>[0-9]+)/?$',
        ResourcePoolDetailView.as_view(),
        name='resourcepool-view'),
    url(r'^resourcepool/?$',
        ResourcePoolListView.as_view(),
        name='resourcepool-list'),
    url(r'^resourcepool/(?P<pk>[0-9]+)/edit/?$',
        ResourcePoolUpdateView.as_view(),
        name='resourcepool-edit'),
    url(r'^resourcepool/(?P<pk>[0-9]+)/delete/?$',
        ResourcePoolDeleteView.as_view(),
        name='resourcepool-delete'),

    url(r'^product/(?P<product>[0-9]+)/resourcerequirement/create/?$',
        ResourceRequirementCreateView.as_view(),
        name='resourcerequirement-create'),
    url(r'^product/(?P<product>[0-9]+)/resource'
        r'requirement/(?P<pk>[0-9]+)/edit/?$',
        ResourceRequirementUpdateView.as_view(),
        name='resourcerequirement-edit'),
    url(r'^product/(?P<product>[0-9]+)/resourcerequirement/?$',
        ResourceRequirementListView.as_view(),
        name='resourcerequirement-list'),
    url(r'^product/(?P<product>[0-9]+)/resource'
        r'requirement/(?P<pk>[0-9]+)/delete/?$',
        ResourceRequirementDeleteView.as_view(),
        name='resourcerequirement-delete'),

    url(r'^visit/(?P<pk>[0-9]+)/resources/?$',
        VisitResourceEditView.as_view(),
        name='visit-resources-edit'
        )

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

embed_views = [
    'index',
    'product-view',
    'search',
]

embedpatterns = []
for x in urlpatterns:
    if isinstance(x, RegexURLPattern):
        if hasattr(x, 'name') and x.name in embed_views:
            # Tell template system that these URLs can be embedded
            x.default_args['can_be_embedded'] = True

            # Add a corresponding embed URL
            embedpatterns.append(
                url(
                    '^(?P<embed>embed/)' + x.regex.pattern[1:],
                    xframe_options_exempt(x._callback),
                    name=x.name + '-embed'
                )
            )

urlpatterns += embedpatterns
