"""
Comando de gestión de Django para poblar la base de datos con datos de demostración
completos y de alta gama para Demo Barber Club.
Uso: python manage.py cargar_demo
"""
import random
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from cuentas.models import Usuario
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import CategoriaServicio, Servicio, ServicioSucursal, ServicioBarbero
from reservas.models import HorarioTrabajo, Bloqueo, Reserva, DiaSemana
from tienda.models import CategoriaProducto, Producto, Pedido, ItemPedido, StockSucursal, MovimientoStock, registrar_movimiento_stock
from contenido.models import ConfiguracionSitio, Testimonio, PreguntaFrecuente, ImagenGaleria, EntradaBlog


class Command(BaseCommand):
    help = 'Puebla la base de datos con datos de demostración para Demo Barber Club'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== Iniciando carga de datos demo para Demo Barber Club ==="))

        # 1. Configuración del Sitio
        config = ConfiguracionSitio.get_solo()
        config.nombre_negocio = "Demo Barber Club"
        config.eslogan = "El Arte de la Barbería Tradicional & Contemporánea"
        config.descripcion_corta = "Atelier de barbería premium en Santiago de Chile. Cortes de cabello de autor, afeitado tradicional con toalla caliente y productos exclusivos de cuidado masculino."
        config.telefono_principal = "+56 2 2345 6789"
        config.whatsapp_numero = "+56912345678"
        config.whatsapp_mensaje = "Hola, vengo del sitio web y quería hacer una consulta sobre los servicios y reservas."
        config.instagram_usuario = "demobarberclub.cl"
        config.facebook_url = "https://facebook.com/demobarberclub"
        config.email_contacto = "contacto@demobarberclub.cl"
        config.horas_minimas_anticipacion = 2
        config.horas_minimas_cancelacion = 4
        config.dias_maximos_futuro = 30
        config.tiempo_descanso_entre_citas_minutos = 10
        config.color_fondo = "#FFFFFF"
        config.color_acento = "#0A0A0A"
        config.color_texto = "#0A0A0A"
        config.stat_anios = 8
        config.stat_clientes = 15400
        config.stat_cortes = 32800
        config.stat_barberos = 5
        config.banner_anuncio_activo = True
        config.banner_anuncio_texto = "⚡ AGENDA ONLINE Y RECIBE UN CAFÉ DE ESPECIALIDAD DE CORTESÍA EN TU VISITA"
        config.save()
        self.stdout.write(self.style.SUCCESS("[OK] Configuracion del sitio establecida."))

        # 2. Cuentas de Usuarios Base
        # Administrador
        admin_user, created = Usuario.objects.get_or_create(
            email="admin@demobarberclub.cl",
            defaults={
                "username": "admin@demobarberclub.cl",
                "first_name": "Administrador",
                "last_name": "Demo",
                "telefono": "+56 9 8888 7777",
                "rol": Usuario.Rol.ADMIN_MAESTRO,
                "is_staff": True,
                "is_superuser": True
            }
        )
        admin_user.set_password("admin123")
        admin_user.save()

        # Barbero Demo de Acceso
        barbero_demo_user, created = Usuario.objects.get_or_create(
            email="barbero@demobarberclub.cl",
            defaults={
                "username": "barbero@demobarberclub.cl",
                "first_name": "Matías",
                "last_name": "Silva",
                "telefono": "+56 9 7777 6666",
                "rol": Usuario.Rol.BARBERO
            }
        )
        barbero_demo_user.set_password("barbero123")
        barbero_demo_user.save()

        # Cliente Demo de Acceso
        cliente_demo_user, created = Usuario.objects.get_or_create(
            email="cliente@demobarberclub.cl",
            defaults={
                "username": "cliente@demobarberclub.cl",
                "first_name": "Carlos",
                "last_name": "Muñoz",
                "telefono": "+56 9 9999 5555",
                "rol": Usuario.Rol.CLIENTE,
                "notas_cliente": "Prefiere fade medio sin navaja en el cuello. Piel sensible."
            }
        )
        cliente_demo_user.set_password("cliente123")
        cliente_demo_user.save()

        # Otros clientes para enriquecer datos del dashboard
        clientes_ficticios = [
            ("Ignacio", "Lagos", "ignacio.lagos@ejemplo.cl", "+56 9 1122 3344"),
            ("Sebastián", "Ríos", "sebastian.rios@ejemplo.cl", "+56 9 2233 4455"),
            ("Felipe", "Galdames", "felipe.g@ejemplo.cl", "+56 9 3344 5566"),
            ("Cristóbal", "Vargas", "c.vargas@ejemplo.cl", "+56 9 4455 6677"),
        ]
        cliente_objs = [cliente_demo_user]
        for nom, ape, mail, tel in clientes_ficticios:
            u, _ = Usuario.objects.get_or_create(
                email=mail,
                defaults={
                    "username": mail,
                    "first_name": nom,
                    "last_name": ape,
                    "telefono": tel,
                    "rol": Usuario.Rol.CLIENTE
                }
            )
            u.set_password("cliente123")
            u.save()
            cliente_objs.append(u)
        self.stdout.write(self.style.SUCCESS("[OK] Usuarios de prueba creados (admin, barbero, cliente)."))

        # 3. Sucursales
        sucursales_datos = [
            {
                "nombre": "Sucursal Providencia",
                "slug": "providencia",
                "direccion": "Av. Providencia 2145, Local 4",
                "comuna": "Providencia",
                "ciudad": "Santiago",
                "telefono": "+56 2 2233 4455",
                "whatsapp": "+56912345678",
                "email": "providencia@demobarberclub.cl",
                "latitud": -33.4248,
                "longitud": -70.6119,
                "horario_atencion": "Lunes a Sábado: 10:00 - 20:00 hrs",
                "foto_estatica_demo": "img/sucursales/providencia.webp",
                "orden": 1,
                "descripcion": "Ubicada en pleno corazón de Providencia a pasos del Metro Los Leones. Dispone de barra de café de especialidad y estacionamiento para clientes."
            },
            {
                "nombre": "Sucursal Las Condes",
                "slug": "las-condes",
                "direccion": "Av. Apoquindo 4800, Nivel 2",
                "comuna": "Las Condes",
                "ciudad": "Santiago",
                "telefono": "+56 2 2345 7788",
                "whatsapp": "+56912345678",
                "email": "lascondes@demobarberclub.cl",
                "latitud": -33.4116,
                "longitud": -70.5794,
                "horario_atencion": "Lunes a Sábado: 10:00 - 20:00 hrs",
                "foto_estatica_demo": "img/sucursales/las_condes.webp",
                "orden": 2,
                "descripcion": "Frente al Metro Escuela Militar. Espacio amplio con sillones de barbero Takara Belmont de alta gama y zona de relajación con bebidas frías."
            },
            {
                "nombre": "Sucursal Vitacura",
                "slug": "vitacura",
                "direccion": "Av. Vitacura 5600",
                "comuna": "Vitacura",
                "ciudad": "Santiago",
                "telefono": "+56 2 2456 9900",
                "whatsapp": "+56912345678",
                "email": "vitacura@demobarberclub.cl",
                "latitud": -33.3934,
                "longitud": -70.5752,
                "horario_atencion": "Lunes a Sábado: 10:00 - 20:00 hrs",
                "foto_estatica_demo": "img/sucursales/vitacura.webp",
                "orden": 3,
                "descripcion": "En el exclusivo sector de Alonso de Córdova. Cabinas privadas de afeitado tradicional y visagismo personalizado para caballeros."
            }
        ]

        sucursal_objs = []
        for s_data in sucursales_datos:
            suc, _ = Sucursal.objects.update_or_create(
                slug=s_data["slug"],
                defaults=s_data
            )
            sucursal_objs.append(suc)
        suc_prov, suc_condes, suc_vita = sucursal_objs
        self.stdout.write(self.style.SUCCESS("[OK] 3 Sucursales creadas."))

        # 3.1 Administradores de Sucursal (1 por sucursal)
        admin_prov, _ = Usuario.objects.get_or_create(
            email="admin.providencia@demobarberclub.cl",
            defaults={
                "username": "admin.providencia@demobarberclub.cl",
                "first_name": "Admin",
                "last_name": "Providencia",
                "telefono": "+56 9 7711 2233",
                "rol": Usuario.Rol.ADMIN_SUCURSAL,
                "is_staff": True,
            }
        )
        admin_prov.set_password("admin123")
        admin_prov.save()
        admin_prov.sucursales_asignadas.set([suc_prov])

        admin_condes, _ = Usuario.objects.get_or_create(
            email="admin.lascondes@demobarberclub.cl",
            defaults={
                "username": "admin.lascondes@demobarberclub.cl",
                "first_name": "Admin",
                "last_name": "Las Condes",
                "telefono": "+56 9 7722 3344",
                "rol": Usuario.Rol.ADMIN_SUCURSAL,
                "is_staff": True,
            }
        )
        admin_condes.set_password("admin123")
        admin_condes.save()
        admin_condes.sucursales_asignadas.set([suc_condes])

        admin_vita, _ = Usuario.objects.get_or_create(
            email="admin.vitacura@demobarberclub.cl",
            defaults={
                "username": "admin.vitacura@demobarberclub.cl",
                "first_name": "Admin",
                "last_name": "Vitacura",
                "telefono": "+56 9 7733 4455",
                "rol": Usuario.Rol.ADMIN_SUCURSAL,
                "is_staff": True,
            }
        )
        admin_vita.set_password("admin123")
        admin_vita.save()
        admin_vita.sucursales_asignadas.set([suc_vita])
        self.stdout.write(self.style.SUCCESS("[OK] 3 Administradores de sucursal creados y vinculados."))

        # 4. Barberos Profesionales (algunos trabajan en 2 sucursales)
        barberos_datos = [
            {
                "usuario": barbero_demo_user,
                "nombre_profesional": "Matías Silva",
                "slug": "matias-silva",
                "sucursales": [suc_prov, suc_condes],
                "foto_estatica_demo": "img/barberos/matias_silva.webp",
                "especialidad_principal": "Master Barber • Especialista en Fade y Texturas",
                "bio": "Más de 9 años esculpiendo estilos impecables. Certificado internacionalmente en técnicas de degradado de precisión milimétrica.",
                "instagram": "matias.barber.cl",
                "anios_experiencia": 9,
                "orden": 1
            },
            {
                "email": "rodrigo.barbero@demobarberclub.cl",
                "nombre": "Rodrigo",
                "apellido": "Valenzuela",
                "nombre_profesional": "Rodrigo Valenzuela",
                "slug": "rodrigo-valenzuela",
                "sucursales": [suc_prov, suc_vita],
                "foto_estatica_demo": "img/barberos/rodrigo_valenzuela.webp",
                "especialidad_principal": "Senior Barber • Afeitado Tradicional y Barba",
                "bio": "Maestro de la navaja clásica y los rituales con toalla caliente infusionada en eucalipto y mentol. Calma y precisión absoluta.",
                "instagram": "rodrigo.cuts",
                "anios_experiencia": 8,
                "orden": 2
            },
            {
                "email": "ignacio.barbero@demobarberclub.cl",
                "nombre": "Ignacio",
                "apellido": "Castro",
                "nombre_profesional": "Ignacio Castro",
                "slug": "ignacio-castro",
                "sucursales": [suc_condes, suc_vita],
                "foto_estatica_demo": "img/barberos/ignacio_castro.webp",
                "especialidad_principal": "Stylist Barber • Tijera Clásica y Visagismo",
                "bio": "Apasionado por las proporciones faciales. Asesor de imagen capilar especializado en cortes formales y ejecutivos a tijera pura.",
                "instagram": "ignacio.visagismo",
                "anios_experiencia": 7,
                "orden": 3
            },
            {
                "email": "diego.barbero@demobarberclub.cl",
                "nombre": "Diego",
                "apellido": "Morales",
                "nombre_profesional": "Diego Morales",
                "slug": "diego-morales",
                "sucursales": [suc_prov, suc_condes],
                "foto_estatica_demo": "img/barberos/diego_morales.webp",
                "especialidad_principal": "Barber Artist • Perfilados y Diseños de Precisión",
                "bio": "Especialista en transiciones modernas, Skin Fade, Taper y delineados con navaja japonesa feather.",
                "instagram": "diego.morales.fade",
                "anios_experiencia": 6,
                "orden": 4
            },
            {
                "email": "camilo.barbero@demobarberclub.cl",
                "nombre": "Camilo",
                "apellido": "Fuentes",
                "nombre_profesional": "Camilo Fuentes",
                "slug": "camilo-fuentes",
                "sucursales": [suc_vita, suc_prov],
                "foto_estatica_demo": "img/barberos/camilo_fuentes.webp",
                "especialidad_principal": "Grooming Specialist • Cuidados y Tratamientos Capilares",
                "bio": "Enfoque holístico en salud capilar, exfoliaciones dérmicas para cuero cabelludo y nutrición profunda de la fibra capilar.",
                "instagram": "camilo.grooming",
                "anios_experiencia": 5,
                "orden": 5
            }
        ]

        barbero_objs = []
        for b_data in barberos_datos:
            if "usuario" in b_data:
                b_user = b_data["usuario"]
            else:
                b_user, _ = Usuario.objects.get_or_create(
                    email=b_data["email"],
                    defaults={
                        "username": b_data["email"],
                        "first_name": b_data["nombre"],
                        "last_name": b_data["apellido"],
                        "rol": Usuario.Rol.BARBERO
                    }
                )
                b_user.set_password("barbero123")
                b_user.save()

            barb, _ = Barbero.objects.update_or_create(
                slug=b_data["slug"],
                defaults={
                    "usuario": b_user,
                    "nombre_profesional": b_data["nombre_profesional"],
                    "foto_estatica_demo": b_data["foto_estatica_demo"],
                    "especialidad_principal": b_data["especialidad_principal"],
                    "bio": b_data["bio"],
                    "instagram": b_data["instagram"],
                    "anios_experiencia": b_data["anios_experiencia"],
                    "orden": b_data["orden"],
                    "activo": True
                }
            )
            barb.sucursales.set(b_data["sucursales"])
            barbero_objs.append(barb)
        self.stdout.write(self.style.SUCCESS("[OK] 5 Barberos profesionales creados y asignados a sucursales."))

        # 5. Horarios de Trabajo por Barbero y Sucursal
        # Para garantizar cobertura completa en todas las sedes de Lunes a Sábado (10:00 - 20:00),
        # asignamos turnos semanales equilibrados sin que ningún barbero se solape en dos sedes el mismo día.
        HorarioTrabajo.objects.all().delete()
        
        # Mapeo de barberos por slug a sus turnos semanales por sucursal
        dias_lun_mie_vie = [DiaSemana.LUNES, DiaSemana.MIERCOLES, DiaSemana.VIERNES]
        dias_mar_jue_sab = [DiaSemana.MARTES, DiaSemana.JUEVES, DiaSemana.SABADO]

        distribucion_turnos = {
            "matias-silva": [
                (suc_prov, dias_lun_mie_vie),
                (suc_condes, dias_mar_jue_sab)
            ],
            "rodrigo-valenzuela": [
                (suc_prov, dias_lun_mie_vie),
                (suc_vita, dias_mar_jue_sab)
            ],
            "ignacio-castro": [
                (suc_condes, dias_lun_mie_vie),
                (suc_vita, dias_mar_jue_sab)
            ],
            "diego-morales": [
                (suc_condes, dias_lun_mie_vie),
                (suc_prov, dias_mar_jue_sab)
            ],
            "camilo-fuentes": [
                (suc_vita, dias_lun_mie_vie),
                (suc_prov, dias_mar_jue_sab)
            ],
        }

        for barb in barbero_objs:
            if barb.slug in distribucion_turnos:
                for suc_turno, dias_asignados in distribucion_turnos[barb.slug]:
                    for d in dias_asignados:
                        HorarioTrabajo.objects.create(
                            barbero=barb,
                            sucursal=suc_turno,
                            dia_semana=d,
                            hora_inicio=time(10, 0),
                            hora_fin=time(20, 0),
                            pausa_inicio=time(14, 0),
                            pausa_fin=time(15, 0),
                            activo=True
                        )
            else:
                for suc_del_barbero in barb.sucursales.all():
                    for d in [DiaSemana.LUNES, DiaSemana.MARTES, DiaSemana.MIERCOLES, DiaSemana.JUEVES, DiaSemana.VIERNES, DiaSemana.SABADO]:
                        HorarioTrabajo.objects.create(
                            barbero=barb,
                            sucursal=suc_del_barbero,
                            dia_semana=d,
                            hora_inicio=time(10, 0),
                            hora_fin=time(20, 0),
                            pausa_inicio=time(14, 0),
                            pausa_fin=time(15, 0),
                            activo=True
                        )
        self.stdout.write(self.style.SUCCESS("[OK] Horarios laborales semanales asignados equitativamente."))

        # 5.1 Bloqueos de Agenda (Vacaciones, Permisos, Feriado y Recurrente)
        Bloqueo.objects.all().delete()
        ahora_demo = timezone.now()

        # 1. Vacaciones de Matías Silva (en 6 días)
        Bloqueo.objects.create(
            barbero=barbero_objs[0],
            sucursal=suc_prov,
            fecha_inicio=ahora_demo + timedelta(days=6),
            fecha_fin=ahora_demo + timedelta(days=9),
            tipo=Bloqueo.TipoBloqueo.VACACIONES,
            motivo="Vacaciones familiares programadas",
            todo_el_dia=True
        )

        # 2. Permiso Personal de Rodrigo Valenzuela (en 2 días, por la tarde)
        fecha_permiso = (ahora_demo + timedelta(days=2)).date()
        Bloqueo.objects.create(
            barbero=barbero_objs[1],
            sucursal=suc_prov,
            fecha_inicio=timezone.make_aware(datetime.combine(fecha_permiso, time(15, 0))),
            fecha_fin=timezone.make_aware(datetime.combine(fecha_permiso, time(17, 30))),
            tipo=Bloqueo.TipoBloqueo.PERMISO,
            motivo="Trámite personal / médico",
            todo_el_dia=False
        )

        # 3. Reunión semanal recurrente todos los Lunes en Providencia (09:30 - 10:30)
        Bloqueo.objects.create(
            barbero=None, # Toda la sucursal
            sucursal=suc_prov,
            fecha_inicio=timezone.make_aware(datetime.combine(ahora_demo.date(), time(9, 30))),
            fecha_fin=timezone.make_aware(datetime.combine(ahora_demo.date(), time(10, 30))),
            tipo=Bloqueo.TipoBloqueo.BLOQUEO_MANUAL,
            motivo="Alineación semanal y calibración de instrumental",
            todo_el_dia=False,
            es_recurrente=True,
            dia_semana_recurrente=DiaSemana.LUNES
        )
        self.stdout.write(self.style.SUCCESS("[OK] Bloqueos de agenda (vacaciones, permiso, recurrente) generados."))

        # 6. Categorías y 6 Servicios de Catálogo
        cat_corte, _ = CategoriaServicio.objects.get_or_create(nombre="Cortes de Cabello", defaults={"orden": 1})
        cat_barba, _ = CategoriaServicio.objects.get_or_create(nombre="Barba & Afeitado", defaults={"orden": 2})
        cat_combos, _ = CategoriaServicio.objects.get_or_create(nombre="Combos Signature", defaults={"orden": 3})
        cat_spa, _ = CategoriaServicio.objects.get_or_create(nombre="Cuidado & Spa Capilar", defaults={"orden": 4})

        servicios_datos = [
            {
                "nombre": "Corte Clásico & Fade",
                "slug": "corte-clasico-fade",
                "categoria": cat_corte,
                "duracion_minutos": 45,
                "precio": 18000,
                "etiqueta": "Más Solicitado",
                "es_destacado": True,
                "foto_estatica_demo": "img/servicios/corte_clasico.webp",
                "descripcion": "Diagnóstico de visagismo según forma de rostro, lavado con masaje capilar, corte degradado a elección (Low, Mid o High Fade) y peinado con pomada premium.",
                "orden": 1
            },
            {
                "nombre": "Afeitado Tradicional",
                "slug": "afeitado-tradicional",
                "categoria": cat_barba,
                "duracion_minutos": 40,
                "precio": 16000,
                "etiqueta": "Ritual Clásico",
                "es_destacado": True,
                "foto_estatica_demo": "img/servicios/afeitado_tradicional.webp",
                "descripcion": "El ritual por excelencia: toallas humeantes al eucalipto, espuma caliente batida con brocha de tejón, navaja clásica y sellado con toalla fría y aftershave.",
                "orden": 2
            },
            {
                "nombre": "Perfilado y Ritual de Barba",
                "slug": "perfilado-ritual-barba",
                "categoria": cat_barba,
                "duracion_minutos": 35,
                "precio": 14000,
                "etiqueta": "Cuidado Barba",
                "es_destacado": True,
                "foto_estatica_demo": "img/servicios/perfilado_barba.webp",
                "descripcion": "Recorte simétrico con tijera y máquina, delineado nítido de contornos con navaja, toalla caliente y nutrición con aceite de cedro y argán.",
                "orden": 3
            },
            {
                "nombre": "Combo Signature: Corte + Barba",
                "slug": "combo-signature-corte-barba",
                "categoria": cat_combos,
                "duracion_minutos": 75,
                "precio": 28000,
                "etiqueta": "Experiencia Completa",
                "es_destacado": True,
                "foto_estatica_demo": "img/servicios/combo_corte_barba.webp",
                "descripcion": "Nuestra experiencia cumbre: corte completo a tu medida, afeitado o perfilado de barba con toalla caliente, masaje facial y bebida de cortesía.",
                "orden": 4
            },
            {
                "nombre": "Corte Niño & Joven",
                "slug": "corte-nino-joven",
                "categoria": cat_corte,
                "duracion_minutos": 35,
                "precio": 14000,
                "etiqueta": "Junior",
                "es_destacado": False,
                "foto_estatica_demo": "img/servicios/corte_nino.webp",
                "descripcion": "Atención paciente, amena y con técnica contemporánea para niños y jóvenes hasta 14 años.",
                "orden": 5
            },
            {
                "nombre": "Tratamiento Detox & Masaje Capilar",
                "slug": "tratamiento-detox-capilar",
                "categoria": cat_spa,
                "duracion_minutos": 45,
                "precio": 22000,
                "etiqueta": "Spa Masculino",
                "es_destacado": False,
                "foto_estatica_demo": "img/servicios/tratamiento_capilar.webp",
                "descripcion": "Exfoliación profunda del cuero cabelludo con sales minerales, lavado purificante de mentol y 15 minutos de masaje craneal relajante.",
                "orden": 6
            }
        ]

        servicio_objs = []
        for s_data in servicios_datos:
            srv, _ = Servicio.objects.update_or_create(
                slug=s_data["slug"],
                defaults=s_data
            )
            servicio_objs.append(srv)

            # Asignar a todas las sucursales y barberos de forma predeterminada
            for suc in sucursal_objs:
                ServicioSucursal.objects.get_or_create(servicio=srv, sucursal=suc, defaults={"disponible": True})
            for barb in barbero_objs:
                ServicioBarbero.objects.get_or_create(servicio=srv, barbero=barb, defaults={"disponible": True})

        self.stdout.write(self.style.SUCCESS("[OK] 6 Servicios creados y sincronizados con sucursales y barberos."))

        # 7. Categorías y 8 Productos para la Tienda
        cat_p_peinado, _ = CategoriaProducto.objects.get_or_create(nombre="Fijación & Peinado", defaults={"orden": 1})
        cat_p_barba, _ = CategoriaProducto.objects.get_or_create(nombre="Cuidado de Barba", defaults={"orden": 2})
        cat_p_afeitado, _ = CategoriaProducto.objects.get_or_create(nombre="Afeitado Tradicional", defaults={"orden": 3})
        cat_p_accesorios, _ = CategoriaProducto.objects.get_or_create(nombre="Accesorios & Fragancias", defaults={"orden": 4})

        productos_datos = [
            {
                "nombre": "Pomada Fijación Mate 100ml",
                "slug": "pomada-fijacion-mate-100ml",
                "categoria": cat_p_peinado,
                "precio": 14990,
                "stock": 24,
                "destacado": True,
                "foto_estatica_demo": "img/productos/pomada_mate.webp",
                "descripcion": "Fijación fuerte y maleable con textura mate sin residuos grasos. Base al agua de fácil lavado. Fragancia masculina a madera de cedro."
            },
            {
                "nombre": "Aceite Esencial para Barba 50ml",
                "slug": "aceite-esencial-barba-50ml",
                "categoria": cat_p_barba,
                "precio": 12990,
                "stock": 18,
                "destacado": True,
                "foto_estatica_demo": "img/productos/aceite_barba.webp",
                "descripcion": "Combinación artesanal de aceite de argán marroquí, jojoba dorada y vitamina E. Suaviza la barba más rebelde e hidrata la piel subyacente."
            },
            {
                "nombre": "Bálsamo Aftershave Calmante 120ml",
                "slug": "balsamo-aftershave-calmante-120ml",
                "categoria": cat_p_afeitado,
                "precio": 11990,
                "stock": 15,
                "destacado": True,
                "foto_estatica_demo": "img/productos/balsamo_aftershave.webp",
                "descripcion": "Fórmula calmante instantánea libre de alcohol con aloe vera puro, hamamelis y extracto de manzanilla. Evita la irritación y los cortes."
            },
            {
                "nombre": "Shampoo Fortificante Capilar & Barba 250ml",
                "slug": "shampoo-fortificante-capilar-barba-250ml",
                "categoria": cat_p_peinado,
                "precio": 13990,
                "stock": 12,
                "destacado": True,
                "foto_estatica_demo": "img/productos/shampoo_fortificante.webp",
                "descripcion": "Limpieza profunda con aceite de árbol de té y mentol revitalizante. Fortalece el folículo capilar y previene la caída prematura."
            },
            {
                "nombre": "Cera Clásica Alto Brillo 100ml",
                "slug": "cera-clasica-alto-brillo-100ml",
                "categoria": cat_p_peinado,
                "precio": 14990,
                "stock": 8,
                "destacado": False,
                "foto_estatica_demo": "img/productos/cera_brillo.webp",
                "descripcion": "Para amantes del estilo pompadour y peinados retro. Proporciona brillo radiante y fijación flexible durante toda la jornada."
            },
            {
                "nombre": "Cepillo de Cerda Natural de Jabalí",
                "slug": "cepillo-cerda-natural-jabali",
                "categoria": cat_p_accesorios,
                "precio": 9990,
                "stock": 10,
                "destacado": False,
                "foto_estatica_demo": "img/productos/cepillo_cerda.webp",
                "descripcion": "Madera de peral noble tratada y cerdas naturales de jabalí que distribuyen uniformemente los aceites naturales de la barba."
            },
            {
                "nombre": "Peine Antiestático de Fibra de Carbono",
                "slug": "peine-antiestatico-fibra-carbono",
                "categoria": cat_p_accesorios,
                "precio": 7990,
                "stock": 3,  # En alerta de stock bajo
                "destacado": False,
                "foto_estatica_demo": "img/productos/peine_carbono.webp",
                "descripcion": "Doble espaciado de dientes, resistente al calor y ultra ligero. Elimina el encrespamiento y la electricidad estática."
            },
            {
                "nombre": "Eau de Parfum Tabaco & Vainilla 100ml",
                "slug": "eau-de-parfum-tabaco-vainilla-100ml",
                "categoria": cat_p_accesorios,
                "precio": 29990,
                "stock": 6,
                "destacado": True,
                "foto_estatica_demo": "img/productos/colonia_tabaco_vainilla.webp",
                "descripcion": "Fragancia de autor exclusiva de Demo Barber Club. Notas cálidas de hoja de tabaco, flor de cacao, haba tonka y vainilla bourbon."
            }
        ]

        producto_objs = []
        for p_data in productos_datos:
            prod, _ = Producto.objects.update_or_create(
                slug=p_data["slug"],
                defaults=p_data
            )
            producto_objs.append(prod)
        self.stdout.write(self.style.SUCCESS("[OK] 8 Productos de barberia cargados en catalogo."))

        # 7.1 Stock por Sucursal y Movimientos de Auditoría Inmutables
        StockSucursal.objects.all().delete()
        MovimientoStock.objects.all().delete()

        for prod in producto_objs:
            # Sede Providencia: Stock saludable salvo el peine en nivel bajo (3 uds)
            cant_prov = 3 if prod.slug == "peine-antiestatico-fibra-carbono" else random.choice([12, 15, 20])
            StockSucursal.objects.create(
                producto=prod,
                sucursal=suc_prov,
                cantidad=cant_prov,
                stock_minimo_alerta=5
            )
            MovimientoStock.objects.create(
                tipo=MovimientoStock.Tipo.ENTRADA,
                producto=prod,
                sucursal=suc_prov,
                cantidad=cant_prov,
                stock_resultante=cant_prov,
                usuario=admin_prov,
                motivo="Reposición inicial de inventario demo"
            )

            # Sede Las Condes: Stock saludable salvo pomada mate en nivel crítico (2 uds)
            cant_condes = 2 if prod.slug == "pomada-mate-fijacion-fuerte-100g" else random.choice([8, 14, 18])
            StockSucursal.objects.create(
                producto=prod,
                sucursal=suc_condes,
                cantidad=cant_condes,
                stock_minimo_alerta=5
            )
            MovimientoStock.objects.create(
                tipo=MovimientoStock.Tipo.ENTRADA,
                producto=prod,
                sucursal=suc_condes,
                cantidad=cant_condes,
                stock_resultante=cant_condes,
                usuario=admin_condes,
                motivo="Carga inicial de existencias para apertura"
            )

            # Sede Vitacura: Un producto agotado (0 uds) para probar alerta de quiebre de stock
            cant_vita = 0 if prod.slug == "shampoo-mentolado-vigorizante-250ml" else random.choice([10, 16, 22])
            StockSucursal.objects.create(
                producto=prod,
                sucursal=suc_vita,
                cantidad=cant_vita,
                stock_minimo_alerta=5
            )
            MovimientoStock.objects.create(
                tipo=MovimientoStock.Tipo.ENTRADA,
                producto=prod,
                sucursal=suc_vita,
                cantidad=cant_vita if cant_vita > 0 else 5,
                stock_resultante=cant_vita,
                usuario=admin_vita,
                motivo="Inventario inicial"
            )
            if cant_vita == 0:
                MovimientoStock.objects.create(
                    tipo=MovimientoStock.Tipo.SALIDA,
                    producto=prod,
                    sucursal=suc_vita,
                    cantidad=5,
                    stock_resultante=0,
                    usuario=admin_vita,
                    motivo="Quiebre de stock por venta rápida en local"
                )

            # Actualizar stock total agregado del producto
            prod.stock = cant_prov + cant_condes + cant_vita
            prod.sku = f"SKU-{prod.slug[:8].upper()}-{prod.id}"
            prod.precio_costo = int(prod.precio * 0.45)
            prod.save(update_fields=['stock', 'sku', 'precio_costo'])

        # Registrar un traslado de ejemplo entre Providencia y Las Condes
        prod_traslado = producto_objs[0]
        registrar_movimiento_stock(
            producto=prod_traslado,
            sucursal=suc_prov,
            tipo=MovimientoStock.Tipo.TRASLADO,
            cantidad=3,
            usuario=admin_user,
            motivo="Traslado preventivo para abastecer fin de semana",
            sucursal_destino=suc_condes
        )
        self.stdout.write(self.style.SUCCESS("[OK] Stock por sucursal y movimientos históricos de auditoría creados."))

        # 8. Testimonios de Clientes
        testimonios = [
            ("Alejandro Concha", "Empresario", 5, "La mejor experiencia de barberia en Santiago. La puntualidad de Matias y el ritual de la toalla caliente son insuperables. 100% recomendado.", "Combo Signature: Corte + Barba"),
            ("Gonzalo Perez", "Arquitecto", 5, "El nivel de detalle en el degradado es perfecto. Las instalaciones en Las Condes tienen una vibra increible y el cafe es de primera categoria.", "Corte Clasico & Fade"),
            ("Esteban Moraga", "Director Creativo", 5, "Llevo dos anos atendiendome con Rodrigo en Vitacura. Nadie perfila la barba con tanta precision en Chile. El sistema de agendamiento online es super rapido.", "Perfilado y Ritual de Barba"),
            ("Marcelo Henriquez", "Consultor TI", 5, "Muy comodo poder agendar desde el celular sin llamadas. La atencion de Ignacio fue impecable, me asesoro sobre que corte me favorecia segun mi tipo de rostro.", "Corte Clasico & Fade"),
        ]
        Testimonio.objects.all().delete()
        for nom, ocu, cal, com, srv in testimonios:
            Testimonio.objects.create(
                cliente_nombre=nom,
                cliente_ocupacion=ocu,
                calificacion=cal,
                comentario=com,
                servicio_mencionado=srv,
                activo=True
            )
        self.stdout.write(self.style.SUCCESS("[OK] Testimonios de clientes agregados."))

        # 9. Preguntas Frecuentes (FAQ)
        faqs = [
            ("¿Es necesario agendar con anticipación o atienden por orden de llegada?",
             "Recomendamos siempre agendar a través de nuestro sitio web para asegurar tu espacio sin esperas. Si vienes de paso, te atenderemos según disponibilidad del momento en la sucursal elegida.", "Reservas", 1),
            ("¿Con cuánto tiempo de anticipación puedo cancelar o reprogramar?",
             "Puedes cancelar o reprogramar tu cita sin ningún costo hasta con 4 horas de anticipación desde 'Mi Cuenta' o a través del enlace de confirmación que llega a tu correo.", "Políticas", 2),
            ("¿Qué incluye el servicio de Afeitado Tradicional?",
             "Incluye aplicación de aceites preshave botánicos, 2 sesiones de toallas calientes humeantes infusionadas en mentol, afeitado a navaja tradicional con hoja nueva desechable, toalla fría para cerrar poros y bálsamo aftershave calmante.", "Servicios", 3),
            ("¿Tienen estacionamiento en sus sucursales?",
             "Sí, nuestras tres sucursales (Providencia, Las Condes y Vitacura) cuentan con convenios de estacionamiento gratuito o con tarifa preferencial para clientes del club.", "Ubicaciones", 4),
            ("¿Cuáles son los medios de pago aceptados?",
             "Aceptamos tarjetas de débito, crédito (Visa, Mastercard, Amex), transferencia bancaria y efectivo directamente en el local al momento de tu atención.", "Pagos", 5),
        ]
        PreguntaFrecuente.objects.all().delete()
        for q, a, cat, ord in faqs:
            PreguntaFrecuente.objects.create(
                pregunta=q,
                respuesta=a,
                categoria=cat,
                orden=ord,
                activa=True
            )
        self.stdout.write(self.style.SUCCESS("[OK] Preguntas Frecuentes (FAQ) configuradas."))

        # 10. Galería de Resultados (con antes/después)
        galeria_items = [
            ("Skin Fade de Alta Precision", "Cortes", "img/galeria/galeria_1.webp", True, 1),
            ("Barba Esculpida & Bigote", "Barba", "img/galeria/galeria_2.webp", False, 2),
            ("Corte Pompadour Texturizado", "Estilos", "img/galeria/galeria_3.webp", False, 3),
            ("Ritual Toalla Caliente", "Experiencia", "img/galeria/galeria_4.webp", False, 4),
            ("Taper Fade Clasico", "Cortes", "img/galeria/galeria_5.webp", False, 5),
            ("Diseno de Barba y Cuello", "Barba", "img/galeria/galeria_6.webp", True, 6),
        ]
        ImagenGaleria.objects.all().delete()
        for tit, cat, ruta, ad, ord in galeria_items:
            ImagenGaleria.objects.create(
                titulo=tit,
                categoria=cat,
                foto_estatica_demo=ruta,
                es_antes_despues=ad,
                orden=ord,
                activa=True
            )
        self.stdout.write(self.style.SUCCESS("[OK] Galeria de resultados configurada."))

        # 11. Artículos de Blog
        articulos = [
            {
                "titulo": "Guía Definitiva para el Cuidado y Crecimiento de tu Barba",
                "slug": "guia-definitiva-cuidado-barba",
                "extracto": "Descubre los secretos de los maestros barberos para mantener una barba densa, hidratada y libre de picazón usando aceites esenciales y cepillado correcto.",
                "contenido": "<p>Mantener una barba frondosa y con presencia requiere disciplina y los productos adecuados. El primer error común es lavar la barba con jabón corporal, lo que elimina los aceites naturales y reseca la piel inferior.</p><p>Te recomendamos aplicar diariamente de 3 a 5 gotas de aceite con base de argán y jojoba, seguido de un peinado con cerdas naturales para estimular el flujo sanguíneo y orientar el crecimiento.</p>",
                "foto_estatica_demo": "img/blog/guia_cuidado_barba.webp",
                "tiempo_lectura_minutos": 4
            },
            {
                "titulo": "¿Qué Tipo de Fade Favorece más la Forma de tu Rostro?",
                "slug": "que-tipo-fade-favorece-forma-rostro",
                "extracto": "Low Fade, Mid Fade o High Fade: el visagismo capilar te enseña cuál resalta mejor tus mandíbulas y estiliza tus facciones.",
                "contenido": "<p>El visagismo es la ciencia estética que estudia las proporciones de tu rostro para potenciar tus mejores ángulos. Para rostros redondos, un High Fade con volumen superior genera un efecto estilizador inmediato.</p><p>En cambio, para rostros alargados o cuadrados, un Taper Fade sutil o un Low Fade mantiene la armonía sin exagerar la altura.</p>",
                "foto_estatica_demo": "img/blog/fade_segun_tu_rostro.webp",
                "tiempo_lectura_minutos": 5
            },
            {
                "titulo": "El Secreto del Afeitado Tradicional con Toalla Caliente",
                "slug": "secreto-afeitado-tradicional-toalla-caliente",
                "extracto": "Por qué este ritual de más de un siglo sigue siendo el preferido por los caballeros que buscan una piel impecable sin irritación.",
                "contenido": "<p>El calor del vapor abre los poros y suaviza la queratina del vello facial hasta en un 60%, permitiendo que el filo de la navaja se deslice sin fricción ni tirones.</p><p>Combinado con toallas aromatizadas con mentol y eucalipto, el afeitado clásico trasciende la estética: es un oasis de relajación mental en medio del ritmo acelerado de la ciudad.</p>",
                "foto_estatica_demo": "img/blog/ritual_afeitado_clasico.webp",
                "tiempo_lectura_minutos": 3
            }
        ]
        EntradaBlog.objects.all().delete()
        for art in articulos:
            EntradaBlog.objects.create(
                titulo=art["titulo"],
                slug=art["slug"],
                extracto=art["extracto"],
                contenido=art["contenido"],
                foto_estatica_demo=art["foto_estatica_demo"],
                tiempo_lectura_minutos=art["tiempo_lectura_minutos"],
                publicado=True
            )
        self.stdout.write(self.style.SUCCESS("[OK] Entradas de blog publicadas."))

        # 12. Reservas de Demostración para KPIs y Gráficos del Dashboard
        Reserva.objects.all().delete()
        ahora = timezone.now()
        # Generar reservas pasadas (últimos 14 días), de hoy y futuras (próximos 7 días)
        estados_posibles = [
            Reserva.Estado.COMPLETADA,
            Reserva.Estado.CONFIRMADA,
            Reserva.Estado.PENDIENTE,
            Reserva.Estado.CANCELADA
        ]

        total_reservas = 0
        # Reservas históricas de los últimos 14 días
        for dia_offset in range(-14, 8):
            fecha_base = (ahora + timedelta(days=dia_offset)).date()
            # Cantidad de reservas por día (entre 2 y 5)
            num_citas = random.randint(2, 5)
            for _ in range(num_citas):
                barb = random.choice(barbero_objs)
                sucursales_disp = list(barb.sucursales.all())
                suc = random.choice(sucursales_disp)
                srv = random.choice(servicio_objs)
                cli = random.choice(cliente_objs)

                hora_azar = random.choice([10, 11, 12, 13, 15, 16, 17, 18, 19])
                minuto_azar = random.choice([0, 30])
                dt_inicio = timezone.make_aware(datetime.combine(fecha_base, time(hora_azar, minuto_azar)))
                dt_fin = dt_inicio + timedelta(minutes=srv.duracion_minutos)

                if dia_offset < 0:
                    estado = Reserva.Estado.COMPLETADA if random.random() > 0.15 else Reserva.Estado.CANCELADA
                elif dia_offset == 0:
                    estado = Reserva.Estado.CONFIRMADA
                else:
                    estado = Reserva.Estado.CONFIRMADA if random.random() > 0.2 else Reserva.Estado.PENDIENTE

                Reserva.objects.create(
                    cliente=cli,
                    cliente_nombre=cli.get_full_name() or cli.email,
                    cliente_email=cli.email,
                    cliente_telefono=cli.telefono or "+56 9 9999 8888",
                    sucursal=suc,
                    barbero=barb,
                    servicio=srv,
                    fecha_hora_inicio=dt_inicio,
                    fecha_hora_fin=dt_fin,
                    precio=srv.precio,
                    estado=estado,
                    notas="Cliente frecuente - Demostracion comercial"
                )
                total_reservas += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] {total_reservas} Reservas de ejemplo generadas para dashboard."))

        # 13. Pedidos de Productos de Ejemplo
        Pedido.objects.all().delete()
        ItemPedido.objects.all().delete()
        total_pedidos = 0
        for dia_offset in range(-10, 2):
            fecha_compra = ahora + timedelta(days=dia_offset)
            cli = random.choice(cliente_objs)
            suc = random.choice(sucursal_objs)
            ped = Pedido(
                cliente=cli,
                cliente_nombre=cli.get_full_name() or cli.email,
                cliente_email=cli.email,
                cliente_telefono=cli.telefono or "+56 9 9999 8888",
                sucursal_retiro=suc,
                metodo_pago=Pedido.MetodoPago.LOCAL,
                estado=Pedido.Estado.PAGADO if dia_offset < 0 else Pedido.Estado.LISTO_PARA_RETIRO,
                total=0
            )
            ped.save()
            ped.creado_el = fecha_compra
            ped.save(update_fields=['creado_el'])

            # Agregar 1 o 2 items
            prods_seleccionados = random.sample(producto_objs, k=random.randint(1, 2))
            total_calc = 0
            for prod in prods_seleccionados:
                cant = random.randint(1, 2)
                sub = cant * prod.precio
                total_calc += sub
                ItemPedido.objects.create(
                    pedido=ped,
                    producto=prod,
                    cantidad=cant,
                    precio_unitario=prod.precio,
                    subtotal=sub
                )
            ped.total = total_calc
            ped.save(update_fields=['total'])
            total_pedidos += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] {total_pedidos} Pedidos de tienda creados con items."))
        self.stdout.write(self.style.SUCCESS("\n[EXITO] Carga de demo finalizada exitosamente. Todo listo para pruebas comerciales."))
