# -*- coding: utf-8 -*-

from django.db.models.expressions import OrderBy
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import formats, timezone
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView, FormView
from booking.booking_workflows.forms import ChangeVisitOccurrenceStatusForm, \
    BecomeSomethingForm
from booking.booking_workflows.forms import VisitOccurrenceAutosendFormSet
from booking.booking_workflows.forms import ChangeVisitOccurrenceTeachersForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceHostsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceRoomsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceCommentsForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceEvalForm
from booking.booking_workflows.forms import VisitOccurrenceAddLogEntryForm
from booking.booking_workflows.forms import VisitOccurrenceAddCommentForm
from booking.booking_workflows.forms import ChangeVisitOccurrenceStartTimeForm
from booking.booking_workflows.forms import ResetVisitOccurrenceChangesForm
from booking.models import VisitOccurrence
from booking.models import EmailTemplate
from booking.models import Locality
from booking.models import LOGACTION_MANUAL_ENTRY
from booking.models import log_action
from booking.models import Room
from booking.views import AutologgerMixin
from booking.views import RoleRequiredMixin, EditorRequriedMixin
from django.views.generic.base import ContextMixin
from profile.models import TEACHER, HOST, EDIT_ROLES


class VisitOccurrenceBreadcrumbMixin(ContextMixin):
    view_title = _(u'opdater')

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {
                'url': reverse('visit-occ-search'),
                'text': _(u'Søg i besøg')
            },
            {
                'url': reverse('visit-occ-view', args=[self.object.pk]),
                'text': _(u'Besøg #%s') % self.object.pk
            },
            {'text': self.view_title},
        ]
        context.update(kwargs)
        return super(VisitOccurrenceBreadcrumbMixin, self).\
            get_context_data(**context)


class UpdateWithCancelView(VisitOccurrenceBreadcrumbMixin, EditorRequriedMixin,
                           UpdateView):
    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            self.object = self.get_object()
            return redirect(self.get_success_url())
        else:
            return super(UpdateWithCancelView, self).post(
                request, *args, **kwargs
            )


class ChangeVisitOccurrenceStartTimeView(AutologgerMixin,
                                         UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStartTimeForm
    template_name = "booking/workflow/change_starttime.html"
    view_title = _(u'Redigér tidspunkt')


class ChangeVisitOccurrenceStatusView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceStatusForm
    template_name = "booking/workflow/change_status.html"
    view_title = _(u'Skift status')

    def form_valid(self, form):
        response = super(ChangeVisitOccurrenceStatusView, self).form_valid(
            form
        )
        status = form.cleaned_data['workflow_status']
        if status == VisitOccurrence.WORKFLOW_STATUS_PLANNED:
            # Booking is planned
            self.object.autosend(EmailTemplate.NOTIFY_ALL__BOOKING_COMPLETE)
        if status == VisitOccurrence.WORKFLOW_STATUS_CANCELLED:
            # Booking is cancelled
            self.object.autosend(EmailTemplate.NOTIFY_ALL__BOOKING_CANCELED)
        return response


class ChangeVisitOccurrenceTeachersView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceTeachersForm
    template_name = "booking/workflow/change_teachers.html"
    view_title = _(u'Redigér undervisere')

    def get_context_data(self, **kwargs):
        context = {}
        context['comments'] = {
            user.id: [
                {
                    'text': comment.text,
                    'time': formats.date_format(
                        timezone.localtime(comment.time),
                        "DATETIME_FORMAT"
                    )
                }
                for comment in self.object.get_comments(user).all()
            ]
            for user in self.get_form().base_fields['teachers'].queryset.all()
        }
        context['can_send_emails'] = self.object.autosend_enabled(
            EmailTemplate.NOTIFY_TEACHER__ASSOCIATED
        )
        context['email_template_name'] = EmailTemplate.get_name(
            EmailTemplate.NOTIFY_TEACHER__ASSOCIATED
        )
        context.update(kwargs)
        return super(ChangeVisitOccurrenceTeachersView, self).\
            get_context_data(**context)

    # When the status or teacher list changes, autosend emails
    def form_valid(self, form):
        old = self.get_object()
        old_teachers = set([x for x in old.teachers.all()])

        response = super(
            ChangeVisitOccurrenceTeachersView, self
        ).form_valid(form)

        if form.cleaned_data.get('send_emails', False):
            new_teachers = self.object.teachers.all()
            recipients = [
                teacher
                for teacher in new_teachers
                if teacher not in old_teachers
            ]
            if len(recipients) > 0:
                print recipients
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplate.NOTIFY_TEACHER__ASSOCIATED,
                    recipients,
                    True
                )

        return response


class ChangeVisitOccurrenceHostsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceHostsForm
    template_name = "booking/workflow/change_hosts.html"
    view_title = _(u'Redigér værter')

    def get_context_data(self, **kwargs):
        context = {}
        context['comments'] = {
            user.id: [
                {
                    'text': comment.text,
                    'time': formats.date_format(
                        timezone.localtime(comment.time),
                        "DATETIME_FORMAT"
                    )
                }
                for comment in self.object.get_comments(user).all()
                ]
            for user in self.get_form().base_fields['hosts'].queryset.all()
            }
        context['can_send_emails'] = self.object.autosend_enabled(
            EmailTemplate.NOTIFY_HOST__ASSOCIATED
        )
        context['email_template_name'] = EmailTemplate.get_name(
            EmailTemplate.NOTIFY_HOST__ASSOCIATED
        )
        context.update(kwargs)
        return super(ChangeVisitOccurrenceHostsView, self).\
            get_context_data(**context)

    # When the status or host list changes, autosend emails
    def form_valid(self, form):
        old = self.get_object()
        old_hosts = set([x for x in old.hosts.all()])

        response = super(ChangeVisitOccurrenceHostsView, self).form_valid(form)

        if form.cleaned_data.get('send_emails', False):
            new_hosts = self.object.hosts.all()
            recipients = [
                host
                for host in new_hosts
                if host not in old_hosts
            ]
            if len(recipients) > 0:
                # Send a message to only these recipients
                self.object.autosend(
                    EmailTemplate.occurrence_added_host_key,
                    recipients,
                    True
                )

        return response


class ChangeVisitOccurrenceRoomsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceRoomsForm
    template_name = "booking/workflow/change_rooms.html"
    view_title = _(u'Redigér lokaler')

    def get_context_data(self, **kwargs):
        context = {}
        context.update(kwargs)

        context['allrooms'] = [
            {
                'id': x.pk,
                'locality_id': x.locality.pk if x.locality else None,
                'name': x.name_with_locality
            }
            for x in Room.objects.all()
        ]

        context['rooms'] = self.object.rooms.all()

        locality = self.object.visit.locality
        unit = self.object.visit.unit

        context['locality_choices'] = [(None, "---------")] + \
            [
                (x.id, x.name_and_address,
                 locality is not None and x.id == locality.id)
                for x in Locality.objects.order_by(
                    # Sort stuff where unit is null last
                    OrderBy(Q(unit__isnull=False), descending=True),
                    # Sort localities belong to current unit first
                    OrderBy(Q(unit=unit), descending=True),
                    # Lastly, sort by name
                    "name"
                )
            ]

        return super(
            ChangeVisitOccurrenceRoomsView, self
        ).get_context_data(**context)

    def form_valid(self, form):
        self.object = form.save()

        self.save_rooms()
        result = super(ChangeVisitOccurrenceRoomsView, self).form_valid(form)
        return result

    def save_rooms(self):
        # This code is more or less the same as EditVisitView.save_rooms()
        # If you update this you might have to update there as well.
        existing_rooms = set([x.pk for x in self.object.rooms.all()])

        new_rooms = self.request.POST.getlist("rooms")

        for roomdata in new_rooms:
            if roomdata.startswith("id:"):
                # Existing rooms are identified by "id:<pk>"
                try:
                    room_pk = int(roomdata[3:])
                    if room_pk in existing_rooms:
                        existing_rooms.remove(room_pk)
                    else:
                        self.object.rooms.add(room_pk)
                except Exception as e:
                    print 'Problem adding room: %s' % e
            elif roomdata.startswith("new:"):
                # New rooms are identified by "new:<name-of-room>"
                room = self.object.add_room_by_name(roomdata[4:])
                if room.pk in existing_rooms:
                    existing_rooms.remove(room.pk)

        # Delete any rooms left in existing rooms
        for x in existing_rooms:
            self.object.rooms.remove(x)


