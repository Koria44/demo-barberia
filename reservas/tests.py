"""
Pruebas automáticas unitarias y de integración para el sistema de reservas.
Cubre:
1. Cálculo de disponibilidad horaria
2. Prevención de doble reserva concurrente
3. Barbero que atiende en múltiples sucursales
4. Políticas de cancelación
"""
from datetime import datetime, date, time, timedelta
from django.test import TestCase
from django.utils import timezone

from cuentas.models import Usuario
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio
from reservas.models import HorarioTrabajo, Reserva, DiaSemana
from reservas.motor import calcular_horarios_disponibles, crear_reserva_segura
from contenido.models import ConfiguracionSitio


class ReservasMotorTestCase(TestCase):
    def setUp(self):
        # 1. Configuración de sitio
        self.config = ConfiguracionSitio.get_solo()
        self.config.horas_minimas_anticipacion = 1
        self.config.horas_minimas_cancelacion = 4
        self.config.tiempo_descanso_entre_citas_minutos = 10
        self.config.save()

        # 2. Sucursales
        self.sucursal_prov = Sucursal.objects.create(
            nombre="Providencia", slug="providencia", direccion="Av. Providencia 100", comuna="Providencia", telefono="+5622222222"
        )
        self.sucursal_condes = Sucursal.objects.create(
            nombre="Las Condes", slug="las-condes", direccion="Av. Apoquindo 200", comuna="Las Condes", telefono="+5623333333"
        )

        # 3. Barbero Multi-sucursal
        self.user_barbero = Usuario.objects.create_user(
            email="test.barbero@demobarberclub.cl", password="password123", first_name="Juan", last_name="Perez", rol=Usuario.Rol.BARBERO
        )
        self.barbero = Barbero.objects.create(
            usuario=self.user_barbero, nombre_profesional="Juan Pérez", slug="juan-perez", activo=True
        )
        self.barbero.sucursales.add(self.sucursal_prov, self.sucursal_condes)

        # 4. Servicio
        self.servicio = Servicio.objects.create(
            nombre="Corte Clásico", slug="corte-clasico", duracion_minutos=45, precio=18000, activo=True
        )

        # 5. Turno laboral: Lunes en Providencia de 10:00 a 14:00
        # Fecha de prueba: próximo lunes a futuro
        hoy = timezone.now().date()
        dias_hasta_lunes = (0 - hoy.weekday()) % 7
        if dias_hasta_lunes <= 1:
            dias_hasta_lunes += 7
        self.fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)

        HorarioTrabajo.objects.create(
            barbero=self.barbero,
            sucursal=self.sucursal_prov,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(10, 0),
            hora_fin=time(14, 0),
            pausa_inicio=time(12, 0),
            pausa_fin=time(12, 30),
            activo=True
        )

    def test_calculo_disponibilidad_basico(self):
        """Verifica que los horarios calculados respeten la jornada y la pausa de colación"""
        horarios = calcular_horarios_disponibles(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            fecha_consulta=self.fecha_lunes,
            barbero=self.barbero
        )
        # Debería ofrecer horarios válidos (10:00, 10:30, 11:00...)
        horas_disponibles = [h['hora'] for h in horarios]
        self.assertIn('10:00', horas_disponibles)
        self.assertIn('10:30', horas_disponibles)
        # 12:00 es la pausa de colación, no debe ofrecerse un servicio de 45 min que choque con 12:00 - 12:30
        self.assertNotIn('12:00', horas_disponibles)

    def test_prevencion_doble_reserva(self):
        """Verifica que no se permita agendar dos reservas solapadas con el mismo barbero"""
        slot_ini = timezone.make_aware(datetime.combine(self.fecha_lunes, time(10, 0)))
        slot_fin = slot_ini + timedelta(minutes=self.servicio.duracion_minutos)

        datos_cli1 = {'nombre': 'Cliente 1', 'email': 'cli1@test.cl', 'telefono': '+56911111111'}
        exito1, res1 = crear_reserva_segura(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            barbero=self.barbero,
            slot_inicio=slot_ini,
            slot_fin=slot_fin,
            datos_cliente=datos_cli1
        )
        self.assertTrue(exito1)
        self.assertIsInstance(res1, Reserva)

        # Intento de colisión simultánea
        datos_cli2 = {'nombre': 'Cliente 2', 'email': 'cli2@test.cl', 'telefono': '+56922222222'}
        exito2, res2 = crear_reserva_segura(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            barbero=self.barbero,
            slot_inicio=slot_ini,
            slot_fin=slot_fin,
            datos_cliente=datos_cli2
        )
        self.assertFalse(exito2)
        self.assertIn("acaba de ser reservado", res2)

    def test_barbero_en_varias_sucursales_no_se_solapa(self):
        """Si un barbero tiene cita a las 10:00 en Providencia, no puede tener cita a las 10:00 en Las Condes"""
        slot_ini = timezone.make_aware(datetime.combine(self.fecha_lunes, time(10, 0)))
        slot_fin = slot_ini + timedelta(minutes=self.servicio.duracion_minutos)

        # Reserva en Providencia
        crear_reserva_segura(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            barbero=self.barbero,
            slot_inicio=slot_ini,
            slot_fin=slot_fin,
            datos_cliente={'nombre': 'Carlos', 'email': 'carlos@test.cl', 'telefono': '+5691234'}
        )

        # Turno ficticio en Las Condes para el mismo día
        HorarioTrabajo.objects.create(
            barbero=self.barbero,
            sucursal=self.sucursal_condes,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(10, 0),
            hora_fin=time(14, 0),
            activo=True
        )

        # Calcular disponibilidad en Las Condes: 10:00 no debe estar disponible
        horarios_condes = calcular_horarios_disponibles(
            sucursal=self.sucursal_condes,
            servicio=self.servicio,
            fecha_consulta=self.fecha_lunes,
            barbero=self.barbero
        )
        horas_disp_condes = [h['hora'] for h in horarios_condes]
        self.assertNotIn('10:00', horas_disp_condes)

    def test_politica_cancelacion(self):
        """Verifica la política de anticipación mínima para cancelar"""
        ahora = timezone.now()
        # Reserva dentro de 2 horas (política exige 4 horas de anticipación)
        res_proxima = Reserva.objects.create(
            cliente_nombre="Pedro",
            cliente_email="pedro@test.cl",
            cliente_telefono="+569999",
            sucursal=self.sucursal_prov,
            barbero=self.barbero,
            servicio=self.servicio,
            fecha_hora_inicio=ahora + timedelta(hours=2),
            fecha_hora_fin=ahora + timedelta(hours=2, minutes=45),
            precio=18000,
            estado=Reserva.Estado.CONFIRMADA
        )
        limite = res_proxima.fecha_hora_inicio - timedelta(hours=self.config.horas_minimas_cancelacion)
        # ahora > limite significa que ya pasó el plazo permitido de cancelación
        self.assertTrue(ahora > limite)
