from copy import deepcopy
from html import escape
import re
import string

from django.utils import timezone

from empleados_app.models import ConfiguracionGeneral

from .models import Diploma, Firma


CANVAS_WIDTH = 3508
CANVAS_HEIGHT = 2480
DESIGN_VERSION = 2
DEFAULT_FONT_FAMILY = 'Georgia, "Times New Roman", serif'
DEFAULT_FONT_WEIGHT = "400"

LEGACY_ELEMENT_KEY_MAP = {
    "logo1": "logo_gobierno",
    "logo_1": "logo_gobierno",
    "logo2": "logo_upcv",
    "logo_2": "logo_upcv",
    "institucion": "titulo_institucional",
    "titulo": "subtitulo_diploma",
    "nombre": "participante_nombre",
    "nombre_participante": "participante_nombre",
    "participant_name": "participante_nombre",
    "curso": "nombre_curso",
    "curso_nombre": "nombre_curso",
    "course_name": "nombre_curso",
    "fecha": "fecha_texto",
}

LEGACY_ELEMENT_TYPE_MAP = {
    "text": "texto",
    "texto": "texto",
    "image": "imagen",
    "imagen": "imagen",
    "img": "imagen",
    "logo": "imagen",
    "decorative": "decorativo",
    "decorativo": "decorativo",
    "decoration": "decorativo",
}


def media_url(file_field, version=None):
    try:
        if not file_field:
            return ""
        url = file_field.url
        if version is None:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={version}"
    except Exception:
        return ""


def design_background_url(diseno):
    if not diseno:
        return ""
    version = None
    updated_at = getattr(diseno, "actualizado_en", None)
    if updated_at is not None:
        version = int(updated_at.timestamp())
    return media_url(getattr(diseno, "imagen_fondo", None), version=version)


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


def format_participant_name(value):
    cleaned = " ".join(str(value or "").split())
    return string.capwords(cleaned.lower())


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
    font_family=DEFAULT_FONT_FAMILY,
    font_weight=DEFAULT_FONT_WEIGHT,
    color="#111827",
    align="center",
    visible=True,
    shape="rect",
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
        "font_family": font_family,
        "font_weight": str(font_weight),
        "color": color,
        "align": align,
        "z_index": z_index,
        "token": token,
        "texto": texto,
        "image_url": image_url,
        "shape": shape,
    }


def build_custom_element_fallback(key, raw_element):
    raw = raw_element if isinstance(raw_element, dict) else {}
    element_type = canonical_element_type(raw.get("type"), "texto")
    default_label = raw.get("label") or key.replace("_", " ").strip().title() or "Elemento personalizado"
    default_width = 360 if element_type == "imagen" else 720
    default_height = 220 if element_type == "imagen" else 140
    default_text = "Nuevo texto" if element_type != "imagen" else ""
    default_image = raw.get("image_url") or ""
    return _base_element(
        key=key,
        label=default_label,
        element_type=element_type,
        x=clamp_number(raw.get("x"), 120, min_value=0, max_value=CANVAS_WIDTH),
        y=clamp_number(raw.get("y"), 120, min_value=0, max_value=CANVAS_HEIGHT),
        width=clamp_number(raw.get("width"), default_width, min_value=20, max_value=CANVAS_WIDTH),
        height=clamp_number(raw.get("height"), default_height, min_value=20, max_value=CANVAS_HEIGHT),
        z_index=int(clamp_number(raw.get("z_index", raw.get("zIndex")), 90, min_value=0, max_value=9999)),
        token=raw.get("token") or "",
        texto=raw.get("texto") or raw.get("content") or default_text,
        image_url=default_image,
        font_size=clamp_number(raw.get("font_size", raw.get("fontSize")), 34, min_value=8, max_value=300),
        font_family=raw.get("font_family") or raw.get("fontFamily") or DEFAULT_FONT_FAMILY,
        font_weight=str(raw.get("font_weight") or raw.get("fontWeight") or "400"),
        color=raw.get("color") or "#111827",
        align=raw.get("align") or "center",
        visible=bool(raw.get("visible", True)),
        shape=raw.get("shape") or "rect",
    )

SIGNATURE_KEY_PATTERN = re.compile(r"^firma_(\d+)_(imagen|nombre|cargo)$")
BOLD_MARKUP_PATTERN = re.compile(r"(\*\*|__)(.+?)\1")
UNRESOLVED_TOKEN_PATTERN = re.compile(r"\{\{\s*[^{}]+\s*\}\}")

