# context_processors.py
from .models import FraseMotivacional
import random

def frase_del_dia(request):
    # Obtener todas las frases
    frases = FraseMotivacional.objects.all()
    
    # Verificar si hay frases disponibles
    if frases.exists():
        frase = random.choice(frases)
    else:
        # Si no hay frases, puedes devolver un valor predeterminado o None
        frase = None
    
    return {
        'frase_del_dia': frase
    }

def grupo_usuario(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'es_departamento': request.user.groups.filter(name='Departamento').exists(),
        'es_administrador': request.user.groups.filter(name='Administrador').exists(),
        'es_scompras': request.user.groups.filter(name='scompras').exists(),
        'es_compras': request.user.groups.filter(name='COMPRAS').exists(),
    }


def scompras_roles(request):
    is_analista = (
        request.user.is_authenticated
        and request.user.groups.filter(name__iexact="analista").exists()
    )
    return {
        "is_analista": is_analista,
    }


from .models import Institucion

def datos_institucion(request):
    try:
        institucion = Institucion.objects.first()
    except Institucion.DoesNotExist:
        institucion = None

    return {
        'institucion': institucion
    }

from django.conf import settings
from scompras_app.models_empleados import Empleado

def empleado_context(request):
    if not request.user.is_authenticated:
        return {}

    empleado = Empleado.objects.using('tickets_db').filter(user=request.user).first()

    foto_url = None
    if empleado and empleado.imagen:
        raw_url = empleado.imagen.url  # Django genera /media/card_images/archivo.jpg

        # Si no incluye /media/
        if not raw_url.startswith('/media/'):
            raw_url = f"/media/{raw_url.lstrip('/')}"

        foto_url = f"{settings.MEDIA_SERVER_TICKETS}{raw_url}"

    return {
        "empleado": empleado,
        "empleado_foto_url": foto_url
    }


from django.conf import settings

def media_server_tickets(request):
    return {'MEDIA_SERVER_TICKETS': settings.MEDIA_SERVER_TICKETS}


from .utils import is_admin, is_presupuesto

def permisos_configuracion(request):
    if not request.user.is_authenticated:
        return {
            'es_admin': False,
            'es_presupuesto': False,
            'es_compras': False,
            'puede_ver_configuracion': False,
            'puede_ver_presupuesto': False,
        }

    es_admin = request.user.groups.filter(name='Administrador').exists()
    es_presupuesto = request.user.groups.filter(name='PRESUPUESTO').exists()
    es_compras = request.user.groups.filter(name='COMPRAS').exists()

    return {
        'es_admin': es_admin,
        'es_presupuesto': es_presupuesto,
        'es_compras': es_compras,
        'puede_ver_configuracion': es_admin,
        'puede_ver_presupuesto': es_admin or es_presupuesto,
    }
