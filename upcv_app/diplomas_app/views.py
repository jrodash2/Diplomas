import json

from django.contrib import messages
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from empleados_app.models import ConfiguracionGeneral, Empleado

from .forms import AgregarEmpleadoCursoForm, CursoForm, DisenoDiplomaForm, FirmaForm
from .models import Curso, CursoEmpleado, DisenoDiploma, Firma


DEFAULT_DIPLOMA_ELEMENTS = {
    "logo1": {"x": 1200, "y": 20, "width": 150, "height": 150, "font_size": 20, "color": "#000000", "align": "left", "content": "{{ logo_1 }}", "type": "logo", "z_index": 1},
    "logo2": {"x": 1650, "y": 20, "width": 150, "height": 150, "font_size": 20, "color": "#000000", "align": "left", "content": "{{ logo_2 }}", "type": "logo", "z_index": 2},
    "institucion": {"x": 1200, "y": 120, "width": 1100, "height": 120, "font_size": 100, "color": "#000000", "align": "center", "content": "{{ institucion_nombre }}", "type": "text", "z_index": 3},
    "titulo": {"x": 1050, "y": 450, "width": 1400, "height": 100, "font_size": 55, "color": "#000000", "align": "center", "content": "OTORGA EL PRESENTE DIPLOMA A:", "type": "text", "z_index": 4},
    "nombre": {"x": 1150, "y": 580, "width": 1300, "height": 160, "font_size": 120, "color": "#000000", "align": "center", "content": "{{ participante_nombre }}", "type": "text", "z_index": 5},
    "curso": {"x": 1250, "y": 780, "width": 1000, "height": 100, "font_size": 55, "color": "#000000", "align": "center", "content": "{{ curso_nombre }}", "type": "text", "z_index": 6},
    "horas": {"x": 1260, "y": 900, "width": 1000, "height": 80, "font_size": 40, "color": "#000000", "align": "center", "content": "{{ horas }}", "type": "text", "z_index": 7},
    "fecha": {"x": 1300, "y": 1050, "width": 900, "height": 80, "font_size": 33, "color": "#000000", "align": "center", "content": "Guatemala, {{ fecha }} © UPCV", "type": "text", "z_index": 8},
    "codigo": {"x": 1400, "y": 760, "width": 900, "height": 80, "font_size": 33, "color": "#000000", "align": "left", "content": "Código- {{ codigo }}", "type": "text", "z_index": 9},
    "firmas": {"x": 800, "y": 1300, "width": 1900, "height": 500, "font_size": 28, "color": "#000000", "align": "center", "content": "{{ firmas }}", "type": "firmas", "z_index": 10},
}


CANVAS_WIDTH = 3508
CANVAS_HEIGHT = 2480


def _clamp_number(value, default, min_value=0):
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return default
    return casted if casted >= min_value else default


def _normalize_element_defaults(key, source, fallback):
    # Base mínimo seguro para evitar KeyError con configuraciones antiguas/incompletas
    base = {
        "x": 0,
        "y": 0,
        "width": 200,
        "height": 80,
        "font_size": 24,
        "color": "#000000",
        "align": "left",
        "z_index": 1,
        "content": "",
        "texto": "",
        "token": "",
        "type": "text",
    }

    data = {**base, **(fallback if isinstance(fallback, dict) else {})}
    if not isinstance(source, dict):
        # mantener consistencia de alias aún sin source
        data["texto"] = data.get("texto") or data.get("content") or ""
        data["token"] = data.get("token") or data.get("content") or ""
        return data

    data["x"] = _clamp_number(source.get("x", source.get("left")), data.get("x", 0))
    data["y"] = _clamp_number(source.get("y", source.get("top")), data.get("y", 0))
    data["width"] = _clamp_number(source.get("width", source.get("ancho")), data.get("width", 200), min_value=20)
    data["height"] = _clamp_number(source.get("height", source.get("alto")), data.get("height", 80), min_value=20)
    data["font_size"] = _clamp_number(source.get("font_size", source.get("fontSize")), data.get("font_size", 24), min_value=1)
    data["color"] = source.get("color") or data.get("color", "#000000")
    data["align"] = source.get("align", source.get("textAlign", source.get("alineacion"))) or data.get("align", "left")

    content_value = (
        source.get("content")
        or source.get("text")
        or source.get("texto")
        or source.get("token")
        or data.get("content")
        or ""
    )
    data["content"] = content_value
    data["texto"] = source.get("texto") or content_value
    data["token"] = source.get("token") or content_value

    data["z_index"] = int(_clamp_number(source.get("z_index", source.get("zIndex")), data.get("z_index", 1), min_value=1))
    data["type"] = source.get("type") or data.get("type", "text")

    data["x"] = min(max(data["x"], 0), CANVAS_WIDTH - data["width"])
    data["y"] = min(max(data["y"], 0), CANVAS_HEIGHT - data["height"])
    return data


