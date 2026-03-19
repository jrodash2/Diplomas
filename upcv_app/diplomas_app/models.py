from django.db import models
from empleados_app.models import Empleado
from django.utils import timezone


class Firma(models.Model):
    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=150)
    firma = models.ImageField(upload_to="firmas/", help_text="Suba la firma en PNG con fondo transparente.")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


class DisenoDiploma(models.Model):
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

    posiciones = models.JSONField(default=dict, blank=True)  # ⭐ NUEVO CAMPO AQUÍ

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CursoEmpleado(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="participantes")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="cursos")
    fecha_asignacion = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('curso', 'empleado')
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"

    def __str__(self):
        return f"{self.empleado} en {self.curso}"


class Diploma(models.Model):
    curso_empleado = models.OneToOneField(CursoEmpleado, on_delete=models.CASCADE, related_name="diploma")
    numero_diploma = models.CharField(max_length=50, blank=True, null=True)
    fecha_emision = models.DateField(default=timezone.now)
    generado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diploma de {self.curso_empleado.empleado} - {self.curso_empleado.curso}"
