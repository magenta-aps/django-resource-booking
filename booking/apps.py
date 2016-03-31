from django.apps import AppConfig


class BookingConfig(AppConfig):
    name = 'booking'

    signals_loaded = False

    def ready(self):
        if not self.signals_loaded:
            import booking.signals  # noqa
            self.signals_loaded = True
