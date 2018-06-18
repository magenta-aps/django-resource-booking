# encoding: utf-8
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms import model_to_dict
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic.base import ContextMixin

from booking.logging import log_action
from booking.constants import LOGACTION_CREATE, LOGACTION_CHANGE
from booking.utils import get_related_content_types
from profile.constants import EDIT_ROLES, ADMINISTRATOR, role_to_text


class AvailabilityUpdaterMixin(object):

    def save(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x.pk for x in aff_qs)

        # Whenever affected_eventtimes is calculated using m2m relations we
        # will get one save before relations are saved and one after. In the
        # one after relations will be broken, but we still have to adjust the
        # eventtimes found at the first save. Therefore we must temporarily
        # store a list of eventtimes to be checked at the next save
        if (
            getattr(self, 'affected_eventtimes_uses_m2m', False) and
            hasattr(self, '_recently_affected')
        ):
            affected.update(self._recently_affected)

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).save(*args, **kwargs)

        # Add what will be affected after the change
        for x in self.affected_eventtimes:
            affected.add(x.pk)

        # Store recently affected, or remove it if we just used it.
        if getattr(self, 'affected_eventtimes_uses_m2m', False):
            if hasattr(self, '_recently_affected'):
                delattr(self, '_recently_affected')
            else:
                self._recently_affected = affected

        # Update cached availability for any calendars affected by this change
        if hasattr(self, "affected_calendars"):
            for x in self.affected_calendars:
                x.recalculate_available()

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res

    def delete(self, *args, **kwargs):
        aff_qs = self.affected_eventtimes
        EventTime = aff_qs.model
        # Store what will be affected before the change
        affected = set(x.pk for x in aff_qs)

        # Make a copy of calendars that will be affected by the change
        if hasattr(self, "affected_calendars"):
            affected_calendars = tuple(self.affected_calendars)
        else:
            affected_calendars = None

        # Perform change
        res = super(AvailabilityUpdaterMixin, self).delete(*args, **kwargs)

        # Update cached availability for any calendars affected by this change
        if affected_calendars is not None:
            for x in affected_calendars:
                x.recalculate_available()

        # Update availability for everything affected
        EventTime.update_resource_status_for_qs(
            EventTime.objects.filter(pk__in=affected)
        )

        return res


class BreadcrumbMixin(ContextMixin):

    def get_breadcrumbs(self):
        try:
            return self.build_breadcrumbs(*self.get_breadcrumb_args())
        except Exception as e:
            print e
            return []

    def get_breadcrumb_args(self):
        return []

    def get_context_data(self, **kwargs):
        breadcrumbs = self.get_breadcrumbs()
        if len(breadcrumbs) > 0 and 'url' in breadcrumbs[-1]:
            del breadcrumbs[-1]['url']
        context = {'breadcrumbs': breadcrumbs}
        context.update(kwargs)
        return super(BreadcrumbMixin, self).get_context_data(**context)


class LoginRequiredMixin(object):
    """Include this mixin to require login.

    Mainly useful for users who are not coordinators or administrators.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Check that user is logged in and dispatch."""
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class RoleRequiredMixin(object):
    """Require that user has any of a number of roles."""

    # Roles is a list of required roles - maybe only one.
    # Each user can have only one role, and the condition is fulfilled
    # if one is found.

    roles = []  # Specify in subclass.

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            role = current_user.userprofile.get_role()
            if role in self.roles:
                return super(RoleRequiredMixin, self).dispatch(*args, **kwargs)
        else:
            pass
        txts = map(role_to_text, self.roles)
        # TODO: Render this with the error message!
        raise AccessDenied(
            u"Kun brugere med disse roller kan logge ind: " +
            u",".join(txts)
        )


class HasBackButtonMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(HasBackButtonMixin, self).get_context_data(**kwargs)
        context['oncancel'] = self.request.GET.get('back')
        return context


class BackMixin(ContextMixin):
    backparam = "back"
    just_preserve_back = False
    back_on_success = True
    back_on_cancel = True

    def redirect(self, regular):
        if self.backparam in self.request.GET:
            back = self.request.GET[self.backparam]
            if self.just_preserve_back:
                url = regular + ('?' if '?' not in regular else '&') + \
                    "back=%s" % back
            else:
                url = back
        else:
            url = regular
        return redirect(url)

    def get_success_url(self, regular=None):
        if self.back_on_success:
            if regular is None:
                regular = self.success_url
            if self.backparam in self.request.GET:
                back = self.request.GET[self.backparam]
                if self.just_preserve_back:
                    return regular + ('?' if '?' not in regular else '&') + \
                        "back=%s" % back
                else:
                    return back
            else:
                return regular
        elif hasattr(self, 'success_url') and self.success_url is not None:
            return self.success_url
        else:
            return super(BackMixin, self).get_success_url()

    def get_context_data(self, **kwargs):
        context = super(BackMixin, self).get_context_data(**kwargs)
        if self.back_on_cancel:
            context['oncancel'] = self.request.GET.get('back')
        return context


