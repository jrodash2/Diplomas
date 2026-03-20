from copy import deepcopy

from django.utils import timezone

from empleados_app.models import ConfiguracionGeneral

from .models import Firma


CANVAS_WIDTH = 3508
CANVAS_HEIGHT = 2480
DESIGN_VERSION = 2

LEGACY_ELEMENT_KEY_MAP = {
    "logo1": "logo_gobierno",
    "logo2": "logo_upcv",
    "institucion": "titulo_institucional",
    "titulo": "subtitulo_diploma",
    "nombre": "participante_nombre",
    "curso": "nombre_curso",
    "fecha": "fecha_texto",
}


def media_url(file_field):
    try:
        return file_field.url if file_field else ""
    except Exception:
        return ""


def clamp_number(value, default, min_value=0, max_value=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)
    if number < min_value:
        number = float(default)
    if max_value is not None:
        number = min(number, max_value)
    return number


def _base_element(
    *,
    key,
    label,
    element_type,
    x,
    y,
    width,
    height,
    z_index,
    token="",
    texto="",
    image_url="",
    font_size=24,
    color="#111827",
    align="center",
    visible=True,
):
    return {
        "key": key,
        "label": label,
        "type": element_type,
        "visible": visible,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "font_size": font_size,
        "color": color,
        "align": align,
        "z_index": z_index,
        "token": token,
        "texto": texto,
        "image_url": image_url,
    }


def get_signature_pair(curso=None):
    if curso is not None:
        curso_firmas = list(curso.firmas.all().order_by("id")[:2])
        if curso_firmas:
            return curso_firmas
    return list(Firma.objects.order_by("id")[:2])


def build_base_elements(diseno=None, firmas=None):
    config = ConfiguracionGeneral.objects.first()
    firmas = firmas if firmas is not None else get_signature_pair()
    firma_1 = firmas[0] if len(firmas) > 0 else None
    firma_2 = firmas[1] if len(firmas) > 1 else None

    return {
        "fondo_diploma": _base_element(
            key="fondo_diploma",
            label="Fondo diploma",
            element_type="imagen",
            x=0,
            y=0,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            z_index=0,
            token="{{ fondo_diploma }}",
            image_url=media_url(getattr(diseno, "imagen_fondo", None)),
            visible=True,
        ),
        "logo_gobierno": _base_element(
            key="logo_gobierno",
            label="Logo Gobierno",
            element_type="imagen",
            x=1180,
            y=70,
            width=210,
            height=210,
            z_index=10,
            token="{{ logo_gobierno }}",
            image_url=media_url(getattr(config, "logotipo2", None)),
        ),
        "logo_upcv": _base_element(
            key="logo_upcv",
            label="Logo UPCV",
            element_type="imagen",
            x=1690,
            y=70,
            width=210,
            height=210,
            z_index=11,
            token="{{ logo_upcv }}",
            image_url=media_url(getattr(config, "logotipo", None)),
        ),
        "titulo_institucional": _base_element(
            key="titulo_institucional",
            label="Título institucional",
            element_type="texto",
            x=800,
            y=290,
            width=1908,
            height=120,
            z_index=20,
            token="{{ institucion_nombre }}",
            texto=getattr(config, "nombre_institucion", "") or "Unidad para la Prevención Comunitaria de la Violencia",
            font_size=54,
        ),
        "subtitulo_diploma": _base_element(
            key="subtitulo_diploma",
            label="Subtítulo diploma",
            element_type="texto",
            x=980,
            y=470,
            width=1548,
            height=80,
            z_index=21,
            token="{{ subtitulo_diploma }}",
            texto="OTORGA EL PRESENTE DIPLOMA A:",
            font_size=48,
        ),
        "adorno_central": _base_element(
            key="adorno_central",
            label="Adorno central",
            element_type="decorativo",
            x=1130,
            y=560,
            width=1248,
            height=60,
            z_index=22,
            token="{{ adorno_central }}",
            texto="──────────── ✦ ────────────",
            font_size=36,
            color="#6b7280",
        ),
        "participante_nombre": _base_element(
            key="participante_nombre",
            label="Nombre participante",
            element_type="texto",
            x=700,
            y=660,
            width=2108,
            height=170,
            z_index=23,
            token="{{ participante_nombre }}",
            texto="{{ participante_nombre }}",
            font_size=104,
        ),
        "codigo": _base_element(
            key="codigo",
            label="Código",
            element_type="texto",
            x=2220,
            y=860,
            width=780,
            height=60,
            z_index=24,
            token="{{ codigo }}",
            texto="Código: {{ codigo }}",
            font_size=30,
            align="left",
        ),
        "nombre_curso": _base_element(
            key="nombre_curso",
            label="Nombre del curso",
            element_type="texto",
            x=760,
            y=900,
            width=1988,
            height=130,
            z_index=25,
            token="{{ curso_nombre }}",
            texto="{{ curso_nombre }}",
            font_size=52,
        ),
        "fecha_texto": _base_element(
            key="fecha_texto",
            label="Fecha",
            element_type="texto",
            x=980,
            y=1080,
            width=1548,
            height=70,
            z_index=26,
            token="{{ fecha }}",
            texto="Guatemala, {{ fecha }} © UPCV",
            font_size=32,
        ),
        "firma_1_imagen": _base_element(
            key="firma_1_imagen",
            label="Firma 1",
            element_type="imagen",
            x=760,
            y=1550,
            width=420,
            height=150,
            z_index=30,
            token="{{ firma_1_imagen }}",
            image_url=media_url(getattr(firma_1, "firma", None)),
        ),
        "firma_1_nombre": _base_element(
            key="firma_1_nombre",
            label="Nombre firma 1",
            element_type="texto",
            x=670,
            y=1700,
            width=600,
            height=50,
            z_index=31,
            token="{{ firma_1_nombre }}",
            texto=getattr(firma_1, "nombre", "") or "{{ firma_1_nombre }}",
            font_size=28,
        ),
        "firma_1_cargo": _base_element(
            key="firma_1_cargo",
            label="Cargo firma 1",
            element_type="texto",
            x=620,
            y=1760,
            width=700,
            height=50,
            z_index=32,
            token="{{ firma_1_cargo }}",
            texto=getattr(firma_1, "rol", "") or "{{ firma_1_cargo }}",
            font_size=24,
            color="#374151",
        ),
        "firma_2_imagen": _base_element(
            key="firma_2_imagen",
            label="Firma 2",
            element_type="imagen",
            x=2328,
            y=1550,
            width=420,
            height=150,
            z_index=33,
            token="{{ firma_2_imagen }}",
            image_url=media_url(getattr(firma_2, "firma", None)),
        ),
        "firma_2_nombre": _base_element(
            key="firma_2_nombre",
            label="Nombre firma 2",
            element_type="texto",
            x=2238,
            y=1700,
            width=600,
            height=50,
            z_index=34,
            token="{{ firma_2_nombre }}",
            texto=getattr(firma_2, "nombre", "") or "{{ firma_2_nombre }}",
            font_size=28,
        ),
        "firma_2_cargo": _base_element(
            key="firma_2_cargo",
            label="Cargo firma 2",
            element_type="texto",
            x=2188,
            y=1760,
            width=700,
            height=50,
            z_index=35,
            token="{{ firma_2_cargo }}",
            texto=getattr(firma_2, "rol", "") or "{{ firma_2_cargo }}",
            font_size=24,
            color="#374151",
        ),
        "sello_medalla": _base_element(
            key="sello_medalla",
            label="Sello / Medalla",
            element_type="imagen",
            x=2670,
            y=1170,
            width=240,
            height=240,
            z_index=36,
            token="{{ sello_medalla }}",
            image_url="",
        ),
    }


