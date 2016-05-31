from django.conf import settings
from django.contrib.auth.models import User
from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.template import defaulttags
from django.template.base import FilterExpression
from django.template.defaultfilters import register
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from timedelta.helpers import parse, nice_repr
from booking.models import LOGACTION_DISPLAY_MAP, Booker, EmailBookerEntry
from profile.models import EmailLoginEntry, UserProfile
import datetime
import re
import json


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


@register.filter(name='timedelta_i18n')
def timedelta_i18n(value, display="long", sep=", "):
    if value is None:
        return value
    if isinstance(value, basestring):
        try:
            value = parse(value)
        except TypeError:
            return value

    assert isinstance(value, datetime.timedelta),\
        "First argument must be a timedelta."

    result = []

    weeks = int(value.days / 7)
    days = value.days % 7
    hours = int(value.seconds / 3600)
    minutes = int((value.seconds % 3600) / 60)
    seconds = value.seconds % 60

    if display == 'minimal':
        # Translators: Single-letter singular time notation
        # (e.g. 1d, meaning 1 day)
        words_singular = [_(u"1w"), _(u"1d"), _(u"1h"), _(u"1m"), _(u"1s")]
        # Translators: Single-letter plural time notation
        # (%id for e.g. 6d, meaning 6 days)
        words_plural = [_(u"%iw"), _(u"%id"), _(u"%ih"), _(u"%im"), _(u"%is")]
    elif display == 'short':
        # Translators: Short singular time notation
        # (e.g. 1 hr, meaning 1 hour)
        words_singular = [_(u"1 wk"), _(u"1 dy"),
                          _(u"1 hr"), _(u"1 min"), _(u"1 sec")]
        # Translators: Short plural time notation
        # (%i hrs for e.g. 6 hrs, meaning 6 hours)
        words_plural = [_(u"%i wks"), _(u"%i dys"),
                        _(u"%i hrs"), _(u"%i min"), _(u"%i sec")]
    elif display == 'long':
        # Translators: Long singular time notation
        # (e.g. 1 hour)
        words_singular = [_(u"1 week"), _(u"1 day"),
                          _(u"1 hour"), _(u"1 minute"), _(u"1 second")]
        # Translators: Long plural time notation
        # (%i hours for e.g. 6 hours)
        words_plural = [_(u"%i weeks"), _(u"%i days"),
                        _(u"%i hours"), _(u"%i minutes"), _(u"%i seconds")]
    else:
        return nice_repr(value, display)

    values = [weeks, days, hours, minutes, seconds]

    for i in range(len(values)):
        if values[i]:
            if values[i] == 1:
                result.append(unicode(words_singular[i]))
            else:
                result.append(unicode(words_plural[i] % values[i]))

    # values with less than one second, which are considered zeroes
    if len(result) == 0:
        # display as 0 of the smallest unit
        result.append(words_plural[-1] % 0)

    return sep.join(result)


@register.filter
def logaction_type_display(value):
    if value in LOGACTION_DISPLAY_MAP:
        return LOGACTION_DISPLAY_MAP[value]
    else:
        return 'LOGACTION_%s' % value


@register.filter
def jsonify(object):
    if isinstance(object, QuerySet):
        return serialize('json', object)
    return json.dumps(object)


@register.filter(name='dotjoin')
def dotjoin(value, arg):
    if value is not None and value != "":
        return "%s.%s" % (value, arg)
    return arg


@register.filter(name='replace')
def replace(value, arg):
    if value is not None and value != "":
        search, replace = arg.split(",")
        return value.replace(search, replace)
    return arg


class FullURLNode(defaulttags.Node):

    TOKEN_USER_KEY = 'token_user'

    our_kwarg_keys = [TOKEN_USER_KEY]
    kwargs = {}

    def __init__(self, url_node):
        # Grab any kwargs that we lay claim to
        for key in self.our_kwarg_keys:
            if key in url_node.kwargs:
                self.kwargs[key] = url_node.kwargs.pop(key)
        self.url_node = url_node

    def url_prefix(self):
        return settings.PUBLIC_URL

    def tokenize(self, url, context):
        # If a valid token_for arg is supplied, put a token on the url
        if url is not None and url != '' and \
                self.TOKEN_USER_KEY in self.kwargs:
            user = self.kwargs[self.TOKEN_USER_KEY]
            if isinstance(user, FilterExpression):
                user = user.resolve(context)
            elif isinstance(user, basestring):
                user = context.get(user)
            if isinstance(user, User):
                pass
            elif isinstance(user, UserProfile):
                user = user.user

            if isinstance(user, User):
                entry = EmailLoginEntry.create_from_url(
                    user,
                    url,
                    expires_in=datetime.timedelta(hours=72)
                )
                return entry.as_url()

            # Special hack for letting Bookers respond to mails
            if isinstance(user, Booker):
                answer = "no"
                if len(self.url_node.args) >= 2:
                    answer = self.url_node.args[1].resolve(context)
                entry = EmailBookerEntry.create(
                    user,
                    expires_in=datetime.timedelta(hours=72)
                )
                return entry.as_url(answer == "yes")
        return url

    def prefix(self, url):
        return self.url_prefix() + url

    def render(self, context):
        try:
            result = self.url_node.render(context)
            if self.url_node.asvar:
                # If asvar was set, we got an empty string in the result,
                # and must fetch from the context
                result = context[self.url_node.asvar]
                context[self.url_node.asvar] = self.prefix(
                    self.tokenize(result, context)
                )
                return ''
            else:
                return self.prefix(self.tokenize(result, context))
        except:
            # return _(u'&lt;Forkert url&gt;')
            args = [arg.resolve(context) for arg in self.url_node.args]
            string_if_invalid = context.template.engine.string_if_invalid
            if not string_if_invalid:
                string_if_invalid = ''
            if string_if_invalid != '':
                arg = args[0] if len(args) > 0 else ''
                arg = re.sub(r"^\{+", '', arg)
                arg = re.sub(r"\}+$", '', arg)
                return "{%% full_url %s %s %%}" % \
                       (self.url_node.view_name, arg)
            else:
                return ''
            # if '%s' in string_if_invalid:
            #    return string_if_invalid % args
            # else:
            #    return string_if_invalid


@register.tag
def full_url(parser, token):
    url_node = defaulttags.url(parser, token)
    return FullURLNode(url_node)
