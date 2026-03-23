from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import UsuarioUbicacionDiploma

GRUPO_DIPLOMAS = "Diplomas"
GRUPO_GESTOR_DIPLOMAS = "Gestor_Diplomas"

User = get_user_model()


def is_diplomas_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.groups.filter(name=GRUPO_DIPLOMAS).exists()))


def is_diplomas_manager(user):
    return bool(user and user.is_authenticated and user.groups.filter(name=GRUPO_GESTOR_DIPLOMAS).exists())


def can_access_diplomas(user):
    return is_diplomas_admin(user) or is_diplomas_manager(user)


def get_user_location_assignment(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return user.asignacion_ubicacion_diplomas
    except UsuarioUbicacionDiploma.DoesNotExist:
        return None


def get_user_location(user):
    assignment = get_user_location_assignment(user)
    return assignment.ubicacion if assignment else None


def build_diplomas_scope(user):
    is_admin = is_diplomas_admin(user)
    is_manager = is_diplomas_manager(user)
    location = None if is_admin else get_user_location(user)
    assignment = None if is_admin else get_user_location_assignment(user)
    return {
        "is_admin": is_admin,
        "is_manager": is_manager,
        "location": location,
        "assignment": assignment,
        "menu_label": "Diplomas" if is_admin or not location else location.nombre,
        "can_manage_locations": is_admin,
        "has_access": is_admin or is_manager,
        "has_location": bool(location),
    }


def scope_queryset(queryset, scope, field_name="ubicacion"):
    if scope.get("is_admin"):
        return queryset
    location = scope.get("location")
    if not location:
        return queryset.none()
    return queryset.filter(**{field_name: location})


def enforce_scope_for_object(obj, scope, field_name="ubicacion"):
    if scope.get("is_admin"):
        return obj
    location = scope.get("location")
    if not location or getattr(obj, field_name) != location:
        raise PermissionDenied("No tiene permiso para acceder a este recurso.")
    return obj


def diplomas_access_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("signin")
        if not can_access_diplomas(request.user):
            raise PermissionDenied("No tiene permisos para acceder al módulo de Diplomas.")
        scope = build_diplomas_scope(request.user)
        if scope["is_manager"] and not scope["has_location"]:
            messages.error(request, "Su usuario Gestor_Diplomas no tiene una ubicación asignada. Contacte a un administrador del módulo.")
            return redirect("diplomas:diplomas_dahsboard") if request.path != "/diplomas/dashboard/" else view_func(request, *args, **kwargs)
        request.diplomas_scope = scope
        return view_func(request, *args, **kwargs)

    return _wrapped


def attach_diplomas_context(context, request):
    scope = getattr(request, "diplomas_scope", build_diplomas_scope(request.user))
    context.setdefault("diplomas_scope", scope)
    context.setdefault("diplomas_menu_label", scope["menu_label"])
    context.setdefault("diplomas_user_location", scope.get("location"))
    return context


def available_manager_users():
    return User.objects.filter(groups__name=GRUPO_GESTOR_DIPLOMAS).order_by("username").distinct()
