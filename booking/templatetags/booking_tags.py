from django.template.defaultfilters import register
import re


@register.filter
def upload_name_clean(value):
    return re.sub(r'_[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)$', r'\1', value)


@register.filter
def upload_name_strip_path(value):
    return re.sub(r'.*/(.*)$', r'\1', value)
