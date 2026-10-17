"""
Rutas de la aplicación 'reservas'.
"""
from django.urls import path
from reservas import views

app_name = 'reservas'

urlpatterns = [
    path('agendar/', views.agendar_view, name='agendar'),
    path('confirmacion/<str:codigo_reserva>/', views.reserva_confirmacion_view, name='confirmacion'),
    path('cancelar-invitado/<uuid:token_invitado>/', views.cancelar_reserva_invitado_view, name='cancelar_invitado'),
    
    # Endpoints JSON para agendamiento interactivo sin recarga
    path('api/servicios/', views.api_servicios_sucursal, name='api_servicios'),
    path('api/barberos/', views.api_barberos_disponibles, name='api_barberos'),
    path('api/dias-disponibles/', views.api_dias_disponibles, name='api_dias_disponibles'),
    path('api/horarios/', views.api_horarios_disponibles, name='api_horarios'),
    path('api/confirmar/', views.api_confirmar_reserva, name='api_confirmar'),
]