DYNAMIC_TEXT_KEYS = {
    "titulo_institucional",
    "participante_nombre",
    "codigo",
    "nombre_curso",
    "descripcion_curso",
    "fecha_texto",
}

DYNAMIC_IMAGE_KEYS = {
    "logo_gobierno",
    "logo_upcv",
    "foto_participante",
}


def _signature_indexes_from_elements(raw_map):
    indexes = set()
    if not isinstance(raw_map, dict):
        return indexes

    for raw_key in raw_map.keys():
        match = SIGNATURE_KEY_PATTERN.match(str(raw_key))
        if match:
            indexes.add(int(match.group(1)))
    return indexes


def _signature_slot_count(firmas=None, minimum=0):
    return max(len(firmas or []), minimum)


def is_signature_key(key):
    return bool(SIGNATURE_KEY_PATTERN.match(str(key)))


def is_dynamic_text_key(key):
    return key in DYNAMIC_TEXT_KEYS or bool(re.match(r"^firma_\d+_(nombre|cargo)$", str(key)))


def is_dynamic_image_key(key):
    return key in DYNAMIC_IMAGE_KEYS or bool(re.match(r"^firma_\d+_imagen$", str(key)))


def get_course_signatures(curso=None):
    if curso is not None:
        curso_firmas = list(curso.firmas.all().order_by("id"))
        if curso_firmas:
            return curso_firmas
    return list(Firma.objects.order_by("id")[:2])


def get_design_signatures(diseno=None):
    if diseno is not None and hasattr(diseno, "cursos"):
        firma_ids = []
        seen = set()
        cursos = diseno.cursos.prefetch_related("firmas").all().order_by("id")
        for curso in cursos:
            for firma in curso.firmas.all().order_by("id"):
                if firma.id in seen:
                    continue
                seen.add(firma.id)
                firma_ids.append(firma.id)
        if firma_ids:
            firmas_by_id = Firma.objects.in_bulk(firma_ids)
            return [firmas_by_id[firma_id] for firma_id in firma_ids if firma_id in firmas_by_id]
    return get_course_signatures()


def _build_signature_layout(index, total):
    if total <= 1:
        base_x_positions = [1544]
        x = base_x_positions[0]
        image_y = 1550
    elif total == 2:
        base_x_positions = [760, 2328]
        x = base_x_positions[index]
        image_y = 1550
    else:
        max_columns = 3
        row_gap = 280
        image_width = 420
        side_margin = 280
        row = index // max_columns
        position_in_row = index % max_columns
        row_count = min(max_columns, total - (row * max_columns))
        usable_width = CANVAS_WIDTH - (side_margin * 2) - image_width
        gap = usable_width / max(row_count - 1, 1)
        x = side_margin + (gap * position_in_row if row_count > 1 else usable_width / 2)
        image_y = 1420 + (row * row_gap)

    return {
        "image_x": round(x),
        "image_y": image_y,
        "name_x": round(max(x - 90, 0)),
        "name_y": image_y + 150,
        "cargo_x": round(max(x - 140, 0)),
        "cargo_y": image_y + 210,
    }


def build_signature_elements(firmas, signature_slots):
    elements = {}
    total = max(signature_slots, 1)

    for index in range(signature_slots):
        signature_number = index + 1
        firma = firmas[index] if index < len(firmas) else None
        layout = _build_signature_layout(index, total)
        elements[f"firma_{signature_number}_imagen"] = _base_element(
            key=f"firma_{signature_number}_imagen",
            label=f"Firma {signature_number}",
            element_type="imagen",
            x=layout["image_x"],
            y=layout["image_y"],
            width=420,
            height=150,
            z_index=30 + (index * 3),
            token=f"{{{{ firma_{signature_number}_imagen }}}}",
            image_url=media_url(getattr(firma, "firma", None)),
            visible=True,
        )
        elements[f"firma_{signature_number}_nombre"] = _base_element(
            key=f"firma_{signature_number}_nombre",
            label=f"Nombre firma {signature_number}",
            element_type="texto",
            x=layout["name_x"],
            y=layout["name_y"],
            width=600,
            height=50,
            z_index=31 + (index * 3),
            token=f"{{{{ firma_{signature_number}_nombre }}}}",
            texto=getattr(firma, "nombre", "") or f"{{{{ firma_{signature_number}_nombre }}}}",
            font_size=28,
            visible=True,
        )
        elements[f"firma_{signature_number}_cargo"] = _base_element(
            key=f"firma_{signature_number}_cargo",
            label=f"Cargo firma {signature_number}",
            element_type="texto",
            x=layout["cargo_x"],
            y=layout["cargo_y"],
            width=700,
            height=50,
            z_index=32 + (index * 3),
            token=f"{{{{ firma_{signature_number}_cargo }}}}",
            texto=getattr(firma, "rol", "") or f"{{{{ firma_{signature_number}_cargo }}}}",
            font_size=24,
            color="#374151",
            visible=True,
        )
    return elements


