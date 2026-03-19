from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail, get_connection, EmailMessage
from django.conf import settings
import logging
import ssl
import certifi

from django.conf import settings
from django.core.mail import get_connection, EmailMessage
from django.db import models
from django.contrib.auth.models import User



logger = logging.getLogger(__name__)  # Asegúrate de tener configurado el logger

class TipoEquipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Oficina(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

logger = logging.getLogger(__name__)

class Ticket(models.Model):
    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado'),
        ('pendiente', 'Pendiente'),
    ]
    
    VIA_CONTACTO_CHOICES = [
        ('telefono', 'Telefono'),
        ('wahtsapp', 'WhatsApp'),
        ('personal ', 'Personal'),
        ('correo', 'Correo'),
    ]

    PRIORIDAD_CHOICES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]

    oficina = models.ForeignKey('Oficina', on_delete=models.SET_NULL, null=True)
    via_contacto = models.CharField(max_length=100, choices=VIA_CONTACTO_CHOICES, default='telefono')
    tipo_equipo = models.ForeignKey('TipoEquipo', on_delete=models.SET_NULL, null=True)
    problema = models.CharField(max_length=200)
    responsable = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, blank=True)
    correo = models.EmailField(max_length=100, blank=True)
    detalle_problema = models.TextField(blank=True)
    solucion_problema = models.TextField(blank=True)
    tecnico_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tickets_asignados')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierto')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='alta')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket {self.id} - {self.problema} ({self.estado})"

    def save(self, *args, **kwargs):
        tecnico_anterior = None

        if self.pk:
            try:
                ticket_anterior = Ticket.objects.get(pk=self.pk)
                tecnico_anterior = ticket_anterior.tecnico_asignado
            except Ticket.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Si se asigna un técnico nuevo o cambia el técnico, se envía el correo
        if self.tecnico_asignado and (tecnico_anterior is None or self.tecnico_asignado != tecnico_anterior):
            try:
                # Crear contexto SSL con certifi
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                connection = get_connection(ssl_context=ssl_context)

                URL_SISTEMA = 'https://apps.upcv.gob.gt/'

                email = EmailMessage(
                    subject=f'Ticket Asignado - ID {self.id}',
                    body=(
                        f"Hola {self.tecnico_asignado.get_full_name() or self.tecnico_asignado.username},\n\n"
                        f"Se te ha asignado un nuevo ticket de soporte:\n\n"
                        f"- Problema: {self.problema}\n"
                        f"- Oficina: {self.oficina}\n"
                        f"- Prioridad: {self.prioridad}\n"
                        f"- Estado: {self.estado}\n\n"
                        f"Puedes iniciar sesión en el sistema para más detalles:\n{URL_SISTEMA}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[self.tecnico_asignado.email],
                    connection=connection
                )
                email.send()
            except Exception as e:
                logger.error(f"Error al enviar correo para Ticket ID {self.id}: {e}")

class FraseMotivacional(models.Model):
    frase = models.CharField(max_length=500)
    personaje = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.personaje}: {self.frase}'    
    

# Modelo de Insumo (para la importación de datos desde Excel)
class Insumo(models.Model):
    renglon = models.IntegerField()
    codigo_insumo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=500)
    caracteristicas = models.TextField(blank=True, null=True)
    nombre_presentacion = models.CharField(max_length=500)
    cantidad_unidad_presentacion = models.CharField(max_length=100)
    codigo_presentacion = models.CharField(max_length=100)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.codigo_insumo} - {self.nombre}"


# Modelo para la fecha de insumo (para la importación de datos desde Excel)
class FechaInsumo(models.Model):
    fechainsumo = models.DateField()  

    def __str__(self):
        return f"{self.fechainsumo}"