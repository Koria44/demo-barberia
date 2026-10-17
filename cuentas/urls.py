"""
Rutas de la aplicación 'cuentas'.
"""
from django.urls import path
from cuentas import views

app_name = 'cuentas'

urlpatterns = [
    path('ingresar/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('salir/', views.logout_view, name='logout'),
    path('recuperar-clave/', views.recuperar_clave_view, name='recuperar_clave'),
    path('mi-cuenta/', views.mi_cuenta_view, name='mi_cuenta'),
    path('mi-cuenta/cancelar/<str:codigo_reserva>/', views.cancelar_reserva_cliente, name='cancelar_reserva'),
    path('redireccionar/', views.redirect_por_rol_view, name='redirect_por_rol'),
]
