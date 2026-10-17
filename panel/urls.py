"""
Rutas de la aplicación 'panel' (Dashboard de Administración Propio).
"""
from django.urls import path
from panel import views

app_name = 'panel'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('cambiar-sucursal/', views.cambiar_sucursal, name='cambiar_sucursal'),

    # Reservas
    path('reservas/', views.reservas_list_view, name='reservas_list'),
    path('reservas/cambiar-estado/<str:codigo_reserva>/', views.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    path('reservas/exportar/csv/', views.exportar_reservas_csv, name='exportar_reservas_csv'),
    
    # Agenda, Horarios y Bloqueos
    path('agenda/', views.agenda_barbero_view, name='agenda_barbero'),
    path('agenda/guardar-horario/', views.guardar_horario_semanal, name='guardar_horario_semanal'),
    path('agenda/copiar-horario-semana/', views.copiar_horario_semana, name='copiar_horario_semana'),
    path('agenda/copiar-horario-barbero/', views.copiar_horario_barbero, name='copiar_horario_barbero'),
    path('agenda/bloqueos/crear/', views.crear_bloqueo_view, name='crear_bloqueo'),
    path('agenda/bloqueos/<int:bloqueo_id>/eliminar/', views.eliminar_bloqueo_view, name='eliminar_bloqueo'),
    path('agenda/reserva-rapida/', views.reserva_rapida_view, name='reserva_rapida'),
    
    # Pedidos y Ventas
    path('pedidos/', views.pedidos_list_view, name='pedidos_list'),
    path('pedidos/cambiar-estado/<str:codigo_pedido>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('pedidos/exportar/csv/', views.exportar_ventas_csv, name='exportar_ventas_csv'),
    
    # Barberos CRUD
    path('barberos/', views.barberos_panel_list, name='barberos_list'),
    path('barberos/nuevo/', views.barbero_crear_view, name='barbero_crear'),
    path('barberos/<int:barbero_id>/editar/', views.barbero_editar_view, name='barbero_editar'),
    path('barberos/<int:barbero_id>/toggle-activo/', views.barbero_toggle_activo_view, name='barbero_toggle_activo'),
    path('barberos/<int:barbero_id>/eliminar/', views.barbero_eliminar_view, name='barbero_eliminar'),

    # Servicios CRUD
    path('servicios/', views.catalogo_servicios_panel, name='servicios_list'),
    path('servicios/nuevo/', views.servicio_crear_view, name='servicio_crear'),
    path('servicios/<int:servicio_id>/editar/', views.servicio_editar_view, name='servicio_editar'),
    path('servicios/<int:servicio_id>/toggle-activo/', views.servicio_toggle_activo_view, name='servicio_toggle_activo'),
    path('servicios/<int:servicio_id>/sucursales/', views.servicio_sucursales_view, name='servicio_sucursales'),
    path('servicios/<int:servicio_id>/eliminar/', views.servicio_eliminar_view, name='servicio_eliminar'),

    # Productos e Inventario
    path('productos/', views.inventario_panel_view, name='productos_list'),
    path('productos/nuevo/', views.producto_crear_view, name='producto_crear'),
    path('productos/<int:producto_id>/editar/', views.producto_editar_view, name='producto_editar'),
    path('productos/<int:producto_id>/eliminar/', views.producto_eliminar_view, name='producto_eliminar'),
    path('inventario/movimiento/', views.registrar_movimiento_panel, name='registrar_movimiento'),
    path('inventario/exportar/csv/', views.exportar_movimientos_csv, name='exportar_movimientos_csv'),
    path('categorias-productos/', views.categorias_producto_view, name='categorias_producto'),

    # Sucursales, Clientes y Configuración
    path('sucursales/', views.sucursales_panel_list, name='sucursales_list'),
    path('clientes/', views.clientes_panel_list, name='clientes_list'),
    path('configuracion/', views.configuracion_sitio_view, name='configuracion'),
]
