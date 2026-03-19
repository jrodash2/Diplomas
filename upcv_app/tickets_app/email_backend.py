
import ssl
import certifi
from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    def open(self):
        # Crear un contexto SSL que use los certificados de certifi
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        return super().open()