def build_base_elements(diseno=None, firmas=None, signature_slots=2):
    config = ConfiguracionGeneral.objects.first()
    firmas = firmas if firmas is not None else get_design_signatures(diseno)

    base_elements = {
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
            image_url=design_background_url(diseno),
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
            font_weight="700",
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
            font_weight="700",
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
            font_family='"Palatino Linotype", "Book Antiqua", Palatino, serif',
            font_weight="700",
        ),
        "foto_participante": _base_element(
            key="foto_participante",
            label="Fotografía participante",
            element_type="imagen",
            x=360,
            y=640,
            width=360,
            height=360,
            z_index=24,
            token="{{ foto_participante }}",
            image_url="{{ foto_participante }}",
            visible=True,
            shape="circle",
        ),
        "codigo": _base_element(
            key="codigo",
            label="Código",
            element_type="texto",
            x=2220,
            y=860,
            width=780,
            height=60,
            z_index=25,
            token="{{ codigo }}",
            texto="Código: {{ codigo }}",
            font_size=30,
            align="left",
            font_family='Arial, "Helvetica Neue", Helvetica, sans-serif',
        ),
        "nombre_curso": _base_element(
            key="nombre_curso",
            label="Nombre del curso",
            element_type="texto",
            x=760,
            y=900,
            width=1988,
            height=130,
            z_index=26,
            token="{{ curso_nombre }}",
            texto="{{ curso_nombre }}",
            font_size=52,
            font_weight="700",
        ),
        "descripcion_curso": _base_element(
            key="descripcion_curso",
            label="Descripción del curso",
            element_type="texto",
            x=760,
            y=1045,
            width=1988,
            height=150,
            z_index=27,
            token="{{ descripcion_curso }}",
            texto="{{ descripcion_curso }}",
            font_size=28,
            color="#374151",
            align="center",
        ),
        "fecha_texto": _base_element(
            key="fecha_texto",
            label="Fecha",
            element_type="texto",
            x=980,
            y=1080,
            width=1548,
            height=70,
            z_index=28,
            token="{{ fecha }}",
            texto="Guatemala, {{ fecha }} © UPCV",
            font_size=32,
            font_family='Arial, "Helvetica Neue", Helvetica, sans-serif',
        ),
    }
    base_elements.update(build_signature_elements(firmas, signature_slots))
    return base_elements




def canonical_element_type(raw_type, fallback_type):
    candidate = str(raw_type or fallback_type or "texto").strip().lower()
    return LEGACY_ELEMENT_TYPE_MAP.get(candidate, fallback_type or "texto")

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
        "type": canonical_element_type(raw.get("type"), fallback["type"]),
        "visible": bool(raw.get("visible", fallback["visible"])),
        "x": clamp_number(raw.get("x", raw.get("left")), fallback["x"], min_value=0, max_value=max_x),
        "y": clamp_number(raw.get("y", raw.get("top")), fallback["y"], min_value=0, max_value=max_y),
        "width": width,
        "height": height,
        "font_size": clamp_number(raw.get("font_size", raw.get("fontSize")), fallback["font_size"], min_value=8, max_value=300),
        "font_family": raw.get("font_family") or raw.get("fontFamily") or fallback.get("font_family", DEFAULT_FONT_FAMILY),
        "font_weight": str(raw.get("font_weight") or raw.get("fontWeight") or ("700" if raw.get("bold") else fallback.get("font_weight", DEFAULT_FONT_WEIGHT))),
        "color": raw.get("color") or fallback["color"],
        "align": raw.get("align") or raw.get("textAlign") or raw.get("alineacion") or fallback["align"],
        "z_index": int(clamp_number(raw.get("z_index", raw.get("zIndex")), fallback["z_index"], min_value=0, max_value=9999)),
        "token": raw.get("token") or fallback["token"],
        "texto": raw.get("texto") or raw.get("content") or fallback["texto"],
        "image_url": raw.get("image_url") or fallback["image_url"],
        "shape": raw.get("shape") or fallback.get("shape", "rect"),
    }
    if is_dynamic_text_key(key):
        normalized["texto"] = fallback["texto"]
        normalized["token"] = fallback["token"]
    if is_dynamic_image_key(key):
        normalized["image_url"] = fallback["image_url"]
        normalized["token"] = fallback["token"]
    return normalized


