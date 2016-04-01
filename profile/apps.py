from django.apps import AppConfig


class ProfileConfig(AppConfig):
    name = 'profile'

    signals_loaded = False

    def ready(self):
        if not self.signals_loaded:
            import profile.signals  # noqa
            self.signals_loaded = True