class AccessDenied(PermissionDenied):
    def __init__(self, text, *args, **kwargs):
        _text = text
        print _text.encode('utf-8')
        return super(AccessDenied, self).__init__(text, *args, **kwargs)

    def __unicode__(self):
        print self._text.encode('utf-8')
        return unicode(self._text)


class ModalMixin(object):
    modalid = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.modalid = request.GET["modalid"]
        except:
            try:
                self.modalid = request.POST["modalid"]
            except:
                pass
        return super(ModalMixin, self).dispatch(request, *args, **kwargs)

    def get_hash(self):
        return "id=" + self.modalid if self.modalid is not None else ""

    def modalurl(self, url):
        url += ";" if "#" in url else "#"
        url += self.get_hash()
        return url


class EditorRequriedMixin(RoleRequiredMixin):
    roles = EDIT_ROLES


class AdminRequiredMixin(RoleRequiredMixin):
    roles = [ADMINISTRATOR]


class UnitAccessRequiredMixin(object):

    def check_item(self, item):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            if current_user.userprofile.can_edit(item):
                return
        raise AccessDenied(_(u"You cannot edit an object for a unit "
                             u"that you don't belong to"))

    def check_unit(self, unit):
        current_user = self.request.user
        if hasattr(current_user, 'userprofile'):
            if current_user.userprofile.unit_access(unit):
                return
        raise AccessDenied(_(u"You cannot edit an object for a unit "
                             u"that you don't belong to"))


class AutologgerMixin(object):
    _old_state = {}

    def _as_state(self, obj=None):
        if obj is None:
            obj = self.object
        if obj and obj.pk:
            return model_to_dict(obj)
        else:
            return {}

    def _get_changed_fields(self, compare_state):
        new_state = self._as_state()

        result = {}

        for key in compare_state:
            if key in new_state:
                if compare_state[key] != new_state[key]:
                    result[key] = (compare_state[key], new_state[key])
                del new_state[key]
            else:
                result[key] = (compare_state[key], None)

        for key in new_state:
            result[key] = (None, new_state[key])

        return result

    def _field_value_to_display(self, fieldname, value):
        field = self.model._meta.get_field(fieldname)
        fname = field.verbose_name

        if value is None:
            return (fname, unicode(value))

        if field.many_to_one:
            try:
                o = field.related_model.objects.get(pk=value)
                return (fname, unicode(o))
            except:
                return (fname, unicode(value))

        if field.many_to_many or field.one_to_many:
            res = []
            for x in value:
                try:
                    o = field.related_model.objects.get(pk=x)
                    res.append(unicode(o))
                except:
                    res.append(unicode(x))
            return (fname, ", ".join(res))

        if field.choices:
            d = dict(field.choices)
            if value in d:
                return (fname, unicode(d[value]))

        return (fname, unicode(value))

    def _changes_to_text(self, changes):
        if not changes:
            return ""

        result = {}
        for key, val in changes.iteritems():
            name, value = self._field_value_to_display(key, val[1])
            result[name] = value

        return "\n".join([
            u"%s: >>>%s<<<" % (x, result[x]) for x in sorted(result)
        ])

    def _log_changes(self):
        if self._old_state:
            action = LOGACTION_CHANGE
            msg = _(u"Ændrede felter:\n%s")
        else:
            action = LOGACTION_CREATE
            msg = _(u"Oprettet med felter:\n%s")

        changeset = self._get_changed_fields(self._old_state)

        log_action(
            self.request.user,
            self.object,
            action,
            msg % self._changes_to_text(changeset)
        )

    def get_object(self, queryset=None):
        res = super(AutologgerMixin, self).get_object(queryset)

        self._old_state = self._as_state(res)

        return res

    def form_valid(self, form):
        res = super(AutologgerMixin, self).form_valid(form)

        self._log_changes()

        return res


class LoggedViewMixin(object):
    def get_log_queryset(self):
        types = get_related_content_types(self.model)

        qs = LogEntry.objects.filter(
            object_id=self.object.pk,
            content_type__in=types
        ).order_by('-action_time')

        return qs

    def get_context_data(self, **kwargs):
        return super(LoggedViewMixin, self).get_context_data(
            log_entries=self.get_log_queryset(),
            **kwargs
        )
