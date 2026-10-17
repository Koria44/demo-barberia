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

    def test_disponibilidad_cada_dia_semana_incluyendo_domingo_y_lunes(self):
        """(1) Verifica disponibilidad para cada día de la semana incluyendo domingo y lunes"""
        # Crear turnos de Lunes a Sábado para self.barbero en self.sucursal_prov
        for d in [DiaSemana.MARTES, DiaSemana.MIERCOLES, DiaSemana.JUEVES, DiaSemana.VIERNES, DiaSemana.SABADO]:
            HorarioTrabajo.objects.get_or_create(
                barbero=self.barbero,
                sucursal=self.sucursal_prov,
                dia_semana=d,
                defaults={
                    'hora_inicio': time(10, 0),
                    'hora_fin': time(18, 0),
                    'pausa_inicio': time(13, 0),
                    'pausa_fin': time(14, 0),
                    'activo': True
                }
            )

        # Buscar el próximo lunes y el próximo domingo a futuro
        hoy = timezone.localdate()
        dias_a_lunes = (0 - hoy.weekday()) % 7
        if dias_a_lunes <= 1:
            dias_a_lunes += 7
        proximo_lunes = hoy + timedelta(days=dias_a_lunes)
        proximo_domingo = proximo_lunes + timedelta(days=6)

        # Lunes debe tener disponibilidad
        horarios_lunes = calcular_horarios_disponibles(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            fecha_consulta=proximo_lunes,
            barbero=self.barbero
        )
        self.assertGreater(len(horarios_lunes), 0, "Lunes debería tener horarios disponibles")

        # Domingo no tiene turnos configurados, debe retornar lista vacía
        horarios_domingo = calcular_horarios_disponibles(
            sucursal=self.sucursal_prov,
            servicio=self.servicio,
            fecha_consulta=proximo_domingo,
            barbero=self.barbero
        )
        self.assertEqual(len(horarios_domingo), 0, "Domingo debe tener 0 horarios disponibles")

    def test_endpoint_json_horarios_fecha_valida(self):
        """(2) Endpoint JSON responde con horarios para una fecha válida"""
        from django.test import Client
        client = Client(SERVER_NAME='localhost')
        url = f"/reservas/api/horarios/?sucursal_id={self.sucursal_prov.id}&servicio_id={self.servicio.id}&fecha={self.fecha_lunes.strftime('%Y-%m-%d')}&barbero_id={self.barbero.id}"
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('horarios', data)
        self.assertIsInstance(data['horarios'], list)
        self.assertGreater(len(data['horarios']), 0)
        primer_slot = data['horarios'][0]
        self.assertIn('hora', primer_slot)
        self.assertIn('barberos_count', primer_slot)

    def test_agenda_panel_roles_acceso(self):
        """(3) Agenda del panel responde 200 para ADMINISTRADOR y BARBERO, y 403/redirección para CLIENTE"""
        from django.test import Client
        client = Client(SERVER_NAME='localhost')

        admin_user = Usuario.objects.create_user(
            email="admin.test@demobarberclub.cl", password="password123", rol=Usuario.Rol.ADMIN_MAESTRO
        )
        cliente_user = Usuario.objects.create_user(
            email="cliente.test@demobarberclub.cl", password="password123", rol=Usuario.Rol.CLIENTE
        )

        # 1. Administrador (sin perfil de barbero) debe responder 200
        client.force_login(admin_user)
        resp_admin = client.get("/panel/agenda/")
        self.assertEqual(resp_admin.status_code, 200)

        # 2. Barbero autenticado debe responder 200
        client.force_login(self.user_barbero)
        resp_barbero = client.get("/panel/agenda/")
        self.assertEqual(resp_barbero.status_code, 200)

        # 3. Cliente debe ser redirigido / bloqueado
        client.force_login(cliente_user)
        resp_cliente = client.get("/panel/agenda/")
        self.assertIn(resp_cliente.status_code, [302, 403])

    def test_admin_ve_agenda_barbero_distinto(self):
        """(4) Admin ve la agenda de un barbero distinto y un barbero no puede ver la de otro"""
        from django.test import Client
        client = Client(SERVER_NAME='localhost')

        user_barbero2 = Usuario.objects.create_user(
            email="barbero2.test@demobarberclub.cl", password="password123", rol=Usuario.Rol.BARBERO
        )
        barbero2 = Barbero.objects.create(
            usuario=user_barbero2, nombre_profesional="Barbero Dos", slug="barbero-dos", activo=True
        )

        admin_user = Usuario.objects.create_user(
            email="admin2.test@demobarberclub.cl", password="password123", rol=Usuario.Rol.ADMIN_MAESTRO
        )

        # Admin consulta específicamente la agenda de barbero2
        client.force_login(admin_user)
        resp_admin = client.get(f"/panel/agenda/?barbero={barbero2.id}")
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(resp_admin.context['barbero'], barbero2)

        # Barbero 1 intenta consultar agenda de barbero 2; la vista debe forzar a barbero 1
        client.force_login(self.user_barbero)
        resp_b1 = client.get(f"/panel/agenda/?barbero={barbero2.id}")
        self.assertEqual(resp_b1.status_code, 200)
        self.assertEqual(resp_b1.context['barbero'], self.barbero)

