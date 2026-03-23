import json
import os
from uuid import uuid4

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from PIL import Image, UnidentifiedImageError

from empleados_app.models import Empleado

from .design_engine import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    build_design_definition,
    build_design_editor_payload,
    build_diploma_render_context,
    ensure_design_definition,
    normalize_definition_from_elements,
)
from .forms import (
    AgregarEmpleadoCursoForm,
    CursoForm,
    DisenoDiplomaForm,
    FirmaForm,
    UbicacionDiplomaForm,
    UsuarioUbicacionDiplomaForm,
)
from .models import (
    Curso,
    CursoEmpleado,
    DisenoDiploma,
    Firma,
    UbicacionDiploma,
    UsuarioUbicacionDiploma,
)
from .utils import attach_diplomas_context, diplomas_access_required, enforce_scope_for_object, scope_queryset


# Helpers

def render_diplomas(request, template_name, context=None):
    context = context or {}
    return render(request, template_name, attach_diplomas_context(context, request))


def get_scope(request):
    return getattr(request, "diplomas_scope", {})


def get_course_or_404(request, **lookup):
    curso = get_object_or_404(Curso.objects.select_related("ubicacion", "diseno_diploma"), **lookup)
    return enforce_scope_for_object(curso, get_scope(request))


def get_design_or_404(request, **lookup):
    diseno = get_object_or_404(DisenoDiploma.objects.select_related("ubicacion"), **lookup)
    return enforce_scope_for_object(diseno, get_scope(request))


def get_signature_or_404(request, **lookup):
    firma = get_object_or_404(Firma.objects.select_related("ubicacion"), **lookup)
    return enforce_scope_for_object(firma, get_scope(request))


def get_location_or_404(request, **lookup):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied("Solo el grupo Diplomas puede administrar ubicaciones.")
    return get_object_or_404(UbicacionDiploma, **lookup)


# Dashboard

@diplomas_access_required
def diplomas_dahsboard(request):
    scope = get_scope(request)
    cursos = scope_queryset(Curso.objects.select_related("ubicacion"), scope).order_by("-creado_en")
    firmas = scope_queryset(Firma.objects.select_related("ubicacion"), scope).order_by("-creado_en")
    disenos = scope_queryset(DisenoDiploma.objects.select_related("ubicacion"), scope).order_by("-creado_en")
    participantes = CursoEmpleado.objects.filter(curso__in=cursos)
    ubicaciones = UbicacionDiploma.objects.order_by("nombre") if scope.get("is_admin") else UbicacionDiploma.objects.filter(id=getattr(scope.get("location"), "id", None))

    context = {
        "total_cursos": cursos.count(),
        "total_firmas": firmas.count(),
        "total_disenos": disenos.count(),
        "total_participantes": participantes.count(),
        "total_ubicaciones": ubicaciones.count(),
        "cursos_recientes": cursos[:5],
        "firmas_recientes": firmas[:5],
        "disenos_recientes": disenos[:5],
    }
    return render_diplomas(request, "diplomas/dashboard.html", context)


# Ubicaciones

@diplomas_access_required
def ubicaciones_lista(request):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    ubicaciones = UbicacionDiploma.objects.order_by("nombre")
    return render_diplomas(request, "diplomas/ubicaciones_lista.html", {
        "ubicaciones": ubicaciones,
        "form": UbicacionDiplomaForm(),
    })


@diplomas_access_required
def crear_ubicacion(request):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    if request.method == "POST":
        form = UbicacionDiplomaForm(request.POST)
        if form.is_valid():
            ubicacion = form.save(commit=False)
            ubicacion.creado_por = request.user
            ubicacion.save()
            messages.success(request, "Ubicación creada correctamente.")
        else:
            messages.error(request, "No se pudo crear la ubicación.")
    return redirect("diplomas:ubicaciones_lista")


@diplomas_access_required
def editar_ubicacion(request, ubicacion_id):
    ubicacion = get_location_or_404(request, id=ubicacion_id)
    if request.method == "POST":
        form = UbicacionDiplomaForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Ubicación actualizada correctamente.")
            return redirect("diplomas:ubicaciones_lista")
    else:
        form = UbicacionDiplomaForm(instance=ubicacion)
    return render_diplomas(request, "diplomas/editar_ubicacion.html", {"form": form, "ubicacion": ubicacion})


