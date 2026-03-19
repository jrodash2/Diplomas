from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Administrador").exists()
    )


def is_presupuesto(user):
    return user.is_authenticated and user.groups.filter(name="PRESUPUESTO").exists()


def is_scompras(user):
    return user.is_authenticated and user.groups.filter(name="scompras").exists()


def is_analista(user):
    return user.is_authenticated and user.groups.filter(name__iexact="analista").exists()


def is_compras(user):
    return user.is_authenticated and user.groups.filter(name__iexact="COMPRAS").exists()


def is_admin_or_presupuesto_or_compras(user):
    return is_admin(user) or is_presupuesto(user) or is_compras(user)


def puede_asignar_proceso(user):
    return is_admin(user) or is_compras(user)


def puede_editar_solicitud(user):
    return is_admin(user) or is_presupuesto(user)



def puede_ver_departamentos(user):
    """Acceso al listado de departamentos según reglas actuales + COMPRAS."""
    return (
        is_admin_or_presupuesto_or_compras(user)
        or is_scompras(user)
        or user.groups.filter(name='Departamento').exists()
    )


def puede_ver_detalle_departamento(user, departamento):
    """Acceso al detalle del departamento sin alterar reglas existentes de asignación."""
    if is_admin_or_presupuesto_or_compras(user):
        return True

    if user.groups.filter(name__in=['Departamento', 'scompras']).exists():
        from scompras_app.models import UsuarioDepartamento

        return UsuarioDepartamento.objects.filter(
            usuario=user,
            departamento=departamento
        ).exists()

    return False


def puede_ver_detalle_solicitud(user):
    """Acceso base a pantalla detalle de solicitud (acciones sensibles se validan aparte)."""
    return (
        is_admin_or_presupuesto_or_compras(user)
        or is_scompras(user)
        or is_analista(user)
        or user.groups.filter(name='Departamento').exists()
    )

def es_presupuesto(user):
    return user.is_authenticated and user.groups.filter(name="PRESUPUESTO").exists()

def puede_imprimir_cdp(user):
    return user.is_authenticated and (
        user.groups.filter(name="Administrador").exists()
        or user.groups.filter(name="PRESUPUESTO").exists()
    )


def bloquear_presupuesto(view_func):
    """Bloquea acciones específicas para usuarios del grupo PRESUPUESTO."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if es_presupuesto(request.user):
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.method == "POST":
                return JsonResponse({"success": False, "error": "No autorizado."}, status=403)
            return redirect(f"/no-autorizado/?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def deny_analista(view_func):
    """Bloquea acciones específicas para usuarios del grupo analista."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if is_analista(request.user):
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "No autorizado."}, status=403)
            return HttpResponseForbidden("No autorizado.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_only_config(view_func):
    """Restringe las vistas de configuración únicamente a administradores."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if is_admin(request.user):
            return view_func(request, *args, **kwargs)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"detail": "No autorizado."}, status=403)
        response = redirect(reverse("scompras:acceso_denegado"))
        response.status_code = 403
        return response
    return _wrapped_view


class AdminOnlyConfigMixin:
    """Mixin para asegurar acceso administrativo en vistas de configuración."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if is_admin(request.user):
            return super().dispatch(request, *args, **kwargs)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"detail": "No autorizado."}, status=403)
        response = redirect(reverse("scompras:acceso_denegado"))
        response.status_code = 403
        return response


def grupo_requerido(*nombres_grupos):
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and (
                request.user.groups.filter(name__in=nombres_grupos).exists() or request.user.is_superuser
            ):
                return view_func(request, *args, **kwargs)
            # Redirigir a la vista de acceso denegado
            return redirect(reverse('scompras:acceso_denegado'))
        return _wrapped_view
    return decorador


def cdps_sumables(qs):
    """Retorna solo CDP reservados para sumas consolidadas."""
    from scompras_app.models import CDP

    return qs.filter(estado=CDP.Estado.RESERVADO)


def obtener_pasos_catalogo(solicitud):
    from django.db.models import Q
    from scompras_app.models import ProcesoCompraPaso

    if not solicitud.tipo_proceso:
        return []
    filtro = Q(tipo=solicitud.tipo_proceso, activo=True)
    if solicitud.subtipo_proceso:
        filtro &= (Q(subtipo__isnull=True) | Q(subtipo=solicitud.subtipo_proceso))
    else:
        filtro &= Q(subtipo__isnull=True)
    return list(ProcesoCompraPaso.objects.filter(filtro).order_by("numero"))


def inicializar_pasos_estado(solicitud):
    from scompras_app.models import SolicitudPasoEstado

    pasos = obtener_pasos_catalogo(solicitud)
    for paso in pasos:
        SolicitudPasoEstado.objects.get_or_create(solicitud=solicitud, paso=paso)


def recalcular_paso_actual(solicitud):
    pasos = obtener_pasos_catalogo(solicitud)
    if not pasos:
        solicitud.paso_actual = 1
        solicitud.save(update_fields=["paso_actual"])
        return
    estados = {
        estado.paso_id: estado
        for estado in solicitud.pasos_estado.filter(paso__in=pasos)
    }
    siguiente = None
    for paso in pasos:
        estado = estados.get(paso.id)
        if not estado or not estado.completado:
            siguiente = paso.numero
            break
    solicitud.paso_actual = siguiente if siguiente is not None else pasos[-1].numero
    solicitud.save(update_fields=["paso_actual"])
