# encoding: utf-8
from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.utils.translation import ugettext_lazy as _

LOGACTION_CREATE = ADDITION
LOGACTION_CHANGE = CHANGE
LOGACTION_DELETE = DELETION
# If we need to add additional values make sure they do not conflict with
# system defined ones by adding 128 to the value.
LOGACTION_MAIL_SENT = 128 + 1
LOGACTION_CUSTOM2 = 128 + 2
LOGACTION_MANUAL_ENTRY = 128 + 64 + 1
LOGACTION_DISPLAY_MAP = {
    LOGACTION_CREATE: _('Oprettet'),
    LOGACTION_CHANGE: _('Ændret'),
    LOGACTION_DELETE: _('Slettet'),
    LOGACTION_MAIL_SENT: _('Mail sendt'),
    LOGACTION_MANUAL_ENTRY: _('Log-post tilføjet manuelt')
}

AVAILABLE_SEATS_NO_LIMIT = -1