class ChangeVisitOccurrenceCommentsView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceCommentsForm
    template_name = "booking/workflow/change_comments.html"
    view_title = _(u'Redigér kommentarer')


class ChangeVisitOccurrenceEvalView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ChangeVisitOccurrenceEvalForm
    template_name = "booking/workflow/change_eval_link.html"
    view_title = _(u'Redigér evalueringslink')


class VisitOccurrenceAddLogEntryView(FormView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAddLogEntryForm
    template_name = "booking/workflow/add_logentry.html"
    object = None
    view_title = _(u'Tilføj log-post')

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.model.objects.get(pk=kwargs['pk'])
        except:
            raise Http404("VisitOccurrence not found")

        return super(VisitOccurrenceAddLogEntryView, self).dispatch(
            request, *args, **kwargs
        )

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            return redirect(self.get_success_url())
        else:
            return super(VisitOccurrenceAddLogEntryView, self).post(
                request, *args, **kwargs
            )

    def get_context_data(self, **kwargs):
        context = {}
        context['breadcrumbs'] = [
            {
                'url': reverse('visit-occ-search'),
                'text': _(u'Søg i besøg')
            },
            {
                'url': reverse('visit-occ-view', args=[self.object.pk]),
                'text': _(u'Besøg #%s') % self.object.pk
            },
            {'text': self.view_title},
        ]
        context.update(kwargs)
        return super(VisitOccurrenceAddLogEntryView, self).get_context_data(
            object=self.object,
            **context
        )

    def form_valid(self, form):
        log_action(
            self.request.user,
            self.object,
            LOGACTION_MANUAL_ENTRY,
            form.cleaned_data['new_comment']
        )
        return super(VisitOccurrenceAddLogEntryView, self).form_valid(form)

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])


class VisitOccurrenceAddCommentView(VisitOccurrenceAddLogEntryView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAddCommentForm
    template_name = "booking/workflow/add_comment.html"
    object = None
    view_title = _(u'Tilføj kommentar')

    def form_valid(self, form):
        self.object.add_comment(
            self.request.user,
            form.cleaned_data['new_comment']
        )
        return super(VisitOccurrenceAddLogEntryView, self).form_valid(form)


class ChangeVisitOccurrenceAutosendView(AutologgerMixin, UpdateWithCancelView):
    model = VisitOccurrence
    form_class = VisitOccurrenceAutosendFormSet
    template_name = "booking/workflow/change_autosend.html"
    view_title = _(u'Redigér automatiske emails')

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = {}
        context['inherited'] = {
            item.template_key:
            {
                'template_key': item.template_key,
                'enabled': item.enabled,
                'days': item.days
            }
            for item in self.object.visit.visitautosend_set.all()
        }
        context['template_keys'] = list(set(
            template.key
            for template in EmailTemplate.get_templates(self.object.visit.unit)
        ))
        context['unit'] = self.object.visit.unit
        context['autosend_enable_days'] = EmailTemplate.enable_days
        context.update(kwargs)
        return super(ChangeVisitOccurrenceAutosendView, self).\
            get_context_data(**context)


class BecomeSomethingView(AutologgerMixin, VisitOccurrenceBreadcrumbMixin,
                          RoleRequiredMixin, FormView):
    model = VisitOccurrence
    errors = None
    m2m_attribute = None
    view_title = _(u'Tilmeld rolle')
    roles = [HOST, TEACHER] + list(EDIT_ROLES)
    form_class = BecomeSomethingForm
    notify_mail_template_key = None

    ERROR_NONE_NEEDED = _(
        u"Det valgte besøg har ikke behov for flere personer i den " +
        u"givne rolle"
    )
    ERROR_WRONG_ROLE = _(
        u"Du har ikke den rette rolle til at bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede blevet tildelt den givne rolle"
    )

    def needs_more(self):
        raise NotImplementedError

    def is_right_role(self):
        raise NotImplementedError

    def get_object(self, queryset=None):
        res = self.model.objects.get(pk=self.kwargs.get("pk"))

        # Store state for autologger
        self._old_state = self._as_state(res)

        return res

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = {}
        context['object'] = self.object
        context.update(kwargs)
        return super(BecomeSomethingView, self).get_context_data(**context)

    def is_valid(self):
        if self.errors is None:
            self.errors = []

            # Are we the right role?
            if not self.is_right_role():
                self.errors.append(self.ERROR_WRONG_ROLE)

            # Do the event need more of the given role?
            if not self.needs_more():
                self.errors.append(self.ERROR_NONE_NEEDED)

            # Is the current user already registered?
            qs = getattr(self.object, self.m2m_attribute).filter(
                pk=self.request.user.pk
            )
            if qs.exists():
                self.errors.append(self.ERROR_ALREADY_REGISTERED)

        return len(self.errors) == 0

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if self.is_valid():

            # Process the form to get cleaned_data, but ignore any error.
            form.is_valid()

            if 'comment' in form.cleaned_data:
                comment = form.cleaned_data['comment']
                if comment:
                    self.object.add_comment(
                        request.user,
                        comment
                    )

            if request.POST.get("cancel"):
                if isinstance(self, DeclineHostView):
                    self.object.hosts_rejected.add(request.user)
                if isinstance(self, DeclineTeacherView):
                    self.object.teachers_rejected.add(request.user)
                self.object.save()

            elif request.POST.get("confirm"):
                # Add user to the specified m2m relation
                getattr(self.object, self.m2m_attribute).add(request.user)

                # Notify the user about the association
                if self.notify_mail_template_key:
                    self.object.autosend(
                        self.notify_mail_template_key,
                        [request.user],
                        True
                    )

            self._log_changes()

        return self.get(request, *args, **kwargs)

    def render_with_error(self, error, request, *args, **kwargs):
        self.errors.append(error)
        return self.get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('visit-occ-view', args=[self.object.pk])


class BecomeTeacherView(BecomeSomethingView):
    m2m_attribute = "teachers"
    template_name = "booking/workflow/become_teacher.html"
    view_title = _(u'Tilmeld som underviser')
    notify_mail_template_key = EmailTemplate.occurrence_added_teacher_key

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere undervisere")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen underviser for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede underviser på besøget"
    )

    def needs_more(self):
        return self.object.needs_teachers

    def is_right_role(self):
        return self.request.user.userprofile.is_teacher


