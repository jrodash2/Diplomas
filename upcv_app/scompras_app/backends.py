from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import connections

class TicketsAuthBackend(ModelBackend):
    """
    Permite autenticar usuarios desde la base de datos de Tickets.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.using('tickets_db').get(username=username)
            if user.check_password(password) and user.is_active:
                return user
        except User.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.using('tickets_db').get(pk=user_id)
        except User.DoesNotExist:
            return None
