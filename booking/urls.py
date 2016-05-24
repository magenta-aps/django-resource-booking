from django.conf.urls import patterns, url, include
from django.conf.urls.static import static
from django.conf import settings

from .views import MainPageView, VisitOccurrenceNotifyView

from booking.views import PostcodeView, SchoolView, VisitInquireView
from booking.views import RrulestrView
from booking.views import ResourceListView, ResourceCustomListView
from booking.views import EditResourceInitialView, ResourceDetailView
from booking.views import BookingView, BookingSuccessView
from booking.views import VisitOccurrenceSearchView
from booking.views import EditOtherResourceView, OtherResourceDetailView
from booking.views import EditVisitView, VisitDetailView
from booking.views import EmailSuccessView, VisitInquireSuccessView
from booking.views import SearchView, EmbedcodesView

from booking.views import BookingNotifyView, BookingDetailView
from booking.views import EmailTemplateListView, EmailTemplateEditView
from booking.views import EmailTemplateDetailView, EmailTemplateDeleteView
from booking.views import ChangeVisitOccurrenceEvalView
from booking.views import ChangeVisitOccurrenceStatusView
from booking.views import ChangeVisitOccurrenceStartTimeView
from booking.views import ChangeVisitOccurrenceTeachersView
from booking.views import ChangeVisitOccurrenceHostsView
from booking.views import ChangeVisitOccurrenceRoomsView
from booking.views import ChangeVisitOccurrenceCommentsView
from booking.views import ChangeVisitOccurrenceAutosendView
from booking.views import BecomeTeacherView
from booking.views import BecomeHostView
from booking.views import EmailReplyView
from booking.views import VisitOccurrenceAddLogEntryView
from booking.views import VisitOccurrenceAddCommentView
from booking.views import VisitOccurrenceDetailView
from booking.views import VisitOccurrenceCustomListView
from booking.views import CloneResourceView


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
    url(r'^resource/?$',
        ResourceListView.as_view(),
        name='resource-list'),

    url(r'^resource/customlist/?$',
        ResourceCustomListView.as_view(),
        name='resource-customlist'),
    url(r'^resource/(?P<pk>[0-9]+)/edit$',
        EditResourceInitialView.as_view(),
        name='resource-edit'),
    url(r'^resource/(?P<pk>[0-9]+)/clone$',
        CloneResourceView.as_view(),
        name='resource-clone'),

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
    url(r'^visit/(?P<visit>[0-9]+)/inquire$',
        VisitInquireView.as_view(),
        name='visit-inquire'),
    url(r'^visit/(?P<visit>[0-9]+)/inquire/success$',
        VisitInquireSuccessView.as_view(),
        name='visit-inquire-success'),

    url(r'^visit/occurrence/(?P<pk>[0-9]+)/notify$',
        VisitOccurrenceNotifyView.as_view(),
        name='visit-occ-notify'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/notify/success$',
        EmailSuccessView.as_view(),
        name='visit-occ-notify-success'),

    url(r'^visit/occurrence/(?P<pk>[0-9]+)$',
        VisitOccurrenceDetailView.as_view(),
        name='visit-occ-view'),

    url(r'^booking/(?P<pk>[0-9]+)/?$',
        BookingDetailView.as_view(),
        name='booking-view'),

    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_status/?$',
        ChangeVisitOccurrenceStatusView.as_view(),
        name='change-visit-occ-status'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_starttime/?$',
        ChangeVisitOccurrenceStartTimeView.as_view(),
        name='change-visit-occ-starttime'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_teachers/?$',
        ChangeVisitOccurrenceTeachersView.as_view(),
        name='change-visit-occ-teachers'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_hosts/?$',
        ChangeVisitOccurrenceHostsView.as_view(),
        name='change-visit-occ-hosts'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_rooms/?$',
        ChangeVisitOccurrenceRoomsView.as_view(),
        name='change-visit-occ-rooms'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_comments/?$',
        ChangeVisitOccurrenceCommentsView.as_view(),
        name='change-visit-occ-comments'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_evaluation_link/?$',
        ChangeVisitOccurrenceEvalView.as_view(),
        name='change-visit-occ-eval'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/add_logentry/?$',
        VisitOccurrenceAddLogEntryView.as_view(),
        name='visit-occ-add-logentry'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/add_comment/?$',
        VisitOccurrenceAddCommentView.as_view(),
        name='visit-occ-add-comment'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/become_teacher/?$',
        BecomeTeacherView.as_view(),
        name='become-teacher'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/become_host/?$',
        BecomeHostView.as_view(),
        name='become-host'),
    url(r'^visit/occurrence/search$',
        VisitOccurrenceSearchView.as_view(),
        name='visit-occ-search'),
    url(r'^visit/occurrence/(?P<pk>[0-9]+)/change_autosend/?$',
        ChangeVisitOccurrenceAutosendView.as_view(),
        name='change-visit-occ-autosend'),
    url(r'^visit/occurrence/customlist/?$',
        VisitOccurrenceCustomListView.as_view(),
        name='visit-occ-customlist'),

    url(r'^booking/(?P<pk>[0-9]+)/notify$',
        BookingNotifyView.as_view(),
        name='booking-notify'),
    url(r'^booking/(?P<visit>[0-9]+)/notify/success$',
        EmailSuccessView.as_view(),
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
        name='emailtemplate-delete'),

    url(r'^reply-to-email/(?P<reply_nonce>[0-9a-f-]{36})',
        EmailReplyView.as_view(),
        name='reply-to-email')

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
