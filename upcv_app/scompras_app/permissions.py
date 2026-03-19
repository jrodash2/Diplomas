"""Helpers reutilizables de permisos por grupos para scompras."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.shortcuts import render

GRUPO_ADMIN = "Administrador"
GRUPO_PRESUPUESTO = "PRESUPUESTO"
GRUPO_COMPRAS = "COMPRAS"


def is_in_group(user, group_name: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=group_name).exists()


def is_presupuesto(user) -> bool:
    return is_in_group(user, GRUPO_PRESUPUESTO)


def is_compras(user) -> bool:
    return is_in_group(user, GRUPO_COMPRAS)


def is_admin_group(user) -> bool:
    return is_in_group(user, GRUPO_ADMIN)


def is_super_or_admin(user) -> bool:
    return getattr(user, "is_superuser", False) or is_admin_group(user)


def can_manage_budget(user) -> bool:
    """Permite pantallas/acciones presupuestarias (sin incluir COMPRAS)."""
    return is_super_or_admin(user) or is_presupuesto(user)


def can_manage_cdp(user) -> bool:
    """Permite CDP/CDO únicamente a admin/superuser/PRESUPUESTO."""
    return can_manage_budget(user) and not is_compras(user)


def can_assign_analyst_or_process(user) -> bool:
    """Asignación de analista/tipo de proceso: solo admin/superuser."""
    if getattr(user, "is_superuser", False):
        return True
    if is_presupuesto(user):
        return False
    return is_admin_group(user)


def group_required(group_names):
    """Permite acceso solo a usuarios autenticados dentro de grupos permitidos."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            allowed = request.user.is_superuser or request.user.groups.filter(
                name__in=group_names
            ).exists()
            if allowed:
                return view_func(request, *args, **kwargs)

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"detail": "Sin permisos"}, status=403)
            return render(request, "scompras/403.html", status=403)

        return _wrapped_view

    return decorator


def sync_compras_group_permissions(group_model=Group, permission_model=None):
    """Sincroniza permisos COMPRAS copiando PRESUPUESTO y removiendo CDP/CDO/presupuesto.

    Esta función existe para reutilizarse en migraciones y comandos.
    """
    presupuesto_group, _ = group_model.objects.get_or_create(name=GRUPO_PRESUPUESTO)
    compras_group, _ = group_model.objects.get_or_create(name=GRUPO_COMPRAS)

    compras_group.permissions.set(presupuesto_group.permissions.all())

    if permission_model is None:
        from django.contrib.auth.models import Permission as permission_model

    blocked_tokens = (
        "presupuesto",
        "renglon",
        "cdp",
        "cdo",
        "kardex",
        "constanciadisponibilidad",
    )
    perms_to_remove = [
        perm for perm in permission_model.objects.all()
        if any(token in perm.codename.lower() for token in blocked_tokens)
    ]
    compras_group.permissions.remove(*perms_to_remove)
    return compras_group
