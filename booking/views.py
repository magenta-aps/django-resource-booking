from django.views.generic import TemplateView


class MainPageView(TemplateView):
    """Display the main page."""
    template_name = 'index.html'
