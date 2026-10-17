"""
Rutas de la aplicación 'tienda'.
"""
from django.urls import path
from tienda import views

app_name = 'tienda'

urlpatterns = [
    path('', views.catalogo_view, name='catalogo'),
    path('producto/<slug:slug>/', views.producto_detalle_view, name='producto_detalle'),
    path('carrito/', views.ver_carrito_view, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_carrito_view, name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_carrito_view, name='actualizar_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_carrito_view, name='eliminar_carrito'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('pedido/<str:codigo_pedido>/confirmacion/', views.confirmacion_pedido_view, name='confirmacion_pedido'),
]
