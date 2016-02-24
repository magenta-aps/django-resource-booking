from django.template.defaultfilters import register
import re
from django.utils.safestring import mark_safe
from booking.models import LOGACTION_DISPLAY_MAP


@register.filter
def upload_name_clean(value):
    return re.sub(r'_[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)$', r'\1', value)


@register.filter
def upload_name_strip_path(value):
    return re.sub(r'.*/(.*)$', r'\1', value)


@register.filter
def highlight(text, filter):
    words = filter.split(' ')
    pattern = re.compile(r"(?P<filter>%s)" % '|'.join(words), re.IGNORECASE)
    return mark_safe(re.sub(pattern, r"<mark>\g<filter></mark>", text))


@register.filter
def logaction_type_display(value):
    if value in LOGACTION_DISPLAY_MAP:
        return LOGACTION_DISPLAY_MAP[value]
    else:
        return 'LOGACTION_%s' % value