def _build_elements_from_positions(posiciones):
    elementos = {
        key: _normalize_element_defaults(key, {}, value.copy())
        for key, value in DEFAULT_DIPLOMA_ELEMENTS.items()
    }
    if not isinstance(posiciones, dict):
        return elementos

    for key, value in posiciones.items():
        if key not in elementos:
            continue
        elementos[key] = _normalize_element_defaults(key, value, elementos[key])
    return elementos

    return elementos

def _build_diseno_elements(diseno, fallback_posiciones):
    elementos = _build_elements_from_positions(fallback_posiciones)
    if not diseno or not isinstance(diseno.estilos, dict):
        return elementos

    estilos = diseno.estilos
    source_elements = estilos.get("elements") if isinstance(estilos.get("elements"), dict) else estilos
    if not isinstance(source_elements, dict):
        return elementos

    for key, value in source_elements.items():
        if key not in elementos:
            continue
        elementos[key] = _normalize_element_defaults(key, value, elementos[key])

    return elementos


def _resolve_content(template_content, curso_empleado, config):
    empleado = curso_empleado.empleado
    curso = curso_empleado.curso
    context_map = {
        "{{ participante_nombre }}": f"{empleado.nombres} {empleado.apellidos}",
        "{{ curso_nombre }}": curso.nombre,
        "{{ fecha }}": timezone.now().strftime("%Y"),
        "{{ horas }}": "",
        "{{ codigo }}": f"{curso_empleado.id:04d}-UPCV",
        "{{ institucion_nombre }}": config.nombre_institucion if config else "",
        "{{ logo_1 }}": "",
        "{{ logo_2 }}": "",
        "{{ firmas }}": "",
    }
    resolved = template_content
    for token, value in context_map.items():
        resolved = resolved.replace(token, value)
    return resolved

def _resolve_content(template_content, curso_empleado, config):
    empleado = curso_empleado.empleado
    curso = curso_empleado.curso
    context_map = {
        "{{ participante_nombre }}": f"{empleado.nombres} {empleado.apellidos}",
        "{{ curso_nombre }}": curso.nombre,
        "{{ fecha }}": timezone.now().strftime("%Y"),
        "{{ horas }}": "",
        "{{ codigo }}": f"{curso_empleado.id:04d}-UPCV",
        "{{ institucion_nombre }}": config.nombre_institucion if config else "",
        "{{ logo_1 }}": "",
        "{{ logo_2 }}": "",
        "{{ firmas }}": "",
    }
    resolved = template_content
    for token, value in context_map.items():
        resolved = resolved.replace(token, value)
    return resolved


def eliminar_participante(request, curso_id, participante_id):
    curso = get_object_or_404(Curso, id=curso_id)
    asignacion = get_object_or_404(CursoEmpleado, id=participante_id)
    asignacion.delete()
    messages.success(request, "Participante eliminado del curso.")
    return redirect("diplomas:detalle_curso", curso_id=curso.id)


def diplomas_dahsboard(request):
    return render(request, 'diplomas/dashboard.html')


def firmas_lista(request):
    firmas = Firma.objects.all().order_by('-id')
    form = FirmaForm()
    return render(request, "diplomas/firmas_lista.html", {"firmas": firmas, "form": form})


def crear_firma(request):
    if request.method == "POST":
        form = FirmaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Firma creada correctamente.")
        else:
            messages.error(request, "Error al crear la firma.")
    return redirect("diplomas:firmas_lista")


def disenos_lista(request):
    disenos = DisenoDiploma.objects.all().order_by('-id')
    form = DisenoDiplomaForm()
    return render(request, "diplomas/disenos_lista.html", {"disenos": disenos, "form": form})


def crear_diseno(request):
    if request.method == "POST":
        form = DisenoDiplomaForm(request.POST, request.FILES)
        if form.is_valid():
            diseno = form.save(commit=False)
            if not diseno.estilos:
                diseno.estilos = {"elements": DEFAULT_DIPLOMA_ELEMENTS}
            diseno.save()
            messages.success(request, "Diseño de diploma creado correctamente.")
        else:
            messages.error(request, "No se pudo crear el diseño. Revise los campos.")
    return redirect("diplomas:disenos_lista")