def normalize_element(key, raw_element, fallback_element):
    fallback = deepcopy(fallback_element)
    raw = raw_element if isinstance(raw_element, dict) else {}

    width = clamp_number(raw.get("width", raw.get("ancho")), fallback["width"], min_value=20, max_value=CANVAS_WIDTH)
    height = clamp_number(raw.get("height", raw.get("alto")), fallback["height"], min_value=20, max_value=CANVAS_HEIGHT)
    max_x = max(CANVAS_WIDTH - width, 0)
    max_y = max(CANVAS_HEIGHT - height, 0)

    normalized = {
        "key": key,
        "label": raw.get("label") or fallback["label"],
        "type": raw.get("type") or fallback["type"],
        "visible": bool(raw.get("visible", fallback["visible"])),
        "x": clamp_number(raw.get("x", raw.get("left")), fallback["x"], min_value=0, max_value=max_x),
        "y": clamp_number(raw.get("y", raw.get("top")), fallback["y"], min_value=0, max_value=max_y),
        "width": width,
        "height": height,
        "font_size": clamp_number(raw.get("font_size", raw.get("fontSize")), fallback["font_size"], min_value=8, max_value=300),
        "color": raw.get("color") or fallback["color"],
        "align": raw.get("align") or raw.get("textAlign") or raw.get("alineacion") or fallback["align"],
        "z_index": int(clamp_number(raw.get("z_index", raw.get("zIndex")), fallback["z_index"], min_value=0, max_value=9999)),
        "token": raw.get("token") or fallback["token"],
        "texto": raw.get("texto") or raw.get("content") or fallback["texto"],
        "image_url": raw.get("image_url") or fallback["image_url"],
    }
    return normalized