@diplomas_access_required
def eliminar_ubicacion(request, ubicacion_id):
    ubicacion = get_location_or_404(request, id=ubicacion_id)
    if request.method == "POST":
        try:
            ubicacion.delete()
            messages.success(request, "Ubicación eliminada correctamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar la ubicación porque tiene registros relacionados.")
    return redirect("diplomas:ubicaciones_lista")


@diplomas_access_required
def asignaciones_ubicacion_lista(request):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    asignaciones = UsuarioUbicacionDiploma.objects.select_related("usuario", "ubicacion", "asignado_por").order_by("usuario__username")
    return render_diplomas(request, "diplomas/asignaciones_ubicacion_lista.html", {
        "asignaciones": asignaciones,
        "form": UsuarioUbicacionDiplomaForm(),
    })


@diplomas_access_required
def crear_asignacion_ubicacion(request):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    if request.method == "POST":
        form = UsuarioUbicacionDiplomaForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data["usuario"]
            ubicacion = form.cleaned_data["ubicacion"]
            UsuarioUbicacionDiploma.objects.update_or_create(
                usuario=usuario,
                defaults={"ubicacion": ubicacion, "asignado_por": request.user},
            )
            messages.success(request, "Asignación guardada correctamente.")
        else:
            messages.error(request, "No se pudo guardar la asignación.")
    return redirect("diplomas:asignaciones_ubicacion_lista")


@diplomas_access_required
def editar_asignacion_ubicacion(request, asignacion_id):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    asignacion = get_object_or_404(UsuarioUbicacionDiploma, id=asignacion_id)
    if request.method == "POST":
        form = UsuarioUbicacionDiplomaForm(request.POST, instance=asignacion)
        if form.is_valid():
            form.save(assigned_by=request.user)
            messages.success(request, "Asignación actualizada correctamente.")
            return redirect("diplomas:asignaciones_ubicacion_lista")
    else:
        form = UsuarioUbicacionDiplomaForm(instance=asignacion)
    return render_diplomas(request, "diplomas/editar_asignacion_ubicacion.html", {"form": form, "asignacion": asignacion})


@diplomas_access_required
def eliminar_asignacion_ubicacion(request, asignacion_id):
    if not get_scope(request).get("is_admin"):
        raise PermissionDenied
    asignacion = get_object_or_404(UsuarioUbicacionDiploma, id=asignacion_id)
    if request.method == "POST":
        asignacion.delete()
        messages.success(request, "Asignación eliminada correctamente.")
    return redirect("diplomas:asignaciones_ubicacion_lista")


# Firmas

@diplomas_access_required
def firmas_lista(request):
    scope = get_scope(request)
    firmas = scope_queryset(Firma.objects.select_related("ubicacion"), scope).order_by("-id")
    form = FirmaForm(scope=scope)
    return render_diplomas(request, "diplomas/firmas_lista.html", {"firmas": firmas, "form": form})


@diplomas_access_required
def crear_firma(request):
    scope = get_scope(request)
    if request.method == "POST":
        form = FirmaForm(request.POST, request.FILES, scope=scope)
        if form.is_valid():
            form.save()
            messages.success(request, "Firma creada correctamente.")
        else:
            messages.error(request, "Error al crear la firma.")
    return redirect("diplomas:firmas_lista")


@diplomas_access_required
def editar_firma(request, firma_id):
    firma = get_signature_or_404(request, id=firma_id)
    scope = get_scope(request)
    if request.method == "POST":
        form = FirmaForm(request.POST, request.FILES, instance=firma, scope=scope)
        if form.is_valid():
            form.save()
            messages.success(request, "Firma actualizada correctamente.")
            return redirect("diplomas:firmas_lista")
    else:
        form = FirmaForm(instance=firma, scope=scope)
    return render_diplomas(request, "diplomas/editar_firma.html", {"form": form, "firma": firma})


