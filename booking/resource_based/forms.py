# encoding: utf-8
from django import forms
from django.utils.translation import ugettext_lazy as _


class CreateTimesFromRulesForm(forms.Form):
    start = forms.DateTimeField(
        label=_(u'Starttidspunkt'),
        required=False,
        initial='',
    )
    end = forms.DateTimeField(
        label=_(u'Sluttidspunkt'),
        required=False,
        initial='',
    )
    has_specific_time = forms.ChoiceField(
        initial=True,
        required=False,
        label=_(u"Angivelse af tidspunkt"),
        choices=(
            (True, _(u"Både dato og tidspunkt")),
            (False, _(u"Kun dato")),
        ),
    )
