"""
Rutas públicas de la aplicación 'contenido'.
"""
from django.urls import path
from contenido import views

app_name = 'sitio_publico'

urlpatterns = [
    path('', views.inicio_view, name='inicio'),
    path('sucursales/<slug:slug>/', views.sucursal_detalle_view, name='sucursal_detalle'),
    path('blog/', views.blog_lista_view, name='blog_lista'),
    path('blog/<slug:slug>/', views.blog_detalle_view, name='blog_detalle'),
    path('contacto/enviar/', views.contacto_submit_view, name='contacto_submit'),
]
