# encoding: utf-8
from django.contrib.auth.models import User


class EmailLoginBackend(object):

    def authenticate(self, user_from_email_login=None):
        return user_from_email_login

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
