from django.urls import path

from . import views

app_name = "diplomas"

urlpatterns = [
    path("dashboard/", views.diplomas_dahsboard, name="diplomas_dahsboard"),
    path("cursos/", views.cursos_lista, name="cursos_lista"),
    path("cursos/crear/", views.crear_curso_modal, name="crear_curso_modal"),
    path("agregar-empleado/", views.agregar_empleado_a_curso, name="agregar_empleado_curso"),
    path("ajax/buscar-empleado/", views.buscar_empleado_por_dpi, name="buscar_empleado_por_dpi"),
    path("curso/<int:curso_id>/", views.detalle_curso, name="detalle_curso"),
    path("curso/<int:curso_id>/agregar/", views.agregar_empleado_detalle, name="agregar_empleado_detalle"),
    path("curso/<int:curso_id>/editar/", views.editar_curso, name="editar_curso"),
    path('curso/<int:curso_id>/eliminar-participante/<int:participante_id>/', views.eliminar_participante, name='eliminar_participante'),
    path('curso/<int:curso_id>/diploma/<int:participante_id>/', views.ver_diploma, name='ver_diploma'),
    path("curso/<int:curso_id>/guardar-posiciones/", views.guardar_posiciones, name="guardar_posiciones"),

    path("firmas/", views.firmas_lista, name="firmas_lista"),
    path("firmas/crear/", views.crear_firma, name="crear_firma"),

    path("disenos/", views.disenos_lista, name="disenos_lista"),
    path("disenos/crear/", views.crear_diseno, name="crear_diseno"),
    path("disenos/<int:diseno_id>/editar/", views.editar_diseno, name="editar_diseno"),
    path("disenos/<int:diseno_id>/modificar/", views.modificar_diseno_visual, name="modificar_diseno_visual"),
    path("disenos/<int:diseno_id>/guardar-visual/", views.guardar_diseno_visual, name="guardar_diseno_visual"),
    path("disenos/<int:diseno_id>/eliminar/", views.eliminar_diseno, name="eliminar_diseno"),
]
