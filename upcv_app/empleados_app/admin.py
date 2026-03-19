from django.contrib import admin
from .models import Contrato, Empleado, Puesto, Sede
from .models import ConfiguracionGeneral
from datetime import datetime


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion')
    search_fields = ('nombre',)


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'dpi', 'imagen',  'activo', 'created_at', 'updated_at')
    list_filter = ('activo',)
    search_fields = ('nombres', 'apellidos')
    date_hierarchy = 'created_at'
    fields = ('nombres', 'apellidos', 'dpi', 'imagen', 'tipoc', 'activo')


class ConfiguracionGeneralAdmin(admin.ModelAdmin):
    list_display = ('nombre_institucion', 'direccion', 'logotipo')  # Campos a mostrar en la lista
    search_fields = ('nombre_institucion', 'direccion')  # Campos por los que se puede buscar
    list_filter = ('nombre_institucion',)  # Campos por los que se puede filtrar
    readonly_fields = ('id',)  # Solo lectura para el campo ID (si es un campo automático)

class ContratoAdmin(admin.ModelAdmin):
    list_display = (
        'empleado', 'fecha_inicio', 'fecha_vencimiento', 'activo',
        'tipo_contrato', 'renglon', 'sede', 'puesto', 'created_at', 'updated_at'
    )
    list_filter = ('activo', 'fecha_inicio', 'fecha_vencimiento', 'sede', 'puesto')
    search_fields = ('empleado__nombres', 'empleado__apellidos', 'sede__nombre', 'puesto__nombre')
    date_hierarchy = 'fecha_inicio'
    autocomplete_fields = ['empleado', 'sede', 'puesto']
    readonly_fields = ('created_at', 'updated_at')


    def save_model(self, request, obj, form, change):
        """Asegura que la lógica de desactivación se aplique también desde el admin."""
        if obj.fecha_vencimiento and obj.fecha_vencimiento <= datetime.today().date():
            obj.activo = False
        super().save_model(request, obj, form, change)
    
# Registro del modelo, solo una vez
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(ConfiguracionGeneral, ConfiguracionGeneralAdmin)
admin.site.register(Contrato, ContratoAdmin)


