# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import IntegrityError


from .models import DetalleFactura, AsignacionDetalleFactura, Kardex, User, Perfil, UsuarioDepartamento, DetalleRequerimiento
import logging
from django.core.mail import send_mail


# Logger para errores
logger = logging.getLogger(__name__)

@receiver(post_save, sender=DetalleFactura)
def crear_kardex_ingreso(sender, instance, created, **kwargs):
    """
    Crea un movimiento de ingreso en el Kardex cuando se guarda un DetalleFactura.
    """
    if created:
        Kardex.objects.create(
            articulo=instance.articulo,
            tipo_movimiento='INGRESO',
            cantidad=instance.cantidad,
            observacion=f'Ingreso desde Form 1H {instance.form1h.numero_serie_completo}',
            fuente_factura=instance
        )

@receiver(post_save, sender=DetalleRequerimiento)
def crear_kardex_salida_despacho(sender, instance, **kwargs):
    """
    Crea un movimiento de salida en el Kardex cuando el estado de un
    DetalleRequerimiento cambia a 'despachado'.
    """
    if instance.estado == 'despachado' and instance.cantidad_despachada > 0:
        try:
            Kardex.objects.create(
                articulo=instance.articulo,
                tipo_movimiento='SALIDA',
                cantidad=instance.cantidad_despachada,
                observacion=f'Requerimiento #{instance.requerimiento.id} para {instance.requerimiento.departamento.nombre}',
                fuente_despacho=instance
            )
        except IntegrityError:
            logger.info(f"Intento de crear un Kardex duplicado para DetalleRequerimiento {instance.id}. Se ha ignorado.")
            pass
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'perfil'):
        Perfil.objects.create(usuario=instance)
        
        
import logging
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