@diplomas_access_required
def eliminar_firma(request, firma_id):
    firma = get_signature_or_404(request, id=firma_id)
    if request.method == "POST":
        try:
            firma.delete()
            messages.success(request, "Firma eliminada correctamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar la firma porque está asociada a cursos.")
    return redirect("diplomas:firmas_lista")


# Diseños

@diplomas_access_required
def disenos_lista(request):
    scope = get_scope(request)
    disenos = scope_queryset(DisenoDiploma.objects.select_related("ubicacion"), scope).order_by("-id")
    form = DisenoDiplomaForm(scope=scope)
    return render_diplomas(request, "diplomas/disenos_lista.html", {"disenos": disenos, "form": form})


@diplomas_access_required
def crear_diseno(request):
    scope = get_scope(request)
    if request.method == "POST":
        form = DisenoDiplomaForm(request.POST, request.FILES, scope=scope)
        if form.is_valid():
            diseno = form.save()
            ensure_design_definition(diseno)
            messages.success(request, "Diseño de diploma creado correctamente.")
        else:
            messages.error(request, "No se pudo crear el diseño. Revise los campos.")
    return redirect("diplomas:disenos_lista")


@diplomas_access_required
def editar_diseno(request, diseno_id):
    diseno = get_design_or_404(request, id=diseno_id)
    scope = get_scope(request)
    if request.method == "POST":
        form = DisenoDiplomaForm(request.POST, request.FILES, instance=diseno, scope=scope)
        if form.is_valid():
            form.save()
            messages.success(request, "Diseño actualizado correctamente.")
            return redirect("diplomas:disenos_lista")
    else:
        form = DisenoDiplomaForm(instance=diseno, scope=scope)

    return render_diplomas(request, "diplomas/editar_diseno.html", {"form": form, "diseno": diseno})


@ensure_csrf_cookie
@diplomas_access_required
def modificar_diseno_visual(request, diseno_id):
    diseno = get_design_or_404(request, id=diseno_id)
    editor_payload = build_design_editor_payload(diseno)
    definition = editor_payload["definition"]
    context = {
        "diseno": diseno,
        "elementos_json": definition,
        "preview_context_json": editor_payload["preview_context"],
        "fondo_url": definition["elements"]["fondo_diploma"]["image_url"],
        "canvas_width": CANVAS_WIDTH,
        "canvas_height": CANVAS_HEIGHT,
    }
    return render_diplomas(request, "diplomas/editor_diseno_visual.html", context)


