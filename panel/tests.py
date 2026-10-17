"""
Pruebas automáticas completas del Panel de Administración.
Cubre los 6 requerimientos obligatorios de seguridad, roles, horarios y stock:
(1) ADMIN_SUCURSAL no puede ver ni editar datos de otra sucursal (403 directo en URL y filtrado en listas)
(2) ADMIN_MAESTRO ve todo y el selector global de sucursal filtra correctamente
(3) Validación de tramos de horario sin solapamiento y prevención de turnos solapados entre distintas sucursales
(4) Bloqueos de intervalo eliminan exactamente esas horas del motor de disponibilidad pública
(5) Stock nunca negativo, traslado entre sucursales conserva el total y cancelar pedido devuelve stock
(6) Permisos: CLIENTE y BARBERO reciben 403 en vistas de administración
"""
from datetime import datetime, date, time, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from cuentas.models import Usuario
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio, CategoriaServicio
from reservas.models import HorarioTrabajo, Reserva, Bloqueo, DiaSemana
from reservas.motor import calcular_horarios_disponibles
from tienda.models import (
    Producto,
    CategoriaProducto,
    StockSucursal,
    MovimientoStock,
    Pedido,
    ItemPedido,
    registrar_movimiento_stock,
)
from contenido.models import ConfiguracionSitio