def _normalize_elements_map(raw_map, base_elements):
    normalized = {key: normalize_element(key, {}, fallback) for key, fallback in base_elements.items()}
    if not isinstance(raw_map, dict):
        return normalized

    for raw_key, raw_value in raw_map.items():
        key = LEGACY_ELEMENT_KEY_MAP.get(raw_key, raw_key)
        if key not in normalized:
            continue
        normalized[key] = normalize_element(key, raw_value, normalized[key])

    normalized["fondo_diploma"]["x"] = 0
    normalized["fondo_diploma"]["y"] = 0
    normalized["fondo_diploma"]["width"] = CANVAS_WIDTH
    normalized["fondo_diploma"]["height"] = CANVAS_HEIGHT
    return normalized


def build_design_definition(diseno, legacy_positions=None, firmas=None):
    base_elements = build_base_elements(diseno, firmas=firmas)
    current_payload = diseno.estilos if diseno and isinstance(diseno.estilos, dict) else {}

    raw_elements = {}
    if isinstance(current_payload.get("elements"), dict):
        raw_elements.update(current_payload["elements"])
    elif current_payload and "elements" not in current_payload:
        raw_elements.update(current_payload)

    if isinstance(legacy_positions, dict):
        raw_elements = {**legacy_positions, **raw_elements}

    return {
        "version": DESIGN_VERSION,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "elements": _normalize_elements_map(raw_elements, base_elements),
    }


def normalize_definition_from_elements(diseno, raw_elements, firmas=None):
    definition = build_design_definition(diseno, None, firmas=firmas)
    definition["elements"] = _normalize_elements_map(raw_elements, build_base_elements(diseno, firmas=firmas))
    return definition


def ensure_design_definition(diseno, firmas=None):
    definition = build_design_definition(diseno, None, firmas=firmas)
    if diseno and diseno.estilos != definition:
        diseno.estilos = definition
        diseno.save(update_fields=["estilos", "actualizado_en"])
    return definition


def resolve_text(text_value, context_map):
    resolved = text_value or ""
    for token, replacement in context_map.items():
        resolved = resolved.replace(token, replacement)
    return resolved


def build_course_design_definition(curso, firmas=None):
    firmas = firmas if firmas is not None else get_signature_pair(curso)
    if curso.diseno_diploma_id:
        return build_design_definition(curso.diseno_diploma, None, firmas=firmas)
    return {
        "version": DESIGN_VERSION,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "elements": _normalize_elements_map(curso.posiciones or {}, build_base_elements(None, firmas=firmas)),
    }


def build_render_elements(definition, context_map):
    render_elements = []
    for element in sorted(definition["elements"].values(), key=lambda item: item["z_index"]):
        item = deepcopy(element)
        if item["type"] in {"texto", "decorativo"}:
            item["rendered_value"] = resolve_text(item["texto"], context_map)
        else:
            item["rendered_value"] = ""
        render_elements.append(item)
    return render_elements


def build_diploma_render_context(curso_empleado):
    curso = curso_empleado.curso
    empleado = curso_empleado.empleado
    config = ConfiguracionGeneral.objects.first()
    firmas = get_signature_pair(curso)
    firma_1 = firmas[0] if len(firmas) > 0 else None
    firma_2 = firmas[1] if len(firmas) > 1 else None
    definition = build_course_design_definition(curso, firmas=firmas)

    context_map = {
        "{{ participante_nombre }}": f"{empleado.nombres} {empleado.apellidos}",
        "{{ curso_nombre }}": curso.nombre,
        "{{ codigo }}": f"{curso_empleado.id:04d}-UPCV",
        "{{ fecha }}": timezone.now().strftime("%Y"),
        "{{ institucion_nombre }}": config.nombre_institucion if config else "",
        "{{ subtitulo_diploma }}": "OTORGA EL PRESENTE DIPLOMA A:",
        "{{ adorno_central }}": "──────────── ✦ ────────────",
        "{{ firma_1_nombre }}": getattr(firma_1, "nombre", "") if firma_1 else "",
        "{{ firma_1_cargo }}": getattr(firma_1, "rol", "") if firma_1 else "",
        "{{ firma_2_nombre }}": getattr(firma_2, "nombre", "") if firma_2 else "",
        "{{ firma_2_cargo }}": getattr(firma_2, "rol", "") if firma_2 else "",
        "{{ logo_gobierno }}": "",
        "{{ logo_upcv }}": "",
        "{{ sello_medalla }}": "",
        "{{ fondo_diploma }}": "",
    }

    render_elements = build_render_elements(definition, context_map)

    return {
        "curso": curso,
        "curso_empleado": curso_empleado,
        "config": config,
        "design_definition": definition,
        "render_elements": render_elements,
        "fondo_url": definition["elements"]["fondo_diploma"]["image_url"],
    }