@diplomas_access_required
def guardar_diseno_visual(request, diseno_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    diseno = get_design_or_404(request, id=diseno_id)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

    incoming_elements = None
    if isinstance(payload, dict):
        if isinstance(payload.get("elementos"), dict):
            incoming_elements = payload["elementos"]
        elif isinstance(payload.get("elements"), dict):
            incoming_elements = payload["elements"]
        elif isinstance(payload.get("definition"), dict) and isinstance(payload["definition"].get("elements"), dict):
            incoming_elements = payload["definition"]["elements"]

    if not isinstance(incoming_elements, dict) or not incoming_elements:
        return JsonResponse({"success": False, "error": "Debe enviar un mapa válido de elementos."}, status=400)

    try:
        normalized_definition = normalize_definition_from_elements(diseno, incoming_elements)
        diseno.estilos = normalized_definition
        diseno.save(update_fields=["estilos", "actualizado_en"])
        diseno.refresh_from_db(fields=["estilos", "actualizado_en"])
    except Exception as exc:
        return JsonResponse({"success": False, "error": f"No se pudo guardar el diseño: {exc}"}, status=500)

    return JsonResponse({
        "success": True,
        "message": "Diseño guardado correctamente.",
        "elementos": diseno.estilos.get("elements", {}),
        "definition": diseno.estilos,
    })


@diplomas_access_required
def subir_imagen_diseno_visual(request, diseno_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

    diseno = get_design_or_404(request, id=diseno_id)
    uploaded_file = request.FILES.get("image")
    if not uploaded_file:
        return JsonResponse({"success": False, "error": "Debe seleccionar una imagen."}, status=400)

    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    extension = os.path.splitext(uploaded_file.name or "")[1].lower()
    if extension not in allowed_extensions:
        return JsonResponse({"success": False, "error": "Formato no permitido. Use PNG, JPG, JPEG o WEBP."}, status=400)

    if not str(getattr(uploaded_file, "content_type", "")).startswith("image/"):
        return JsonResponse({"success": False, "error": "El archivo seleccionado no es una imagen válida."}, status=400)

    try:
        image_bytes = uploaded_file.read()
        Image.open(ContentFile(image_bytes)).verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return JsonResponse({"success": False, "error": "No se pudo validar la imagen enviada."}, status=400)
    finally:
        uploaded_file.seek(0)

    folder_name = slugify(diseno.nombre) or f"diseno-{diseno.id}"
    filename = f"{uuid4().hex}{extension}"
    storage_path = f"diplomas/editor/{folder_name}/{filename}"
    saved_path = default_storage.save(storage_path, uploaded_file)
    file_url = default_storage.url(saved_path)

    return JsonResponse({
        "success": True,
        "message": "Imagen subida correctamente.",
        "image_url": file_url,
        "path": saved_path,
        "filename": os.path.basename(saved_path),
    })


@diplomas_access_required
def eliminar_diseno(request, diseno_id):
    diseno = get_design_or_404(request, id=diseno_id)
    if request.method == "POST":
        if diseno.cursos.exists():
            messages.error(request, "No se puede eliminar el diseño porque está asignado a uno o más cursos.")
        else:
            try:
                diseno.delete()
                messages.success(request, "Diseño eliminado correctamente.")
            except ProtectedError:
                messages.error(request, "No se puede eliminar el diseño por integridad de datos.")
    return redirect("diplomas:disenos_lista")


# Cursos

@diplomas_access_required
def cursos_lista(request):
    scope = get_scope(request)
    cursos = scope_queryset(Curso.objects.select_related("ubicacion", "diseno_diploma"), scope).order_by("-creado_en")
    form = CursoForm(scope=scope)
    return render_diplomas(request, "diplomas/cursos_lista.html", {"cursos": cursos, "form": form})


@diplomas_access_required
def crear_curso_modal(request):
    scope = get_scope(request)
    if request.method == "POST":
        form = CursoForm(request.POST, scope=scope)
        if form.is_valid():
            form.save()
            messages.success(request, "Curso creado correctamente.")
            return redirect("diplomas:cursos_lista")
        messages.error(request, "Corrige los errores del formulario.")
    return redirect("diplomas:cursos_lista")


@diplomas_access_required
def editar_curso(request, curso_id):
    curso = get_course_or_404(request, id=curso_id)
    scope = get_scope(request)

    if request.method == "POST":
        form = CursoForm(request.POST, instance=curso, scope=scope)
        if form.is_valid():
            form.save()
            messages.success(request, "Curso actualizado correctamente.")
            return redirect("diplomas:cursos_lista")
    else:
        form = CursoForm(instance=curso, scope=scope)

    return render_diplomas(request, "diplomas/editar_curso.html", {"form": form, "curso": curso})


@diplomas_access_required
def detalle_curso(request, curso_id):
    curso = get_course_or_404(request, id=curso_id)
    participantes = CursoEmpleado.objects.filter(curso=curso).select_related("empleado")
    total_participantes = participantes.count()

    return render_diplomas(request, "diplomas/detalle_curso.html", {
        "curso": curso,
        "participantes": participantes,
        "total_participantes": total_participantes
    })


@diplomas_access_required
def eliminar_participante(request, curso_id, participante_id):
    curso = get_course_or_404(request, id=curso_id)
    asignacion = get_object_or_404(CursoEmpleado, id=participante_id, curso=curso)
    asignacion.delete()
    messages.success(request, "Participante eliminado del curso.")
    return redirect("diplomas:detalle_curso", curso_id=curso.id)


@diplomas_access_required
def agregar_empleado_a_curso(request):
    scope = get_scope(request)
    if request.method == "POST":
        form = AgregarEmpleadoCursoForm(request.POST, scope=scope)
        if form.is_valid():
            curso = form.cleaned_data["curso"]
            enforce_scope_for_object(curso, scope)
            empleado = form.cleaned_data["empleado"]

            if CursoEmpleado.objects.filter(curso=curso, empleado=empleado).exists():
                messages.warning(request, "Este empleado ya está asignado a este curso.")
                return redirect("diplomas:agregar_empleado_curso")

            CursoEmpleado.objects.create(curso=curso, empleado=empleado)
            messages.success(request, "Empleado agregado correctamente al curso.")
            return redirect("diplomas:agregar_empleado_curso")
    else:
        form = AgregarEmpleadoCursoForm(scope=scope)

    return render_diplomas(request, "diplomas/agregar_empleado_curso.html", {"form": form})


@diplomas_access_required
def agregar_empleado_detalle(request, curso_id):
    curso = get_course_or_404(request, id=curso_id)
    dpi = request.POST.get("dpi")

    if not dpi:
        messages.error(request, "Debe ingresar un DPI.")
        return redirect("diplomas:detalle_curso", curso_id=curso.id)

    try:
        empleado = Empleado.objects.get(dpi=dpi)
    except Empleado.DoesNotExist:
        messages.error(request, "No existe un empleado con ese DPI.")
        return redirect("diplomas:detalle_curso", curso_id=curso.id)

    if CursoEmpleado.objects.filter(curso=curso, empleado=empleado).exists():
        messages.warning(request, "El empleado ya está inscrito en este curso.")
        return redirect("diplomas:detalle_curso", curso_id=curso.id)

    CursoEmpleado.objects.create(curso=curso, empleado=empleado, fecha_asignacion=timezone.now())
    messages.success(request, "Empleado agregado correctamente.")
    return redirect("diplomas:detalle_curso", curso_id=curso.id)


@diplomas_access_required
def buscar_empleado_por_dpi(request):
    dpi = request.GET.get("dpi")
    if not dpi:
        return JsonResponse({"error": "No se envió DPI"}, status=400)

    try:
        empleado = Empleado.objects.get(dpi=dpi)
        return JsonResponse({
            "existe": True,
            "nombres": empleado.nombres,
            "apellidos": empleado.apellidos,
            "nombre_completo": f"{empleado.nombres} {empleado.apellidos}"
        })
    except Empleado.DoesNotExist:
        return JsonResponse({"existe": False})


@diplomas_access_required
def ver_diploma(request, curso_id, participante_id):
    curso_empleado = get_object_or_404(CursoEmpleado.objects.select_related("curso", "curso__ubicacion", "empleado"), id=participante_id, curso_id=curso_id)
    enforce_scope_for_object(curso_empleado.curso, get_scope(request))
    context = build_diploma_render_context(curso_empleado)
    return render_diplomas(request, "diplomas/ver_diploma.html", context)


@csrf_exempt
@diplomas_access_required
def guardar_posiciones(request, curso_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    curso = get_course_or_404(request, id=curso_id)

    try:
        data = json.loads(request.body)
    except Exception as e:
        return JsonResponse({"error": f"JSON inválido: {str(e)}"}, status=400)

    posiciones_limpias = {}
    for key, values in data.items():
        posiciones_limpias[key] = {
            "left": int(values.get("left", 0)),
            "top": int(values.get("top", 0)),
            "width": int(values.get("width", 0)),
            "height": int(values.get("height", 0)),
            "scale": float(values.get("scale", 1)),
        }

    if curso.diseno_diploma:
        if curso.diseno_diploma.ubicacion_id and curso.ubicacion_id != curso.diseno_diploma.ubicacion_id:
            return JsonResponse({"error": "El diseño del curso no coincide con su ubicación."}, status=400)
        current_definition = build_design_definition(curso.diseno_diploma, None)
        patched_elements = current_definition["elements"]
        for key, values in posiciones_limpias.items():
            if key not in patched_elements:
                continue
            patched_elements[key]["x"] = values["left"]
            patched_elements[key]["y"] = values["top"]
            patched_elements[key]["width"] = values["width"]
            patched_elements[key]["height"] = values["height"]

        curso.diseno_diploma.estilos = normalize_definition_from_elements(curso.diseno_diploma, patched_elements)
        curso.diseno_diploma.save(update_fields=["estilos", "actualizado_en"])
    else:
        curso.posiciones = posiciones_limpias
        curso.save(update_fields=["posiciones"])

    return JsonResponse({"success": True})