def _normalize_elements_map(raw_map, base_elements):
    normalized = {key: normalize_element(key, {}, fallback) for key, fallback in base_elements.items()}
    if not isinstance(raw_map, dict):
        return normalized

    for raw_key, raw_value in raw_map.items():
        key = LEGACY_ELEMENT_KEY_MAP.get(raw_key, raw_key)
        if is_signature_key(key) and key not in base_elements:
            continue
        if key not in normalized:
            normalized[key] = build_custom_element_fallback(key, raw_value)
        normalized[key] = normalize_element(key, raw_value, normalized[key])

    normalized["fondo_diploma"]["x"] = 0
    normalized["fondo_diploma"]["y"] = 0
    normalized["fondo_diploma"]["width"] = CANVAS_WIDTH
    normalized["fondo_diploma"]["height"] = CANVAS_HEIGHT
    normalized["fondo_diploma"]["image_url"] = base_elements["fondo_diploma"]["image_url"]
    return normalized


def build_design_definition(diseno, legacy_positions=None, firmas=None):
    current_payload = diseno.estilos if diseno and isinstance(diseno.estilos, dict) else {}

    raw_elements = {}
    if isinstance(current_payload.get("elements"), dict):
        raw_elements.update(current_payload["elements"])
    elif current_payload and "elements" not in current_payload:
        raw_elements.update(current_payload)

    if isinstance(legacy_positions, dict):
        raw_elements = {**legacy_positions, **raw_elements}

    firmas = firmas if firmas is not None else get_design_signatures(diseno)
    signature_slots = _signature_slot_count(firmas)
    base_elements = build_base_elements(diseno, firmas=firmas, signature_slots=signature_slots)

    return {
        "version": DESIGN_VERSION,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "elements": _normalize_elements_map(raw_elements, base_elements),
    }


def normalize_definition_from_elements(diseno, raw_elements, firmas=None):
    firmas = firmas if firmas is not None else get_design_signatures(diseno)
    signature_slots = _signature_slot_count(firmas)
    definition = build_design_definition(diseno, None, firmas=firmas)
    definition["elements"] = _normalize_elements_map(
        raw_elements,
        build_base_elements(diseno, firmas=firmas, signature_slots=signature_slots),
    )
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


def resolve_image_url(image_value, context_map):
    resolved = image_value or ""
    for token, replacement in context_map.items():
        resolved = resolved.replace(token, replacement)
    return resolved


def is_unresolved_token(value):
    return bool(UNRESOLVED_TOKEN_PATTERN.fullmatch(str(value or "").strip()))


def render_safe_inline_bold(text_value):
    escaped = escape(text_value or "")

    def replace(match):
        content = match.group(2)
        return f"<strong>{content}</strong>"

    return BOLD_MARKUP_PATTERN.sub(replace, escaped)


def render_text_content(element_key, resolved_text):
    if element_key == "descripcion_curso":
        return {
            "rendered_value": resolved_text,
            "rendered_html": render_safe_inline_bold(resolved_text),
            "render_as_html": True,
        }
    return {
        "rendered_value": resolved_text,
        "rendered_html": escape(resolved_text or ""),
        "render_as_html": False,
    }




def build_token_context_map(*, curso=None, curso_empleado=None, config=None, firmas=None, sample=False):
    config = config if config is not None else ConfiguracionGeneral.objects.first()
    firmas = firmas if firmas is not None else get_course_signatures(curso)

    participante_nombre = "NOMBRE DEL PARTICIPANTE"
    curso_nombre = getattr(curso, "nombre", "NOMBRE DEL CURSO") or "NOMBRE DEL CURSO"
    descripcion_curso = getattr(curso, "descripcion", "") or ("Descripción del curso" if sample else "")
    sample_location = getattr(curso, "ubicacion", None)
    sample_location_code = getattr(sample_location, "abreviatura", "") if sample_location else "GRAL"
    codigo = f"UPCV-{sample_location_code or 'GRAL'}-0001-{timezone.now().year}"
    if curso_empleado is not None:
        raw_name = getattr(curso_empleado, "nombre_participante", "") or ""
        participante_nombre = format_participant_name(raw_name)
        curso_nombre = curso_empleado.curso.nombre
        descripcion_curso = curso_empleado.curso.descripcion or ""
        try:
            diploma = curso_empleado.diploma
        except Diploma.DoesNotExist:
            diploma = None
        if diploma and diploma.numero_diploma:
            codigo = diploma.numero_diploma
        else:
            codigo = Diploma.build_numero_diploma(curso_empleado)
    participante_foto = ""
    if curso_empleado is not None:
        participante_foto = getattr(curso_empleado, "foto_participante_url", "") or ""

    context = {
        "{{ participante_nombre }}": participante_nombre,
        "{{ foto_participante }}": participante_foto,
        "{{ curso_nombre }}": curso_nombre,
        "{{ descripcion_curso }}": descripcion_curso,
        "{{ codigo }}": codigo,
        "{{ fecha }}": timezone.now().strftime("%Y"),
        "{{ institucion_nombre }}": config.nombre_institucion if config else "",
        "{{ subtitulo_diploma }}": "OTORGA EL PRESENTE DIPLOMA A:",
        "{{ adorno_central }}": "──────────── ✦ ────────────",
        "{{ logo_gobierno }}": "",
        "{{ logo_upcv }}": "",
        "{{ fondo_diploma }}": "",
    }
    for index, firma in enumerate(firmas, start=1):
        context[f"{{{{ firma_{index}_nombre }}}}"] = getattr(firma, "nombre", "") or ""
        context[f"{{{{ firma_{index}_cargo }}}}"] = getattr(firma, "rol", "") or ""
        context[f"{{{{ firma_{index}_imagen }}}}"] = media_url(getattr(firma, "firma", None))
    return context


