from django.contrib import admin
from .models import Ticket
from .models import TipoEquipo
from .models import Oficina
from .models import FraseMotivacional

class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'oficina', 'via_contacto', 'tipo_equipo', 'problema', 'responsable', 'tecnico_asignado', 'estado', 'fecha_creacion', 'fecha_actualizacion')
    list_filter = ('estado', 'fecha_creacion', 'fecha_actualizacion')
    search_fields = ('problema', 'responsable', 'tecnico_asignado')

admin.site.register(Ticket, TicketAdmin)


class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


admin.site.register(TipoEquipo, TipoEquipoAdmin)


class OficinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


admin.site.register(Oficina, OficinaAdmin)


# Crea una clase que personaliza la vista en el admin
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')  # Qué campos mostrar en la lista
    search_fields = ('frase', 'personaje')  # Habilitar búsqueda por estos campos
    ordering = ('personaje',)  # Ordenar por el campo 'personaje'

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)