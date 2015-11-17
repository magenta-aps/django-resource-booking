# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

i18n_test = _("Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'