def build_design_editor_payload(diseno, firmas=None):
    firmas = firmas if firmas is not None else get_design_signatures(diseno)
    definition = build_design_definition(diseno, None, firmas=firmas)
    preview_context = build_token_context_map(config=ConfiguracionGeneral.objects.first(), firmas=firmas, sample=True)
    return {
        "definition": definition,
        "preview_context": preview_context,
    }

def build_course_design_definition(curso, firmas=None):
    firmas = firmas if firmas is not None else get_course_signatures(curso)
    if curso.diseno_diploma_id:
        return build_design_definition(curso.diseno_diploma, None, firmas=firmas)
    signature_slots = _signature_slot_count(firmas)
    return {
        "version": DESIGN_VERSION,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "elements": _normalize_elements_map(
            curso.posiciones or {},
            build_base_elements(None, firmas=firmas, signature_slots=signature_slots),
        ),
    }


def build_render_elements(definition, context_map):
    render_elements = []
    for element in sorted(definition["elements"].values(), key=lambda item: item["z_index"]):
        item = deepcopy(element)
        if item["type"] in {"texto", "decorativo"}:
            resolved_text = resolve_text(item["texto"], context_map)
            rendered = render_text_content(item["key"], resolved_text)
            item["rendered_value"] = rendered["rendered_value"]
            item["rendered_html"] = rendered["rendered_html"]
            item["render_as_html"] = rendered["render_as_html"]
        else:
            item["rendered_value"] = ""
            item["rendered_html"] = ""
            item["render_as_html"] = False
            item["image_url"] = resolve_image_url(item.get("image_url"), context_map)
        if SIGNATURE_KEY_PATTERN.match(item["key"]):
            if item["type"] == "imagen" and (
                not item.get("image_url") or is_unresolved_token(item.get("image_url"))
            ):
                item["visible"] = False
            elif item["type"] != "imagen" and (
                not item["rendered_value"].strip() or is_unresolved_token(item["rendered_value"])
            ):
                item["visible"] = False
        if item["key"] == "foto_participante" and not item.get("image_url"):
            item["visible"] = False
        if item["key"] == "descripcion_curso" and not item["rendered_value"].strip():
            item["visible"] = False
        render_elements.append(item)
    return render_elements


def build_diploma_render_context(curso_empleado):
    Diploma.ensure_for_course_employee(curso_empleado)
    curso_empleado = type(curso_empleado).objects.select_related(
        "curso",
        "curso__ubicacion",
        "curso__diseno_diploma",
        "empleado",
        "empleado__datos_basicos",
        "diploma",
    ).get(pk=curso_empleado.pk)
    curso = curso_empleado.curso
    config = ConfiguracionGeneral.objects.first()
    firmas = get_course_signatures(curso)
    definition = build_course_design_definition(curso, firmas=firmas)
    context_map = build_token_context_map(
        curso=curso,
        curso_empleado=curso_empleado,
        config=config,
        firmas=firmas,
    )

    render_elements = build_render_elements(definition, context_map)

    return {
        "curso": curso,
        "curso_empleado": curso_empleado,
        "config": config,
        "design_definition": definition,
        "render_elements": render_elements,
        "fondo_url": definition["elements"]["fondo_diploma"]["image_url"],
    }
