from django.urls import path

from . import views

app_name = "diplomas"

urlpatterns = [
    path("publico/registro/", views.public_course_registration, name="public_course_registration"),
    path("publico/descarga/", views.public_diploma_download, name="public_diploma_download"),
    path("publico/ajax/curso/", views.public_buscar_curso_por_codigo, name="public_buscar_curso_por_codigo"),
    path("publico/ajax/participante/", views.public_buscar_participante_por_dpi, name="public_buscar_participante_por_dpi"),

    path("dashboard/", views.diplomas_dahsboard, name="diplomas_dahsboard"),

    path("ubicaciones/", views.ubicaciones_lista, name="ubicaciones_lista"),
    path("ubicaciones/crear/", views.crear_ubicacion, name="crear_ubicacion"),
    path("ubicaciones/<int:ubicacion_id>/editar/", views.editar_ubicacion, name="editar_ubicacion"),
    path("ubicaciones/<int:ubicacion_id>/eliminar/", views.eliminar_ubicacion, name="eliminar_ubicacion"),

    path("asignaciones/", views.asignaciones_ubicacion_lista, name="asignaciones_ubicacion_lista"),
    path("asignaciones/crear/", views.crear_asignacion_ubicacion, name="crear_asignacion_ubicacion"),
    path("asignaciones/<int:asignacion_id>/editar/", views.editar_asignacion_ubicacion, name="editar_asignacion_ubicacion"),
    path("asignaciones/<int:asignacion_id>/eliminar/", views.eliminar_asignacion_ubicacion, name="eliminar_asignacion_ubicacion"),

    path("cursos/", views.cursos_lista, name="cursos_lista"),
    path("cursos/crear/", views.crear_curso_modal, name="crear_curso_modal"),
    path("agregar-empleado/", views.agregar_empleado_a_curso, name="agregar_empleado_curso"),
    path("ajax/buscar-empleado/", views.buscar_empleado_por_dpi, name="buscar_empleado_por_dpi"),
    path("curso/<int:curso_id>/", views.detalle_curso, name="detalle_curso"),
    path("curso/<int:curso_id>/exportar-participantes/", views.exportar_participantes_excel, name="exportar_participantes_excel"),
    path("curso/<int:curso_id>/agregar/", views.agregar_empleado_detalle, name="agregar_empleado_detalle"),
    path("curso/<int:curso_id>/participante/<int:participante_id>/editar/", views.editar_participante_detalle, name="editar_participante_detalle"),
    path("curso/<int:curso_id>/editar/", views.editar_curso, name="editar_curso"),
    path("curso/<int:curso_id>/eliminar-participante/<int:participante_id>/", views.eliminar_participante, name="eliminar_participante"),
    path("curso/<int:curso_id>/diploma/<int:participante_id>/", views.ver_diploma, name="ver_diploma"),
    path("curso/<int:curso_id>/guardar-posiciones/", views.guardar_posiciones, name="guardar_posiciones"),

    path("firmas/", views.firmas_lista, name="firmas_lista"),
    path("firmas/crear/", views.crear_firma, name="crear_firma"),
    path("firmas/<int:firma_id>/editar/", views.editar_firma, name="editar_firma"),
    path("firmas/<int:firma_id>/eliminar/", views.eliminar_firma, name="eliminar_firma"),

    path("disenos/", views.disenos_lista, name="disenos_lista"),
    path("disenos/crear/", views.crear_diseno, name="crear_diseno"),
    path("disenos/<int:diseno_id>/editar/", views.editar_diseno, name="editar_diseno"),
    path("disenos/<int:diseno_id>/modificar/", views.modificar_diseno_visual, name="modificar_diseno_visual"),
    path("disenos/<int:diseno_id>/guardar-visual/", views.guardar_diseno_visual, name="guardar_diseno_visual"),
    path("disenos/<int:diseno_id>/subir-imagen-visual/", views.subir_imagen_diseno_visual, name="subir_imagen_diseno_visual"),
    path("disenos/<int:diseno_id>/eliminar/", views.eliminar_diseno, name="eliminar_diseno"),
]
