from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy



app_name = 'scompras'

# Manejador global de errores (esto debe estar fuera de urlpatterns)
handler403 = 'scompras_app.views.acceso_denegado'  # Asegúrate que el nombre de tu app sea correcto

urlpatterns = [
    path('', views.home, name='home'), 
    path('dahsboard/', views.dashboard_admin, name='dahsboard'),  # compatibilidad con ruta previa
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    # Acceso denegado
    path('no-autorizado/', views.acceso_denegado, name='acceso_denegado'),
    path('importar-excel/', views.importar_excel, name='importar_excel'),
    path('catalogo-insumos/', views.catalogo_insumos_view, name='catalogo_insumos_view'),  
    path('insumos-json/', views.insumos_json, name='insumos_json'),
    path('agregar-insumo-solicitud/', views.agregar_insumo_solicitud, name='agregar_insumo_solicitud'),
    path('eliminar-servicio/<int:servicio_id>/', views.eliminar_servicio_solicitud, name='eliminar_servicio_solicitud'),
    path('detalle-seccion-usuario/', views.detalle_seccion_usuario, name='detalle_seccion_usuario'),
    path('dashboard-usuario/', views.dashboard_scompras, name='dashboard_usuario'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/scompras/', views.dashboard_scompras, name='dashboard_scompras'),

    
    

    path('descargar-insumos/', views.descargar_insumos_excel, name='descargar_insumos'),
    # Usuarios
    path('usuario/crear/', views.user_create, name='user_create'),
    path('usuario/editar/<int:user_id>/', views.user_edit, name='user_edit'),

    path('usuario/eliminar/<int:user_id>/', views.user_delete, name='user_delete'),

    # Presupuesto
    path('presupuestos/', views.presupuesto_anual_list, name='presupuesto_anual_list'),
    path('presupuestos/crear/', views.presupuesto_anual_crear, name='presupuesto_anual_crear'),
    path('presupuestos/<int:presupuesto_id>/', views.presupuesto_anual_detalle, name='presupuesto_anual_detalle'),
    path('presupuestos/<int:presupuesto_id>/activar/', views.activar_presupuesto, name='activar_presupuesto'),
    path('presupuestos/<int:presupuesto_id>/carga-masiva/', views.presupuesto_renglon_carga_masiva, name='presupuesto_renglon_carga_masiva'),
    path('presupuestos/renglon/<int:renglon_id>/kardex/', views.kardex_renglon, name='kardex_renglon'),
    path('presupuestos/transferencias/', views.transferencias_list, name='transferencias_list'),
    path('presupuestos/transferencias/crear/', views.transferencia_crear, name='transferencia_crear'),
    path('presupuestos/transferencias/crear-multiple/', views.transferencia_multiple_crear, name='transferencia_multiple_crear'),
    path('presupuestos/transferencias/buscar-renglones/', views.transferencia_buscar_renglones, name='transferencia_buscar_renglones'),
    path('presupuestos/transferencias/renglon-monto/', views.transferencia_renglon_monto, name='transferencia_renglon_monto'),
    path('presupuestos/transferencias/<int:pk>/reversar/', views.reversar_transferencia, name='reversar_transferencia'),
    path('catalogo/subproductos/', views.subproductos_por_producto, name='subproductos_por_producto'),

    # Departamentos
    path('departamento/', views.crear_departamento, name='crear_departamento'),
    path('departamento/editar/<int:pk>/', views.editar_departamento, name='editar_departamento'),
    path('departamentos/', views.lista_departamentos, name='lista_departamentos'),
    path('departamento/<int:pk>/', views.detalle_departamento, name='detalle_departamento'),
    path('departamento/<int:departamento_id>/seccion/<int:seccion_id>/', views.detalle_seccion, name='detalle_seccion'),
    path('secciones/', views.crear_seccion, name='crear_seccion'),
    path('secciones/editar/<int:pk>/', views.crear_seccion, name='editar_seccion'),

    path('ajax/cargar-secciones/', views.ajax_cargar_secciones, name='ajax_cargar_secciones'),
    path('ajax/cargar_subproductos/', views.ajax_cargar_subproductos, name='ajax_cargar_subproductos'),
    path('solicitud/<int:pk>/',views.SolicitudCompraDetailView.as_view(), name='detalle_solicitud'),
    path('solicitud/<int:solicitud_id>/asignar-analista/', views.asignar_analista_solicitud, name='asignar_analista_solicitud'),
    path('solicitud/<int:solicitud_id>/asignar-tipo-proceso/', views.asignar_tipo_proceso_solicitud, name='asignar_tipo_proceso_solicitud'),
    path('solicitud/<int:solicitud_id>/pasos/<int:paso_id>/toggle/', views.toggle_paso_solicitud, name='toggle_paso_solicitud'),
    path('solicitud/<int:solicitud_id>/set-paso-actual/', views.set_paso_actual_solicitud, name='set_paso_actual_solicitud'),
    path('solicitud/<int:solicitud_id>/cdp/nuevo/', views.crear_cdp_solicitud, name='crear_cdp_solicitud'),
    path('cdp/<int:cdp_id>/ejecutar/', views.ejecutar_cdp, name='ejecutar_cdp'),
    path('cdp/<int:cdp_id>/liberar/', views.liberar_cdp, name='liberar_cdp'),
    path('cdp/<int:cdp_id>/pdf/', views.generar_pdf_cdp, name='generar_pdf_cdp'),
    path('solicitudes/<int:solicitud_id>/cdp/liberar-todos/', views.liberar_cdps_solicitud, name='liberar_cdps_solicitud'),
    path('solicitud/eliminar_insumo/<int:detalle_id>/', views.eliminar_detalle_solicitud, name='eliminar_detalle_solicitud'),
    path(
        'actualizar-caracteristica-especial/',
        views.actualizar_caracteristica_especial,
        name='actualizar_caracteristica_especial',
    ),
    path(
        'actualizar-caracteristica-insumo/<int:detalle_id>/',
        views.actualizar_caracteristica_insumo,
        name='actualizar_caracteristica_insumo',
    ),
    path(
        'actualizar-caracteristica-servicio/<int:servicio_id>/',
        views.actualizar_caracteristica_servicio,
        name='actualizar_caracteristica_servicio',
    ),
    path(
        'actualizar-nombre-servicio/<int:pk>/',
        views.actualizar_nombre_servicio,
        name='actualizar_nombre_servicio',
    ),
    path('editar-solicitud/', views.editar_solicitud, name='editar_solicitud'),
    path('subproductos/<int:producto_id>/', views.obtener_subproductos, name='obtener_subproductos'),
    path('finalizar_solicitud/', views.finalizar_solicitud, name='finalizar_solicitud'),
    path('rechazar_solicitud/', views.rechazar_solicitud, name='rechazar_solicitud'),
    path('solicitud/<int:solicitud_id>/generar_pdf/', views.generar_pdf_solicitud, name='generar_pdf_solicitud'),
    path('agregar-servicio-solicitud/', views.agregar_servicio_solicitud, name='agregar_servicio_solicitud'),
    path('analista/dashboard/', views.analista_dashboard, name='analista_dashboard'),
    path('analista/bandeja/', views.analista_bandeja, name='analista_bandeja'),
    path('tipos-proceso/', views.tipos_proceso, name='tipos_proceso'),
    path('tipos-proceso/crear/', views.crear_tipo_proceso, name='crear_tipo_proceso'),
    path('tipos-proceso/<int:tipo_id>/editar/', views.editar_tipo_proceso, name='editar_tipo_proceso'),
    path('tipos-proceso/<int:tipo_id>/pasos/', views.pasos_tipo_proceso, name='pasos_tipo_proceso'),
    path(
        'tipos-proceso/<int:tipo_id>/subtipos/<int:subtipo_id>/pasos/',
        views.pasos_tipo_proceso,
        name='pasos_subtipo_proceso',
    ),
    path('tipos-proceso/<int:tipo_id>/pasos/crear/', views.crear_paso_proceso, name='crear_paso_proceso'),
    path('pasos/<int:paso_id>/editar/', views.editar_paso_proceso, name='editar_paso_proceso'),
    path('subtipos/crear/', views.crear_subtipo_proceso, name='crear_subtipo_proceso'),

    # CRUD Tipos/Subtipos/Pasos
    path('procesos/tipos/', views.tipos_proceso_list, name='tipos_proceso_list'),
    path('procesos/tipos/create/', views.tipo_proceso_create, name='tipo_proceso_create'),
    path('procesos/tipos/<int:tipo_id>/update/', views.tipo_proceso_update, name='tipo_proceso_update'),
    path('procesos/tipos/<int:tipo_id>/toggle/', views.tipo_proceso_toggle, name='tipo_proceso_toggle'),
    path('procesos/tipos/<int:tipo_id>/eliminar/', views.tipo_proceso_eliminar, name='tipo_proceso_eliminar'),
    path(
        'procesos/tipos/<int:tipo_id>/subtipos/',
        views.subtipos_proceso_list,
        name='subtipos_proceso_list',
    ),
    path(
        'procesos/tipos/<int:tipo_id>/subtipos/create/',
        views.subtipo_proceso_create,
        name='subtipo_proceso_create',
    ),
    path(
        'procesos/subtipos/<int:subtipo_id>/update/',
        views.subtipo_proceso_update,
        name='subtipo_proceso_update',
    ),
    path(
        'procesos/subtipos/<int:subtipo_id>/toggle/',
        views.subtipo_proceso_toggle,
        name='subtipo_proceso_toggle',
    ),
    path(
        'procesos/tipos/<int:tipo_id>/subtipos/<int:subtipo_id>/eliminar/',
        views.subtipo_proceso_eliminar,
        name='subtipo_proceso_eliminar',
    ),
    path(
        'procesos/tipos/<int:tipo_id>/pasos/',
        views.pasos_tipo_list,
        name='pasos_tipo_list',
    ),
    path(
        'procesos/tipos/<int:tipo_id>/subtipos/<int:subtipo_id>/pasos/',
        views.pasos_subtipo_list,
        name='pasos_subtipo_list',
    ),
    path(
        'procesos/tipos/<int:tipo_id>/pasos/create/',
        views.paso_create_tipo,
        name='paso_create_tipo',
    ),
    path(
        'procesos/subtipos/<int:subtipo_id>/pasos/create/',
        views.paso_create_subtipo,
        name='paso_create_subtipo',
    ),
    path(
        'procesos/pasos/<int:paso_id>/update/',
        views.paso_update,
        name='paso_update',
    ),
    path(
        'procesos/pasos/<int:paso_id>/toggle/',
        views.paso_toggle,
        name='paso_toggle',
    ),
    path(
        'procesos/pasos/<int:paso_id>/eliminar/',
        views.paso_proceso_eliminar,
        name='paso_proceso_eliminar',
    ),



    path('insumos-disponibles-json/', views.insumos_disponibles_json, name='insumos_disponibles_json'),
    

   


    # Asignación de usuarios a departamentos
    path('asignar-usuario-departamento/', views.asignar_departamento_usuario, name='asignar_departamento'),
    path('eliminar-asignacion/<int:usuario_id>/<int:departamento_id>/<int:seccion_id>/', views.eliminar_asignacion, name='eliminar_asignacion'),
    path('editar_institucion/', views.editar_institucion, name='editar_institucion'),



# Cambiar contraseña
path(
    'cambiar-contrasena/',
    auth_views.PasswordChangeView.as_view(
        template_name='scompras/password_change_form.html',
        success_url=reverse_lazy('scompras:password_change_done')  # aquí el namespace
    ),
    name='password_change'
),

path(
    'cambiar-contrasena/hecho/',
    auth_views.PasswordChangeDoneView.as_view(
        template_name='scompras/password_change_done.html'
    ),
    name='password_change_done'
),

  


]
