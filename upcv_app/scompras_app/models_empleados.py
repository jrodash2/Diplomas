from django.db import models
from django.contrib.auth.models import User

class Empleado(models.Model):
    class Meta:
        managed = False
        db_table = 'empleados_app_empleado'  # nombre real de la tabla en Ticktes

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to='card_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
