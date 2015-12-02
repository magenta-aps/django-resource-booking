# -*- coding: utf-8 -*-
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _


i18n_test = _(u"Dette tester oversættelses-systemet")


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'


# A couple of generic superclasses for crud views
# Our views will inherit from these and from django.views.generic classes

class Mixin(object):
    object_name = 'Object'
    url_base = 'object'

    # Get the view's topmost superclass that is not a Mixin
    def get_other_superclass(self):
        for superclass in self.__class__.__mro__:
            if not issubclass(superclass, Mixin):
                return superclass

    # Call the 'real' get_context_data() from the non-Mixin superclass
    # and apply the object_name to it.
    def get_context_data(self, **kwargs):
        superclass = super(self.get_other_superclass(), self)
        context = superclass.get_context_data(**kwargs)
        context['object_name'] = self.object_name
        return context
