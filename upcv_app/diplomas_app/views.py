import json

from django.contrib import messages
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from empleados_app.models import Empleado

from .design_engine import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    build_design_definition,
    build_diploma_render_context,
    ensure_design_definition,
    normalize_definition_from_elements,
)
from .forms import AgregarEmpleadoCursoForm, CursoForm, DisenoDiplomaForm, FirmaForm
from .models import Curso, CursoEmpleado, DisenoDiploma, Firma


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
            diseno = form.save()
            ensure_design_definition(diseno)
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



@ensure_csrf_cookie
def modificar_diseno_visual(request, diseno_id):
    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
    definition = ensure_design_definition(diseno)
    editor_elements = sorted(definition["elements"].values(), key=lambda item: item["z_index"])
    context = {
        "diseno": diseno,
        "design_definition": definition,
        "design_definition_json": json.dumps(definition),
        "editor_elements": editor_elements,
        "editor_background_url": definition["elements"]["fondo_diploma"]["image_url"],
        "canvas_width": CANVAS_WIDTH,
        "canvas_height": CANVAS_HEIGHT,
    }
    return render(request, "diplomas/editor_diseno_visual.html", context)


def guardar_diseno_visual(request, diseno_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    diseno = get_object_or_404(DisenoDiploma, id=diseno_id)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

    incoming_elements = None
    if isinstance(payload, dict):
        if isinstance(payload.get("elements"), dict):
            incoming_elements = payload.get("elements")
        elif isinstance(payload.get("definition"), dict) and isinstance(payload["definition"].get("elements"), dict):
            incoming_elements = payload["definition"]["elements"]
    if not isinstance(incoming_elements, dict):
        return JsonResponse({"success": False, "error": "Estructura de elementos inválida"}, status=400)

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
        "definition": diseno.estilos,
    })


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
    context = build_diploma_render_context(curso_empleado)
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
        current_definition = build_design_definition(curso.diseno_diploma, None)
        for key, values in posiciones_limpias.items():
            if key not in current_definition["elements"]:
                continue
            current_definition["elements"][key]["x"] = values["left"]
            current_definition["elements"][key]["y"] = values["top"]
            current_definition["elements"][key]["width"] = values["width"]
            current_definition["elements"][key]["height"] = values["height"]
        curso.diseno_diploma.estilos = current_definition
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