class PanelGestionMultiSucursalTestCase(TestCase):
    def setUp(self):
        # 1. Configuración de sitio
        self.config = ConfiguracionSitio.get_solo()
        self.config.horas_minimas_anticipacion = 1
        self.config.horas_minimas_cancelacion = 4
        self.config.tiempo_descanso_entre_citas_minutos = 0
        self.config.save()

        # 2. Sucursales
        self.sucursal_a = Sucursal.objects.create(
            nombre="Sucursal Providencia",
            slug="sucursal-providencia",
            direccion="Av. Providencia 123",
            comuna="Providencia",
            telefono="+5622222222",
            activa=True
        )
        self.sucursal_b = Sucursal.objects.create(
            nombre="Sucursal Las Condes",
            slug="sucursal-las-condes",
            direccion="Av. Apoquindo 456",
            comuna="Las Condes",
            telefono="+5623333333",
            activa=True
        )

        # 3. Usuarios y Roles
        self.admin_maestro = Usuario.objects.create_user(
            email="maestro@demobarberclub.cl",
            password="password123",
            rol=Usuario.Rol.ADMIN_MAESTRO,
            first_name="Admin",
            last_name="Maestro"
        )

        self.admin_sucursal_a = Usuario.objects.create_user(
            email="admin.prov@demobarberclub.cl",
            password="password123",
            rol=Usuario.Rol.ADMIN_SUCURSAL,
            first_name="Admin",
            last_name="Providencia"
        )
        self.admin_sucursal_a.sucursales_asignadas.add(self.sucursal_a)

        self.user_barbero_a = Usuario.objects.create_user(
            email="barbero.a@demobarberclub.cl",
            password="password123",
            rol=Usuario.Rol.BARBERO,
            first_name="Carlos",
            last_name="Providencia"
        )
        self.barbero_a = Barbero.objects.create(
            usuario=self.user_barbero_a,
            nombre_profesional="Carlos Barbero",
            slug="carlos-barbero",
            activo=True
        )
        self.barbero_a.sucursales.add(self.sucursal_a)

        self.user_barbero_b = Usuario.objects.create_user(
            email="barbero.b@demobarberclub.cl",
            password="password123",
            rol=Usuario.Rol.BARBERO,
            first_name="Mateo",
            last_name="Las Condes"
        )
        self.barbero_b = Barbero.objects.create(
            usuario=self.user_barbero_b,
            nombre_profesional="Mateo Barbero",
            slug="mateo-barbero",
            activo=True
        )
        self.barbero_b.sucursales.add(self.sucursal_b)

        self.user_cliente = Usuario.objects.create_user(
            email="cliente@test.cl",
            password="password123",
            rol=Usuario.Rol.CLIENTE,
            first_name="Juan",
            last_name="Cliente"
        )

        # 4. Catálogo y Tienda
        self.cat_serv = CategoriaServicio.objects.create(nombre="Cortes", slug="cortes")
        self.servicio = Servicio.objects.create(
            categoria=self.cat_serv,
            nombre="Corte Tradicional",
            slug="corte-tradicional",
            duracion_minutos=30,
            precio=18000,
            activo=True
        )

        self.cat_prod = CategoriaProducto.objects.create(nombre="Pomadas", slug="pomadas")
        self.producto = Producto.objects.create(
            categoria=self.cat_prod,
            nombre="Pomada Mate Clásica",
            slug="pomada-mate-clasica",
            precio=15000,
            sku="POM-MATE-01",
            stock_minimo_alerta=3,
            activo=True
        )

        # 5. Cliente HTTP
        self.client = Client(SERVER_NAME="localhost")

    # =========================================================================
    # REQ (1): ADMIN_SUCURSAL NO PUEDE VER NI EDITAR OTRA SUCURSAL (403)
    # =========================================================================
    def test_1_admin_sucursal_scope_restrictions(self):
        """ADMIN_SUCURSAL recibe 403 al intentar editar/eliminar datos de otra sucursal y sus listas están filtradas"""
        self.client.force_login(self.admin_sucursal_a)

        # 1.1 Listado de barberos solo debe incluir los de su sucursal (barbero_a)
        resp_list = self.client.get("/panel/barberos/")
        self.assertEqual(resp_list.status_code, 200)
        barberos_en_contexto = list(resp_list.context['barberos'])
        self.assertIn(self.barbero_a, barberos_en_contexto)
        self.assertNotIn(self.barbero_b, barberos_en_contexto)

        # 1.2 Intentar editar directamente un barbero de otra sucursal por URL debe dar 403
        resp_edit = self.client.get(f"/panel/barberos/{self.barbero_b.id}/editar/")
        self.assertEqual(resp_edit.status_code, 403)

        # 1.3 Intentar eliminar directamente un barbero de otra sucursal por URL debe dar 403
        resp_del = self.client.post(f"/panel/barberos/{self.barbero_b.id}/eliminar/")
        self.assertEqual(resp_del.status_code, 403)

        # 1.4 Intentar ver agenda de barbero fuera de su sucursal debe dar 403
        resp_agenda = self.client.get(f"/panel/agenda/?barbero={self.barbero_b.id}")
        self.assertEqual(resp_agenda.status_code, 403)

        # 1.5 Crear un pedido en sucursal B e intentar modificar su estado con admin A debe dar 403
        pedido_b = Pedido.objects.create(
            codigo_pedido="PED-COND-001",
            cliente_nombre="Cliente B",
            cliente_email="clienteb@test.cl",
            cliente_telefono="+56911112222",
            sucursal_retiro=self.sucursal_b,
            total=15000,
            estado=Pedido.Estado.PAGADO
        )
        resp_ped = self.client.post(
            f"/panel/pedidos/cambiar-estado/{pedido_b.codigo_pedido}/",
            {'nuevo_estado': Pedido.Estado.ENTREGADO}
        )
        self.assertEqual(resp_ped.status_code, 403)

        # 1.6 En el listado de pedidos, pedido_b no debe aparecer para admin A
        resp_ped_list = self.client.get("/panel/pedidos/")
        self.assertEqual(resp_ped_list.status_code, 200)
        pedidos_visibles = list(resp_ped_list.context['pedidos'])
        self.assertNotIn(pedido_b, pedidos_visibles)

    # =========================================================================
    # REQ (2): ADMIN_MAESTRO VE TODO Y SELECTOR GLOBAL FILTRA CORRECTAMENTE
    # =========================================================================
    def test_2_admin_maestro_ve_todo_y_filtro_global(self):
        """ADMIN_MAESTRO ve todo sin filtro, y al activar el selector global se filtran listados y vistas"""
        self.client.force_login(self.admin_maestro)

        # 2.1 Sin selector activo: ve ambos barberos
        resp_todos = self.client.get("/panel/barberos/")
        self.assertEqual(resp_todos.status_code, 200)
        barberos_todos = list(resp_todos.context['barberos'])
        self.assertIn(self.barbero_a, barberos_todos)
        self.assertIn(self.barbero_b, barberos_todos)

        # 2.2 Cambiar selector global a Sucursal A vía endpoint cambiar_sucursal
        resp_cambio = self.client.get(f"/panel/cambiar-sucursal/?sucursal={self.sucursal_a.id}", follow=True)
        self.assertEqual(resp_cambio.status_code, 200)
        self.assertEqual(self.client.session.get('panel_sucursal_id'), self.sucursal_a.id)

        # 2.3 Listado con selector activo en Sucursal A: solo debe aparecer barbero_a
        resp_filtrado = self.client.get("/panel/barberos/")
        self.assertEqual(resp_filtrado.status_code, 200)
        barberos_filtrados = list(resp_filtrado.context['barberos'])
        self.assertIn(self.barbero_a, barberos_filtrados)
        self.assertNotIn(self.barbero_b, barberos_filtrados)

        # 2.4 Restablecer selector a "Todas" (ID 0)
        resp_reset = self.client.get("/panel/cambiar-sucursal/?sucursal=0", follow=True)
        self.assertEqual(resp_reset.status_code, 200)
        self.assertIsNone(self.client.session.get('panel_sucursal_id'))

        # Vuelve a ver todos
        resp_todos_de_nuevo = self.client.get("/panel/barberos/")
        self.assertEqual(len(resp_todos_de_nuevo.context['barberos']), 2)

    # =========================================================================
    # REQ (3): VALIDACIÓN DE TRAMOS SIN SOLAPAMIENTO Y ENTRE SUCURSALES
    # =========================================================================
    def test_3_validacion_tramos_horarios_y_entre_sucursales(self):
        """Valida que inicio < fin, sin solapamientos en el mismo día ni turnos cruzados entre sucursales"""
        self.client.force_login(self.admin_maestro)

        # 3.1 Error cuando hora_inicio >= hora_fin (ej. 18:00-10:00)
        post_invalido = {
            'barbero_id': str(self.barbero_a.id),
            'sucursal_id': str(self.sucursal_a.id),
            'trabaja_0': 'on',
            'tramos_0': ['18:00-10:00'],
        }
        resp_inv = self.client.post("/panel/agenda/guardar-horario/", post_invalido, follow=True)
        self.assertEqual(resp_inv.status_code, 200)
        # No debe haberse creado el horario erróneo
        self.assertFalse(HorarioTrabajo.objects.filter(barbero=self.barbero_a, dia_semana=DiaSemana.LUNES).exists())

        # 3.2 Error por solapamiento de tramos el mismo día (ej. 10:00-14:00 y 13:00-18:00)
        post_solapado = {
            'barbero_id': str(self.barbero_a.id),
            'sucursal_id': str(self.sucursal_a.id),
            'trabaja_0': 'on',
            'tramos_0': ['10:00-14:00', '13:00-18:00'],
        }
        resp_sol = self.client.post("/panel/agenda/guardar-horario/", post_solapado, follow=True)
        self.assertEqual(resp_sol.status_code, 200)
        self.assertFalse(HorarioTrabajo.objects.filter(barbero=self.barbero_a, dia_semana=DiaSemana.LUNES).exists())

        # 3.3 Guardar tramos legítimos con pausa de colación en Sucursal A (10:00-14:00 y 15:00-19:00)
        post_legitimo = {
            'barbero_id': str(self.barbero_a.id),
            'sucursal_id': str(self.sucursal_a.id),
            'trabaja_0': 'on',
            'tramos_0': ['10:00-14:00', '15:00-19:00'],
        }
        resp_ok = self.client.post("/panel/agenda/guardar-horario/", post_legitimo, follow=True)
        self.assertEqual(resp_ok.status_code, 200)
        self.assertEqual(
            HorarioTrabajo.objects.filter(barbero=self.barbero_a, sucursal=self.sucursal_a, dia_semana=DiaSemana.LUNES).count(),
            2
        )

        # 3.4 Asignar barbero_a también a Sucursal B e intentar asignarle turno de 12:00 a 16:00 en Sucursal B el mismo día
        self.barbero_a.sucursales.add(self.sucursal_b)
        post_cruzado = {
            'barbero_id': str(self.barbero_a.id),
            'sucursal_id': str(self.sucursal_b.id),
            'trabaja_0': 'on',
            'tramos_0': ['12:00-16:00'],
        }
        resp_cruz = self.client.post("/panel/agenda/guardar-horario/", post_cruzado, follow=True)
        self.assertEqual(resp_cruz.status_code, 200)
        # No debe haberse creado el turno cruzado en Sucursal B porque choca con 10:00-14:00 y 15:00-19:00
        self.assertFalse(HorarioTrabajo.objects.filter(barbero=self.barbero_a, sucursal=self.sucursal_b, dia_semana=DiaSemana.LUNES).exists())

    # =========================================================================
    # REQ (4): BLOQUEO DE INTERVALO ELIMINA HORAS EN DISPONIBILIDAD PÚBLICA
    # =========================================================================
    def test_4_bloqueo_intervalo_elimina_horas_disponibilidad(self):
        """Un bloqueo horario elimina exactamente sus horas del motor de disponibilidad pública"""
        # Próximo lunes a futuro
        hoy = timezone.localdate()
        dias_a_lunes = (0 - hoy.weekday()) % 7
        if dias_a_lunes <= 1:
            dias_a_lunes += 7
        fecha_lunes = hoy + timedelta(days=dias_a_lunes)

        # Crear turno de trabajo 10:00 a 14:00
        HorarioTrabajo.objects.create(
            barbero=self.barbero_a,
            sucursal=self.sucursal_a,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(10, 0),
            hora_fin=time(14, 0),
            activo=True
        )

        # 4.1 Disponibilidad sin bloqueo: debe incluir 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30
        horarios_antes = calcular_horarios_disponibles(
            sucursal=self.sucursal_a,
            servicio=self.servicio,
            fecha_consulta=fecha_lunes,
            barbero=self.barbero_a
        )
        horas_antes = [h['hora'] for h in horarios_antes]
        self.assertIn('10:00', horas_antes)
        self.assertIn('10:30', horas_antes)
        self.assertIn('11:00', horas_antes)
        self.assertIn('12:00', horas_antes)

        # 4.2 Crear bloqueo de 10:00 a 11:30 para este barbero
        inicio_bloqueo = timezone.make_aware(datetime.combine(fecha_lunes, time(10, 0)))
        fin_bloqueo = timezone.make_aware(datetime.combine(fecha_lunes, time(11, 30)))
        Bloqueo.objects.create(
            barbero=self.barbero_a,
            sucursal=self.sucursal_a,
            fecha_inicio=inicio_bloqueo,
            fecha_fin=fin_bloqueo,
            tipo=Bloqueo.TipoBloqueo.BLOQUEO_MANUAL,
            motivo="Capacitación técnica"
        )

        # 4.3 Disponibilidad con bloqueo: 10:00, 10:30 y 11:00 no deben existir; 11:30 en adelante sí
        horarios_despues = calcular_horarios_disponibles(
            sucursal=self.sucursal_a,
            servicio=self.servicio,
            fecha_consulta=fecha_lunes,
            barbero=self.barbero_a
        )
        horas_despues = [h['hora'] for h in horarios_despues]
        self.assertNotIn('10:00', horas_despues)
        self.assertNotIn('10:30', horas_despues)
        self.assertNotIn('11:00', horas_despues)
        self.assertIn('11:30', horas_despues)
        self.assertIn('12:00', horas_despues)
        self.assertIn('12:30', horas_despues)

    # =========================================================================
    # REQ (5): STOCK NO NEGATIVO, TRASLADOS CONSERVAN TOTAL Y CANCELACIÓN DEVUELVE
    # =========================================================================
    def test_5_stock_seguridad_traslado_y_devolucion_por_cancelacion(self):
        """El stock nunca puede ser negativo, el traslado conserva el total y cancelar pedido restituye unidades"""
        # Inicializar stock: 10 en Sucursal A, 0 en Sucursal B
        stock_a = StockSucursal.objects.create(producto=self.producto, sucursal=self.sucursal_a, cantidad=10)
        stock_b = StockSucursal.objects.create(producto=self.producto, sucursal=self.sucursal_b, cantidad=0)

        # 5.1 Prevención de stock negativo: intentar sacar 15 unidades debe lanzar ValueError
        with self.assertRaises(ValueError) as ctx:
            registrar_movimiento_stock(
                producto=self.producto,
                sucursal=self.sucursal_a,
                tipo=MovimientoStock.Tipo.SALIDA,
                cantidad=15,
                usuario=self.admin_maestro,
                motivo="Prueba de sobregiro"
            )
        self.assertIn("insuficiente", str(ctx.exception).lower())
        stock_a.refresh_from_db()
        self.assertEqual(stock_a.cantidad, 10)

        # Ajuste a valor negativo también lanza ValueError
        with self.assertRaises(ValueError) as ctx2:
            registrar_movimiento_stock(
                producto=self.producto,
                sucursal=self.sucursal_a,
                tipo=MovimientoStock.Tipo.AJUSTE,
                cantidad=-5,
                usuario=self.admin_maestro,
                motivo="Ajuste inválido negativo"
            )
        self.assertIn("no puede ser negativo", str(ctx2.exception).lower())

        # 5.2 Traslado de 4 unidades de Sucursal A a Sucursal B
        self.client.force_login(self.admin_maestro)
        post_traslado = {
            'tipo': 'TRASLADO',
            'producto_id': str(self.producto.id),
            'sucursal_id': str(self.sucursal_a.id),
            'sucursal_destino_id': str(self.sucursal_b.id),
            'cantidad': '4',
            'motivo': 'Reposición por alta demanda',
        }
        resp_traslado = self.client.post("/panel/inventario/movimiento/", post_traslado, follow=True)
        self.assertEqual(resp_traslado.status_code, 200)

        stock_a.refresh_from_db()
        stock_b.refresh_from_db()
        self.assertEqual(stock_a.cantidad, 6)
        self.assertEqual(stock_b.cantidad, 4)
        self.assertEqual(stock_a.cantidad + stock_b.cantidad, 10, "El total consolidado se conserva exactamente")

        # 5.3 Venta y cancelación de pedido
        pedido = Pedido.objects.create(
            codigo_pedido="PED-PROV-999",
            cliente_nombre="Ignacio Rojas",
            cliente_email="ignacio@test.cl",
            cliente_telefono="+56955554444",
            sucursal_retiro=self.sucursal_a,
            total=30000,
            estado=Pedido.Estado.PAGADO
        )
        ItemPedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=self.producto.precio,
            subtotal=30000
        )
        # Descuento por venta
        registrar_movimiento_stock(
            producto=self.producto,
            sucursal=self.sucursal_a,
            tipo=MovimientoStock.Tipo.VENTA,
            cantidad=2,
            motivo=f"Venta Pedido #{pedido.codigo_pedido}"
        )
        stock_a.refresh_from_db()
        self.assertEqual(stock_a.cantidad, 4)

        # Cancelar pedido desde el panel: debe devolver las 2 unidades vía DEVOLUCION
        post_cancelar = {
            'nuevo_estado': Pedido.Estado.CANCELADO
        }
        resp_canc = self.client.post(f"/panel/pedidos/cambiar-estado/{pedido.codigo_pedido}/", post_cancelar, follow=True)
        self.assertEqual(resp_canc.status_code, 200)

        stock_a.refresh_from_db()
        self.assertEqual(stock_a.cantidad, 6, "El stock vuelve a 6 tras la cancelación del pedido")
        self.assertTrue(
            MovimientoStock.objects.filter(
                producto=self.producto,
                sucursal=self.sucursal_a,
                tipo=MovimientoStock.Tipo.DEVOLUCION,
                cantidad=2
            ).exists()
        )

    # =========================================================================
    # REQ (6): PERMISOS CLIENTE Y BARBERO RECIBEN 403 EN VISTAS DE ADMINISTRACIÓN
    # =========================================================================
    def test_6_permisos_cliente_y_barbero_reciben_403_en_admin(self):
        """CLIENTE y BARBERO reciben 403 Forbidden al intentar acceder a rutas de administración"""
        rutas_admin = [
            "/panel/",
            "/panel/barberos/",
            "/panel/servicios/",
            "/panel/productos/",
            "/panel/reservas/",
            "/panel/pedidos/",
        ]

        # 6.1 Un CLIENTE recibe 403 en todas las rutas de administración
        self.client.force_login(self.user_cliente)
        for ruta in rutas_admin:
            resp = self.client.get(ruta)
            self.assertEqual(
                resp.status_code, 403,
                f"CLIENTE debería recibir 403 al acceder a {ruta}, obtuvo {resp.status_code}"
            )

        # 6.2 Un BARBERO recibe 403 en gestión de barberos, servicios, inventario, etc.
        self.client.force_login(self.user_barbero_a)
        rutas_bloqueadas_para_barbero = [
            "/panel/barberos/",
            "/panel/servicios/",
            "/panel/productos/",
            "/panel/pedidos/",
        ]
        for ruta in rutas_bloqueadas_para_barbero:
            resp = self.client.get(ruta)
            self.assertEqual(
                resp.status_code, 403,
                f"BARBERO debería recibir 403 al acceder a {ruta}, obtuvo {resp.status_code}"
            )

        # 6.3 Pero el BARBERO SÍ tiene acceso legítimo a su propia agenda
        resp_agenda_propia = self.client.get("/panel/agenda/")
        self.assertEqual(resp_agenda_propia.status_code, 200)
