"""
Módulo de modelos para la app 'reservas'.
Gestiona los turnos laborales de los barberos por sucursal, bloqueos y excepciones,
y el registro de reservas con estados y códigos únicos.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio, formatear_clp


class DiaSemana(models.IntegerChoices):
    LUNES = 0, _('Lunes')
    MARTES = 1, _('Martes')
    MIERCOLES = 2, _('Miércoles')
    JUEVES = 3, _('Jueves')
    VIERNES = 4, _('Viernes')
    SABADO = 5, _('Sábado')
    DOMINGO = 6, _('Domingo')


class HorarioTrabajo(models.Model):
    """
    Define el horario recurrente semanal de un barbero en una sucursal específica.
    Permite definir jornada con intervalo de almuerzo/colación.
    """
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='horarios_trabajo')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='horarios_barberos')
    dia_semana = models.IntegerField('Día de la Semana', choices=DiaSemana.choices)
    hora_inicio = models.TimeField('Hora de Entrada')
    hora_fin = models.TimeField('Hora de Salida')
    pausa_inicio = models.TimeField('Inicio de Colación/Pausa', null=True, blank=True)
    pausa_fin = models.TimeField('Fin de Colación/Pausa', null=True, blank=True)
    activo = models.BooleanField('Turno Activo', default=True)

    class Meta:
        verbose_name = 'Horario de Trabajo'
        verbose_name_plural = 'Horarios de Trabajo'
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.barbero.nombre_profesional} - {self.sucursal.nombre} ({self.get_dia_semana_display()}: {self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')})"


class Bloqueo(models.Model):
    """
    Bloqueo temporal de agenda por vacaciones, permisos, feriados o bloqueo manual.
    Si barbero es null, el bloqueo aplica a toda la sucursal.
    """
    class TipoBloqueo(models.TextChoices):
        VACACIONES = 'VACACIONES', _('Vacaciones')
        PERMISO = 'PERMISO', _('Permiso Personal')
        FERIADO = 'FERIADO', _('Feriado Nacional')
        BLOQUEO_MANUAL = 'BLOQUEO_MANUAL', _('Bloqueo Administrativo')

    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='bloqueos', null=True, blank=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='bloqueos', null=True, blank=True)
    fecha_inicio = models.DateTimeField('Inicio del Bloqueo')
    fecha_fin = models.DateTimeField('Fin del Bloqueo')
    tipo = models.CharField('Tipo de Bloqueo', max_length=25, choices=TipoBloqueo.choices, default=TipoBloqueo.BLOQUEO_MANUAL)
    motivo = models.CharField('Motivo del Bloqueo', max_length=200, blank=True)
    todo_el_dia = models.BooleanField('Bloqueo de todo el día', default=False)
    es_recurrente = models.BooleanField('Bloqueo recurrente semanal', default=False)
    dia_semana_recurrente = models.IntegerField('Día de la semana recurrente', choices=DiaSemana.choices, null=True, blank=True)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bloqueo de Agenda'
        verbose_name_plural = 'Bloqueos de Agenda'
        ordering = ['-fecha_inicio']

    def __str__(self):
        entidad = self.barbero.nombre_profesional if self.barbero else f"Toda la sucursal ({self.sucursal})"
        return f"Bloqueo: {entidad} [{self.get_tipo_display()}] {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')} - {self.fecha_fin.strftime('%d/%m/%Y %H:%M')}"


class Reserva(models.Model):
    """
    Registro formal de una cita agendada en la barbería.
    Soporta clientes autenticados y reservas express de invitados con token único.
    """
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', _('Pendiente de Confirmación')
        CONFIRMADA = 'CONFIRMADA', _('Confirmada')
        COMPLETADA = 'COMPLETADA', _('Completada')
        CANCELADA = 'CANCELADA', _('Cancelada')
        NO_ASISTIO = 'NO_ASISTIO', _('No Asistió')

    codigo_reserva = models.CharField('Código de Reserva', max_length=15, unique=True, editable=False)
    token_invitado = models.UUIDField('Token para Gestión de Invitado', default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reservas',
        null=True,
        blank=True,
        verbose_name='Cliente Registrado'
    )
    cliente_nombre = models.CharField('Nombre del Cliente', max_length=120)
    cliente_email = models.EmailField('Correo Electrónico')
    cliente_telefono = models.CharField('Teléfono / WhatsApp', max_length=25)

    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='reservas')
    barbero = models.ForeignKey(Barbero, on_delete=models.PROTECT, related_name='reservas')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='reservas')

    fecha_hora_inicio = models.DateTimeField('Fecha y Hora de Inicio')
    fecha_hora_fin = models.DateTimeField('Fecha y Hora de Finalización')
    precio = models.IntegerField('Precio Acordado en CLP', default=0)
    estado = models.CharField('Estado de la Reserva', max_length=20, choices=Estado.choices, default=Estado.CONFIRMADA)
    notas = models.TextField('Notas o Peticiones Especiales', blank=True)

    creado_el = models.DateTimeField('Fecha de Creación', auto_now_add=True)
    actualizado_el = models.DateTimeField('Última Modificación', auto_now=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_hora_inicio']
        indexes = [
            models.Index(fields=['fecha_hora_inicio', 'barbero']),
            models.Index(fields=['codigo_reserva']),
            models.Index(fields=['estado']),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            # Generar código de reserva comercial amigable, ej. DBC-9428
            import random
            numero = random.randint(1000, 9999)
            self.codigo_reserva = f"DBC-{numero}"
            # Asegurar unicidad rápida
            while Reserva.objects.filter(codigo_reserva=self.codigo_reserva).exists():
                numero = random.randint(1000, 9999)
                self.codigo_reserva = f"DBC-{numero}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_reserva} - {self.cliente_nombre} con {self.barbero.nombre_profesional} ({self.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')})"

    @property
    def precio_formateado(self):
        return formatear_clp(self.precio)

    @property
    def duracion_minutos(self):
        diff = self.fecha_hora_fin - self.fecha_hora_inicio
        return int(diff.total_seconds() / 60)
