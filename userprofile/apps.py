from django.apps import AppConfig


class UserProfileConfig(AppConfig):
    name = 'userprofile'

    signals_loaded = False

    def ready(self):
        if not self.signals_loaded:
            import userprofile.signals  # noqa
            self.signals_loaded = True
