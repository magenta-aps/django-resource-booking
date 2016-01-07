
from django.views.generic import TemplateView

from booking.views import LoginRequiredMixin


class ProfileView(LoginRequiredMixin, TemplateView):
    """Display the user's profile."""
    pass
