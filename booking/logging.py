# Thanks to https://gist.github.com/albertoalcolea/ for the code below.

import traceback

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType


class WsgiLogErrors(object):
    """
    Dump django exceptions to apache (with mod_wsgi) error logs
    """
    def process_exception(self, request, exception):
        tb_text = traceback.format_exc()
        url = request.build_absolute_uri()
        request.META['wsgi.errors'].write(
            "Exception caught on request to %s:\n" % url +
            str(tb_text) + '\n'
        )


def log_action(user, obj, action_flag, change_message=''):
    if user and hasattr(user, "pk") and user.pk:
        user_id = user.pk
    else:
        # Late import due to mutual import conflicts
        from profile.models import get_public_web_user  # noqa
        pw_user = get_public_web_user()
        user_id = pw_user.pk

    content_type_id = None
    object_id = None
    object_repr = ""
    if obj:
        ctype = ContentType.objects.get_for_model(obj)
        content_type_id = ctype.pk
        try:
            object_id = obj.pk
        except:
            pass
        try:
            object_repr = unicode(obj)
        except:
            pass

    LogEntry.objects.log_action(
        user_id,
        content_type_id,
        object_id,
        object_repr,
        action_flag,
        change_message
    )