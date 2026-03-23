from django.conf import settings
from django.db import models
from django.utils import timezone

from empleados_app.models import Empleado


class UbicacionDiploma(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ubicaciones_diplomas_creadas",
    )

    class Meta:
        verbose_name = "Ubicación de diplomas"
        verbose_name_plural = "Ubicaciones de diplomas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Firma(models.Model):
    ubicacion = models.ForeignKey(
        UbicacionDiploma,
        on_delete=models.PROTECT,
        related_name="firmas",
        blank=True,
        null=True,
    )
    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=150)
    firma = models.ImageField(upload_to="firmas/", help_text="Suba la firma en PNG con fondo transparente.")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


class DisenoDiploma(models.Model):
    ubicacion = models.ForeignKey(
        UbicacionDiploma,
        on_delete=models.PROTECT,
        related_name="disenos",
        blank=True,
        null=True,
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    imagen_fondo = models.ImageField(upload_to="diplomas/fondos/", blank=True, null=True)
    estilos = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diseño de diploma"
        verbose_name_plural = "Diseños de diploma"

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"{self.nombre} ({estado})"


class Curso(models.Model):
    ubicacion = models.ForeignKey(
        UbicacionDiploma,
        on_delete=models.PROTECT,
        related_name="cursos",
        blank=True,
        null=True,
    )
    codigo = models.CharField(
        max_length=5,
        unique=True,
        help_text="Código del curso (5 dígitos)."
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    firmas = models.ManyToManyField(
        Firma,
        blank=True,
        related_name="cursos"
    )

    diseno_diploma = models.ForeignKey(
        DisenoDiploma,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="cursos",
        help_text="Diseño de diploma que utilizará el curso."
    )

    posiciones = models.JSONField(default=dict, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CursoEmpleado(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="participantes")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="cursos", null=True, blank=True)
    participante_dpi = models.CharField(max_length=15, blank=True, default="")
    participante_nombre = models.CharField(max_length=200, blank=True, default="")
    participante_foto = models.ImageField(upload_to="diplomas/participantes/", null=True, blank=True)
    participante_correo = models.EmailField(blank=True, default="")
    participante_telefono = models.CharField(max_length=30, blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    fecha_asignacion = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('curso', 'empleado')
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"

    def __str__(self):
        return f"{self.nombre_participante or self.empleado or 'Participante'} en {self.curso}"

    @property
    def nombre_participante(self):
        if self.participante_nombre:
            return self.participante_nombre
        if self.empleado_id:
            return f"{self.empleado.nombres} {self.empleado.apellidos}".strip()
        return ""

    @property
    def dpi_participante(self):
        if self.participante_dpi:
            return self.participante_dpi
        return getattr(self.empleado, "dpi", "")

    @property
    def foto_participante_url(self):
        foto = self.participante_foto or getattr(self.empleado, "imagen", None)
        try:
            return foto.url if foto else ""
        except Exception:
            return ""

    @property
    def correo_participante(self):
        if self.participante_correo:
            return self.participante_correo
        datos_basicos = getattr(self.empleado, "datos_basicos", None)
        return getattr(datos_basicos, "correo_institucional", "") or ""

    @property
    def telefono_participante(self):
        if self.participante_telefono:
            return self.participante_telefono
        datos_basicos = getattr(self.empleado, "datos_basicos", None)
        return getattr(datos_basicos, "telefono_personal", "") or ""

    @property
    def observaciones_participante(self):
        return self.observaciones or ""


class Diploma(models.Model):
    curso_empleado = models.OneToOneField(CursoEmpleado, on_delete=models.CASCADE, related_name="diploma")
    numero_diploma = models.CharField(max_length=50, blank=True, null=True)
    fecha_emision = models.DateField(default=timezone.now)
    generado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diploma de {self.curso_empleado.nombre_participante or self.curso_empleado.empleado} - {self.curso_empleado.curso}"


class UsuarioUbicacionDiploma(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asignacion_ubicacion_diplomas",
    )
    ubicacion = models.ForeignKey(
        UbicacionDiploma,
        on_delete=models.CASCADE,
        related_name="asignaciones_usuarios",
    )
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="asignaciones_ubicacion_diplomas_realizadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asignación de usuario a ubicación"
        verbose_name_plural = "Asignaciones de usuarios a ubicación"

    def __str__(self):
        return f"{self.usuario} -> {self.ubicacion}"
