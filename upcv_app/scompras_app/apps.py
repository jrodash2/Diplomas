from django.apps import AppConfig

class scomprasAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scompras_app'

    # def ready(self):
    #     import scompras_app.signals  # 👈 importa tus signals aquí
