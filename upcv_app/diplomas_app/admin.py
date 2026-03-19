from django.contrib import admin

from .models import Curso, CursoEmpleado, Diploma, DisenoDiploma, Firma


@admin.register(Firma)
class FirmaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rol", "creado_en")
    search_fields = ("nombre", "rol")
    list_filter = ("creado_en",)


@admin.register(DisenoDiploma)
class DisenoDiplomaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "creado_en", "actualizado_en")
    search_fields = ("nombre", "descripcion")
    list_filter = ("activo", "creado_en")


class CursoEmpleadoInline(admin.TabularInline):
    model = CursoEmpleado
    extra = 0
    autocomplete_fields = ("empleado",)


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "diseno_diploma", "fecha_inicio", "fecha_fin", "creado_en")
    search_fields = ("codigo", "nombre")
    list_filter = ("fecha_inicio", "fecha_fin")
    filter_horizontal = ("firmas",)
    inlines = [CursoEmpleadoInline]
    readonly_fields = ("posiciones",)


@admin.register(CursoEmpleado)
class CursoEmpleadoAdmin(admin.ModelAdmin):
    list_display = ("curso", "empleado", "fecha_asignacion")
    search_fields = ("empleado__nombres", "empleado__apellidos", "curso__nombre")
    list_filter = ("curso", "fecha_asignacion")
    autocomplete_fields = ("curso", "empleado")


@admin.register(Diploma)
class DiplomaAdmin(admin.ModelAdmin):
    list_display = ("numero_diploma", "curso_empleado", "fecha_emision", "generado_en")
    search_fields = ("numero_diploma", "curso_empleado__empleado__nombres", "curso_empleado__empleado__apellidos")
    list_filter = ("fecha_emision", "generado_en")
    autocomplete_fields = ("curso_empleado",)
    readonly_fields = ("generado_en",)
