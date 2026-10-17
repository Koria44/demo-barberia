"""
Rutas de la aplicación 'panel' (Dashboard de Administración Propio).
"""
from django.urls import path
from panel import views

app_name = 'panel'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('reservas/', views.reservas_list_view, name='reservas_list'),
    path('reservas/cambiar-estado/<str:codigo_reserva>/', views.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    path('reservas/exportar/csv/', views.exportar_reservas_csv, name='exportar_reservas_csv'),
    
    path('agenda/', views.agenda_barbero_view, name='agenda_barbero'),
    
    path('pedidos/', views.pedidos_list_view, name='pedidos_list'),
    path('pedidos/cambiar-estado/<str:codigo_pedido>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('pedidos/exportar/csv/', views.exportar_ventas_csv, name='exportar_ventas_csv'),
    
    path('servicios/', views.catalogo_servicios_panel, name='servicios_list'),
    path('productos/', views.catalogo_productos_panel, name='productos_list'),
    path('barberos/', views.barberos_panel_list, name='barberos_list'),
    path('sucursales/', views.sucursales_panel_list, name='sucursales_list'),
    path('clientes/', views.clientes_panel_list, name='clientes_list'),
    path('configuracion/', views.configuracion_sitio_view, name='configuracion'),
]
