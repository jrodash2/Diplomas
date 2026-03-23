from django.contrib import admin

from .models import Curso, CursoEmpleado, Diploma, DisenoDiploma, Firma, UbicacionDiploma


@admin.register(UbicacionDiploma)
class UbicacionDiplomaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "abreviatura", "activa", "creado_en")
    search_fields = ("nombre", "abreviatura")
    list_filter = ("activa", "creado_en")


@admin.register(Firma)
class FirmaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rol", "ubicacion", "creado_en")
    search_fields = ("nombre", "rol", "ubicacion__nombre", "ubicacion__abreviatura")
    list_filter = ("ubicacion", "creado_en")


@admin.register(DisenoDiploma)
class DisenoDiplomaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "activo", "creado_en", "actualizado_en")
    search_fields = ("nombre", "descripcion", "ubicacion__nombre", "ubicacion__abreviatura")
    list_filter = ("ubicacion", "activo", "creado_en")


class CursoEmpleadoInline(admin.TabularInline):
    model = CursoEmpleado
    extra = 0
    autocomplete_fields = ("empleado",)


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "ubicacion", "diseno_diploma", "fecha_inicio", "fecha_fin", "creado_en")
    search_fields = ("codigo", "nombre", "ubicacion__nombre", "ubicacion__abreviatura")
    list_filter = ("ubicacion", "fecha_inicio", "fecha_fin")
    filter_horizontal = ("firmas",)
    inlines = [CursoEmpleadoInline]
    readonly_fields = ("posiciones",)


@admin.register(CursoEmpleado)
class CursoEmpleadoAdmin(admin.ModelAdmin):
    list_display = ("curso", "empleado", "fecha_asignacion")
    search_fields = ("empleado__nombres", "empleado__apellidos", "curso__nombre", "curso__ubicacion__abreviatura")
    list_filter = ("curso__ubicacion", "curso", "fecha_asignacion")
    autocomplete_fields = ("curso", "empleado")


@admin.register(Diploma)
class DiplomaAdmin(admin.ModelAdmin):
    list_display = ("numero_diploma", "curso_empleado", "fecha_emision", "generado_en")
    search_fields = ("numero_diploma", "curso_empleado__empleado__nombres", "curso_empleado__empleado__apellidos")
    list_filter = ("fecha_emision", "generado_en")
    autocomplete_fields = ("curso_empleado",)
    readonly_fields = ("generado_en",)