class DeclineTeacherView(BecomeSomethingView):
    m2m_attribute = "teachers"
    template_name = "booking/workflow/decline_teacher.html"
    view_title = _(u'Tilmeld som underviser')
    notify_mail_template_key = EmailTemplate.occurrence_added_teacher_key

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere undervisere")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen underviser for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede underviser på besøget"
    )

    def needs_more(self):
        return self.object.needs_teachers

    def is_right_role(self):
        return self.request.user.userprofile.is_teacher


class BecomeHostView(BecomeSomethingView):
    m2m_attribute = "hosts"
    template_name = "booking/workflow/become_host.html"
    view_title = _(u'Tilmeld som vært')
    notify_mail_template_key = EmailTemplate.occurrence_added_host_key

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere værter")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen vært for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede vært på besøget"
    )

    def needs_more(self):
        return self.object.needs_hosts

    def is_right_role(self):
        return self.request.user.userprofile.is_host


class DeclineHostView(BecomeSomethingView):
    m2m_attribute = "hosts"
    template_name = "booking/workflow/decline_host.html"
    view_title = _(u'Tilmeld som vært')
    notify_mail_template_key = EmailTemplate.occurrence_added_host_key

    ERROR_NONE_NEEDED = _(u"Besøget har ikke brug for flere værter")
    ERROR_WRONG_ROLE = _(
        u"Du skal have rollen vært for at kunne bruge denne funktion"
    )
    ERROR_ALREADY_REGISTERED = _(
        u"Du er allerede vært på besøget"
    )

    def needs_more(self):
        return self.object.needs_hosts

    def is_right_role(self):
        return self.request.user.userprofile.is_host


class ResetVisitOccurrenceChangesView(UpdateWithCancelView):
    model = VisitOccurrence
    form_class = ResetVisitOccurrenceChangesForm
    template_name = "booking/workflow/change_changes_marker.html"
    view_title = _(u'Nulstil markør for nylige ændringer')

    def form_valid(self, form):
        self.object = form.save()
        self.object.last_workflow_update = timezone.now()
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
