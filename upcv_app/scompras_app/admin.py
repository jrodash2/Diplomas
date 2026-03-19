from django.contrib import admin
from .models import (
    Institucion, Departamento, Seccion, SolicitudCompra,
    UsuarioDepartamento, FraseMotivacional, Perfil, Producto, Subproducto
)

# Inline para SolicitudCompra dentro de Seccion
class SolicitudCompraInline(admin.TabularInline):
    model = SolicitudCompra
    extra = 0
    fields = ('usuario', 'descripcion', 'fecha_solicitud', 'estado', 'prioridad', 'producto', 'subproducto')
    readonly_fields = ('fecha_solicitud',)

class SeccionInline(admin.TabularInline):
    model = Seccion
    extra = 0
    fields = ('nombre', 'descripcion', 'activo', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',)

# Admin para Institucion
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono')
    search_fields = ('nombre', 'direccion')

admin.site.register(Institucion, InstitucionAdmin)

# Admin para Perfil
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

admin.site.register(Perfil, PerfilAdmin)

# Admin para SolicitudCompra
class SolicitudCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'seccion', 'usuario', 'fecha_solicitud')
    search_fields = ('seccion__nombre', 'usuario__username', 'descripcion')
    list_filter = ('fecha_solicitud', 'estado', 'prioridad')

admin.site.register(SolicitudCompra, SolicitudCompraAdmin)

# Admin para Seccion con SolicitudCompra inline
class SeccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento', 'activo', 'fecha_creacion')
    search_fields = ('nombre', 'departamento__nombre')
    list_filter = ('activo', 'departamento')
    inlines = [SolicitudCompraInline]

admin.site.register(Seccion, SeccionAdmin)

# Admin para Departamento con Seccion inline
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id_departamento', 'nombre', 'descripcion', 'activo', 'fecha_creacion', 'fecha_actualizacion')
    search_fields = ('nombre', 'id_departamento')
    list_filter = ('activo', 'fecha_creacion', 'fecha_actualizacion')
    inlines = [SeccionInline]

admin.site.register(Departamento, DepartamentoAdmin)

# Admin para UsuarioDepartamento
class UsuarioDepartamentoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'departamento')
    search_fields = ('usuario__username', 'departamento__nombre')
    list_filter = ('departamento',)

admin.site.register(UsuarioDepartamento, UsuarioDepartamentoAdmin)

# Admin para FraseMotivacional
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')
    search_fields = ('frase', 'personaje')
    ordering = ('personaje',)

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)

from .models import Producto, Subproducto

# Inline para Subproducto dentro del admin de Producto
class SubproductoInline(admin.TabularInline):
    model = Subproducto
    extra = 1
    fields = ('nombre', 'codigo', 'descripcion', 'activo', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',)

# Admin para Producto
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'activo', 'fecha_creacion', 'fecha_actualizacion')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo', 'fecha_creacion')
    inlines = [SubproductoInline]

admin.site.register(Producto, ProductoAdmin)

# Admin para Subproducto independiente (si lo quieres fuera también)
class SubproductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'producto', 'activo', 'fecha_creacion')
    search_fields = ('nombre', 'codigo', 'producto__nombre')
    list_filter = ('producto', 'activo')

admin.site.register(Subproducto, SubproductoAdmin)