def editar_diseno(request, diseno_id):
    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
    if request.method == "POST":
        form = DisenoDiplomaForm(request.POST, request.FILES, instance=diseno)
        if form.is_valid():
            form.save()
            messages.success(request, "Diseño actualizado correctamente.")
            return redirect("diplomas:disenos_lista")
    else:
        form = DisenoDiplomaForm(instance=diseno)

    return render(request, "diplomas/editar_diseno.html", {"form": form, "diseno": diseno})


def _media_url(file_field):
    try:
        return file_field.url if file_field else ""
    except Exception:
        return ""


def _real_editor_elements(diseno):
    config = ConfiguracionGeneral.objects.first()
    firmas = list(Firma.objects.order_by('id')[:2])
    firma1 = firmas[0] if len(firmas) > 0 else None
    firma2 = firmas[1] if len(firmas) > 1 else None

    base = {
        "logo_gobierno": {"key": "logo_gobierno", "label": "Logo Gobierno", "type": "imagen", "x": 1280, "y": 30, "width": 180, "height": 180, "font_size": 22, "color": "#111827", "align": "center", "z_index": 15, "token": "[[logo_gobierno]]", "texto": "", "image_url": _media_url(getattr(config, 'logotipo2', None)), "visible": True},
        "logo_upcv": {"key": "logo_upcv", "label": "Logo UPCV", "type": "imagen", "x": 1580, "y": 30, "width": 180, "height": 180, "font_size": 22, "color": "#111827", "align": "center", "z_index": 16, "token": "[[logo_upcv]]", "texto": "", "image_url": _media_url(getattr(config, 'logotipo', None)), "visible": True},
        "titulo_institucional": {"key": "titulo_institucional", "label": "Título institucional", "type": "texto", "x": 980, "y": 220, "width": 1500, "height": 120, "font_size": 56, "color": "#0f172a", "align": "center", "z_index": 20, "token": "[[institucion]]", "texto": getattr(config, 'nombre_institucion', '') or 'Unidad para la Prevención Comunitaria de la Violencia', "image_url": "", "visible": True},
        "subtitulo_diploma": {"key": "subtitulo_diploma", "label": "Subtítulo diploma", "type": "texto", "x": 1020, "y": 430, "width": 1450, "height": 100, "font_size": 50, "color": "#111827", "align": "center", "z_index": 21, "token": "[[subtitulo_diploma]]", "texto": "OTORGA EL PRESENTE DIPLOMA A:", "image_url": "", "visible": True},
        "adorno_central": {"key": "adorno_central", "label": "Adorno central", "type": "decorativo", "x": 1050, "y": 540, "width": 1380, "height": 50, "font_size": 40, "color": "#6b7280", "align": "center", "z_index": 22, "token": "[[adorno_central]]", "texto": "──────────── ✦ ────────────", "image_url": "", "visible": True},
        "codigo": {"key": "codigo", "label": "Código", "type": "texto", "x": 1410, "y": 760, "width": 850, "height": 70, "font_size": 33, "color": "#111827", "align": "left", "z_index": 23, "token": "[[codigo]]", "texto": "Código-0002-UPCV", "image_url": "", "visible": True},
        "nombre_curso": {"key": "nombre_curso", "label": "Nombre curso", "type": "texto", "x": 1060, "y": 860, "width": 1400, "height": 100, "font_size": 54, "color": "#111827", "align": "center", "z_index": 24, "token": "[[curso_nombre]]", "texto": "Nombre del Curso", "image_url": "", "visible": True},
        "participante_nombre": {"key": "participante_nombre", "label": "Nombre participante", "type": "texto", "x": 900, "y": 620, "width": 1700, "height": 170, "font_size": 110, "color": "#111827", "align": "center", "z_index": 25, "token": "[[participante_nombre]]", "texto": "Oscar Javier Peinado Monroy", "image_url": "", "visible": True},
        "fecha_texto": {"key": "fecha_texto", "label": "Fecha", "type": "texto", "x": 1230, "y": 1060, "width": 1100, "height": 70, "font_size": 33, "color": "#111827", "align": "center", "z_index": 26, "token": "[[fecha]]", "texto": "Guatemala, 2026 © UPCV", "image_url": "", "visible": True},
        "firma_1_imagen": {"key": "firma_1_imagen", "label": "Firma 1 Imagen", "type": "imagen", "x": 900, "y": 1320, "width": 280, "height": 120, "font_size": 20, "color": "#111827", "align": "center", "z_index": 30, "token": "[[firma_1_imagen]]", "texto": "", "image_url": _media_url(getattr(firma1, 'firma', None)), "visible": True},
        "firma_1_nombre": {"key": "firma_1_nombre", "label": "Firma 1 Nombre", "type": "texto", "x": 860, "y": 1450, "width": 360, "height": 50, "font_size": 28, "color": "#111827", "align": "center", "z_index": 31, "token": "[[firma_1_nombre]]", "texto": getattr(firma1, 'nombre', '') or 'Nombre Firma 1', "image_url": "", "visible": True},
        "firma_1_cargo": {"key": "firma_1_cargo", "label": "Firma 1 Cargo", "type": "texto", "x": 860, "y": 1505, "width": 360, "height": 50, "font_size": 24, "color": "#374151", "align": "center", "z_index": 32, "token": "[[firma_1_cargo]]", "texto": getattr(firma1, 'rol', '') or 'Cargo Firma 1', "image_url": "", "visible": True},
        "firma_2_imagen": {"key": "firma_2_imagen", "label": "Firma 2 Imagen", "type": "imagen", "x": 2240, "y": 1320, "width": 280, "height": 120, "font_size": 20, "color": "#111827", "align": "center", "z_index": 33, "token": "[[firma_2_imagen]]", "texto": "", "image_url": _media_url(getattr(firma2, 'firma', None)), "visible": True},
        "firma_2_nombre": {"key": "firma_2_nombre", "label": "Firma 2 Nombre", "type": "texto", "x": 2200, "y": 1450, "width": 360, "height": 50, "font_size": 28, "color": "#111827", "align": "center", "z_index": 34, "token": "[[firma_2_nombre]]", "texto": getattr(firma2, 'nombre', '') or 'Nombre Firma 2', "image_url": "", "visible": True},
        "firma_2_cargo": {"key": "firma_2_cargo", "label": "Firma 2 Cargo", "type": "texto", "x": 2200, "y": 1505, "width": 360, "height": 50, "font_size": 24, "color": "#374151", "align": "center", "z_index": 35, "token": "[[firma_2_cargo]]", "texto": getattr(firma2, 'rol', '') or 'Cargo Firma 2', "image_url": "", "visible": True},
        "sello_medalla": {"key": "sello_medalla", "label": "Sello / Medalla", "type": "imagen", "x": 2600, "y": 980, "width": 220, "height": 220, "font_size": 20, "color": "#111827", "align": "center", "z_index": 36, "token": "[[sello_medalla]]", "texto": "", "image_url": "", "visible": True},
        "fondo_diploma": {"key": "fondo_diploma", "label": "Fondo diploma", "type": "imagen", "x": 0, "y": 0, "width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "font_size": 20, "color": "#111827", "align": "center", "z_index": 0, "token": "[[fondo_diploma]]", "texto": "", "image_url": _media_url(getattr(diseno, 'imagen_fondo', None)), "visible": False},
    }

    existing = diseno.estilos.get("elements") if isinstance(diseno.estilos, dict) and isinstance(diseno.estilos.get("elements"), dict) else {}
    for key, base_el in base.items():
        source = existing.get(key) if isinstance(existing.get(key), dict) else {}
        merged = {**base_el, **source}
        merged["x"] = _clamp_number(source.get("x", source.get("left", merged.get("x", 0))), merged.get("x", 0))
        merged["y"] = _clamp_number(source.get("y", source.get("top", merged.get("y", 0))), merged.get("y", 0))
        merged["width"] = _clamp_number(source.get("width", source.get("ancho", merged.get("width", 200))), merged.get("width", 200), min_value=20)
        merged["height"] = _clamp_number(source.get("height", source.get("alto", merged.get("height", 80))), merged.get("height", 80), min_value=20)
        merged["font_size"] = _clamp_number(source.get("font_size", source.get("fontSize", merged.get("font_size", 24))), merged.get("font_size", 24), min_value=1)
        merged["align"] = source.get("align", source.get("textAlign", source.get("alineacion", merged.get("align", "left"))))
        merged["z_index"] = int(_clamp_number(source.get("z_index", source.get("zIndex", merged.get("z_index", 1))), merged.get("z_index", 1), min_value=0))
        merged["token"] = source.get("token") or merged.get("token")
        merged["texto"] = source.get("texto", source.get("content", merged.get("texto", "")))
        merged["content"] = source.get("content", merged.get("content", merged.get("texto", "")))
        merged["image_url"] = source.get("image_url") or merged.get("image_url", "")
        merged["visible"] = bool(source.get("visible", merged.get("visible", True)))
        merged["key"] = key
        base[key] = merged

    return base


def modificar_diseno_visual(request, diseno_id):
    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
    elementos = _real_editor_elements(diseno)
    context = {
        "diseno": diseno,
        "elementos": elementos,
        "elementos_json": json.dumps(elementos),
        "canvas_width": CANVAS_WIDTH,
        "canvas_height": CANVAS_HEIGHT,
    }
    return render(request, "diplomas/editor_diseno_visual.html", context)


def guardar_diseno_visual(request, diseno_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    incoming = payload.get("elements") if isinstance(payload, dict) else None
    if not isinstance(incoming, dict):
        return JsonResponse({"error": "Estructura de elementos inválida"}, status=400)

    elementos = _build_diseno_elements(diseno, {})
    for key, value in incoming.items():
        if key not in elementos:
            continue
        elementos[key] = _normalize_element_defaults(key, value, elementos[key])

    diseno.estilos = {"elements": elementos}
    diseno.save(update_fields=["estilos", "actualizado_en"])
    return JsonResponse({"success": True})


def eliminar_diseno(request, diseno_id):
    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
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


def editar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    if request.method == "POST":
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            form.save()
            messages.success(request, "Curso actualizado correctamente.")
            return redirect("diplomas:cursos_lista")
    else:
        form = CursoForm(instance=curso)

    return render(request, "diplomas/editar_curso.html", {"form": form, "curso": curso})


def agregar_empleado_a_curso(request):
    if request.method == "POST":
        form = AgregarEmpleadoCursoForm(request.POST)
        if form.is_valid():
            curso = form.cleaned_data["curso"]
            empleado = form.cleaned_data["empleado"]

            if CursoEmpleado.objects.filter(curso=curso, empleado=empleado).exists():
                messages.warning(request, "Este empleado ya está asignado a este curso.")
                return redirect("agregar_empleado_curso")

            CursoEmpleado.objects.create(curso=curso, empleado=empleado)
            messages.success(request, "Empleado agregado correctamente al curso.")
            return redirect("agregar_empleado_curso")
    else:
        form = AgregarEmpleadoCursoForm()

    return render(request, "diplomas/agregar_empleado_curso.html", {"form": form})


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


def crear_curso_modal(request):
    if request.method == "POST":
        form = CursoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Curso creado correctamente.")
            return redirect("diplomas:cursos_lista")
        messages.error(request, "Corrige los errores del formulario.")
        return redirect("diplomas:cursos_lista")

    return redirect("diplomas:cursos_lista")


def cursos_lista(request):
    cursos = Curso.objects.all().order_by('-creado_en')
    form = CursoForm()
    return render(request, "diplomas/cursos_lista.html", {"cursos": cursos, "form": form})


def ver_diploma(request, curso_id, participante_id):
    curso_empleado = get_object_or_404(CursoEmpleado, id=participante_id, curso_id=curso_id)
    curso = curso_empleado.curso
    config = ConfiguracionGeneral.objects.first()

    elementos = _build_diseno_elements(curso.diseno_diploma, curso.posiciones or {})
    for _, data in elementos.items():
        if data.get("type") == "text":
            data["rendered_content"] = _resolve_content(data.get("content", ""), curso_empleado, config)
        else:
            data["rendered_content"] = data.get("content", "")

    fondo_url = curso.diseno_diploma.imagen_fondo.url if curso.diseno_diploma and curso.diseno_diploma.imagen_fondo else None

    context = {
        "curso": curso,
        "curso_empleado": curso_empleado,
        "config": config,
        "elementos": elementos,
        "fondo_url": fondo_url,
    }
    return render(request, "diplomas/ver_diploma.html", context)


@csrf_exempt
def guardar_posiciones(request, curso_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    curso = get_object_or_404(Curso, id=curso_id)

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
        elementos = _build_diseno_elements(curso.diseno_diploma, curso.posiciones)
        for key, values in posiciones_limpias.items():
            if key in elementos:
                elementos[key]["x"] = values["left"]
                elementos[key]["y"] = values["top"]
                elementos[key]["width"] = values["width"]
                elementos[key]["height"] = values["height"]
        curso.diseno_diploma.estilos = {"elements": elementos}
        curso.diseno_diploma.save(update_fields=["estilos", "actualizado_en"])
    else:
        curso.posiciones = posiciones_limpias
        curso.save(update_fields=["posiciones"])

    return JsonResponse({"success": True})


def detalle_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    participantes = CursoEmpleado.objects.filter(curso=curso).select_related("empleado")
    total_participantes = participantes.count()

    return render(request, "diplomas/detalle_curso.html", {
        "curso": curso,
        "participantes": participantes,
        "total_participantes": total_participantes
    })


def agregar_empleado_detalle(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
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
