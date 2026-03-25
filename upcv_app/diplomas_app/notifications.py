import logging
import smtplib
import ssl
from urllib.parse import urlencode

import certifi
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail import get_connection
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from empleados_app.models import ConfiguracionGeneral

from .models import CursoEmpleado

logger = logging.getLogger(__name__)


def _build_course_context(participante, request=None):
    curso = participante.curso
    configuracion = ConfiguracionGeneral.objects.first()
    institucion = getattr(configuracion, "nombre_institucion", "UPCV") or "UPCV"
    ubicacion = getattr(curso.ubicacion, "nombre", "Sin ubicación") if curso else "Sin ubicación"

    diploma_query = urlencode(
        {
            "codigo_curso": curso.codigo,
            "dpi": participante.dpi_participante,
        }
    )
    diploma_relative_url = f"{reverse('diplomas:public_diploma_download')}?{diploma_query}"
    if request:
        diploma_url = request.build_absolute_uri(diploma_relative_url)
    else:
        diploma_url = diploma_relative_url

    return {
        "participante": participante,
        "curso": curso,
        "institucion": institucion,
        "ubicacion": ubicacion,
        "diploma_url": diploma_url,
    }


def _send_notification_email(*, to_email, subject, text_template, html_template, context):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connection = get_connection(ssl_context=ssl_context)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost")
    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to_email],
        connection=connection,
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def _resolve_valid_recipient(raw_email):
    email = (raw_email or "").strip()
    if not email:
        return None, "missing_email"
    try:
        validate_email(email)
    except ValidationError:
        return None, "invalid_email"
    return email, ""


def send_enrollment_notification(participante, request=None):
    email, reason = _resolve_valid_recipient(participante.correo_participante)
    if not email:
        if reason == "invalid_email":
            logger.warning(
                "Correo inválido para inscripción participante_id=%s curso_id=%s",
                participante.id,
                participante.curso_id,
            )
        return {"status": "skipped", "reason": reason}

    if participante.correo_inscripcion_enviado_en:
        return {"status": "skipped", "reason": "already_sent"}

    context = _build_course_context(participante, request=request)
    subject = f"Confirmación de inscripción - {participante.curso.nombre}"

    try:
        _send_notification_email(
            to_email=email,
            subject=subject,
            text_template="diplomas/emails/inscripcion.txt",
            html_template="diplomas/emails/inscripcion.html",
            context=context,
        )
    except Exception as exc:
        logger.exception(
            "No se pudo enviar correo de inscripción para participante_id=%s curso_id=%s",
            participante.id,
            participante.curso_id,
        )
        CursoEmpleado.objects.filter(id=participante.id).update(ultimo_error_correo_inscripcion=str(exc)[:1000])
        return {"status": "error", "reason": str(exc)}

    now = timezone.now()
    CursoEmpleado.objects.filter(id=participante.id).update(
        correo_inscripcion_enviado_en=now,
        ultimo_error_correo_inscripcion="",
    )
    participante.correo_inscripcion_enviado_en = now
    participante.ultimo_error_correo_inscripcion = ""
    return {"status": "sent"}


def send_completion_notifications_for_finished_courses(request=None, course=None):
    today = timezone.localdate()
    queryset = CursoEmpleado.objects.filter(curso__fecha_fin__lte=today, correo_finalizacion_enviado_en__isnull=True)
    if course is not None:
        queryset = queryset.filter(curso=course)

    summary = {"sent": 0, "skipped": 0, "errors": 0}
    for participante_id in queryset.values_list("id", flat=True).iterator():
        with transaction.atomic():
            locked = (
                CursoEmpleado.objects.select_for_update()
                .filter(pk=participante_id, correo_finalizacion_enviado_en__isnull=True)
                .first()
            )
            if not locked:
                summary["skipped"] += 1
                continue
            if locked.correo_finalizacion_enviado_en:
                summary["skipped"] += 1
                continue

            email, reason = _resolve_valid_recipient(locked.correo_participante)
            if not email:
                if reason == "invalid_email":
                    logger.warning(
                        "Correo inválido para finalización participante_id=%s curso_id=%s",
                        locked.id,
                        locked.curso_id,
                    )
                summary["skipped"] += 1
                continue

            context = _build_course_context(locked, request=request)
            subject = f"Finalización de curso y diploma disponible - {locked.curso.nombre}"
            try:
                _send_notification_email(
                    to_email=email,
                    subject=subject,
                    text_template="diplomas/emails/finalizacion.txt",
                    html_template="diplomas/emails/finalizacion.html",
                    context=context,
                )
            except Exception as exc:
                logger.exception(
                    "No se pudo enviar correo de finalización para participante_id=%s curso_id=%s",
                    locked.id,
                    locked.curso_id,
                )
                locked.ultimo_error_correo_finalizacion = str(exc)[:1000]
                locked.save(update_fields=["ultimo_error_correo_finalizacion"])
                summary["errors"] += 1
                if isinstance(exc, smtplib.SMTPAuthenticationError):
                    summary["fatal_error"] = "smtp_auth"
                    return summary
                continue

            locked.correo_finalizacion_enviado_en = timezone.now()
            locked.ultimo_error_correo_finalizacion = ""
            locked.save(update_fields=["correo_finalizacion_enviado_en", "ultimo_error_correo_finalizacion"])
            summary["sent"] += 1

    return summary
