# encoding: utf-8
from django.apps import AppConfig


class ProfileConfig(AppConfig):
    name = 'user_profile'

    signals_loaded = False

    def ready(self):
        if not self.signals_loaded:
            import user_profile.signals  # noqa
            self.signals_loaded = True
