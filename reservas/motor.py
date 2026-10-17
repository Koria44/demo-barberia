"""
Motor de Cálculo de Disponibilidad y Prevención de Doble Reserva
para Demo Barber Club.
"""
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings

from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio, ServicioBarbero, ServicioSucursal
from reservas.models import HorarioTrabajo, Bloqueo, Reserva
from contenido.models import ConfiguracionSitio


def obtener_barberos_elegibles(sucursal, servicio=None):
    """
    Retorna la lista de barberos activos asignados a una sucursal
    que además realicen el servicio indicado (si se especifica).
    """
    barberos = Barbero.objects.filter(sucursales=sucursal, activo=True)
    if servicio:
        # Filtrar si existe restricción explícita en ServicioBarbero
        barberos_excluidos = ServicioBarbero.objects.filter(
            servicio=servicio, disponible=False
        ).values_list('barbero_id', flat=True)
        barberos = barberos.exclude(id__in=barberos_excluidos)
    return barberos


def calcular_horarios_disponibles(sucursal, servicio, fecha_consulta, barbero=None):
    """
    Calcula los intervalos de hora disponibles para una fecha específica.
    Tiene en cuenta:
    - Jornada laboral del barbero en la sucursal (HorarioTrabajo)
    - Pausa de colación
    - Bloqueos de agenda (vacaciones, permisos, feriados)
    - Citas existentes del barbero en CUALQUIER sucursal (evita doble agenda)
    - Duración del servicio y tiempo de descanso configurable
    - Anticipación mínima en horas (no ofrecer citas en el pasado inmediato)
    """
    config = ConfiguracionSitio.get_solo()
    ahora = timezone.now()

    # Validar límite máximo de días a futuro
    limite_futuro = (ahora + timedelta(days=config.dias_maximos_futuro)).date()
    if fecha_consulta > limite_futuro or fecha_consulta < ahora.date():
        return []

    dia_semana = fecha_consulta.weekday()
    duracion = servicio.duracion_minutos
    descanso = config.tiempo_descanso_entre_citas_minutos
    duracion_total = timedelta(minutes=duracion + descanso)

    # Determinar qué barberos evaluar
    if barbero:
        barberos_a_evaluar = [barbero]
    else:
        barberos_a_evaluar = list(obtener_barberos_elegibles(sucursal, servicio))

    if not barberos_a_evaluar:
        return []

    # Mapa de slots horarios -> lista de barberos libres en ese slot
    slots_disponibles = {}

    for b in barberos_a_evaluar:
        # 1. Turno laboral del barbero en esta sucursal para este día
        turnos = HorarioTrabajo.objects.filter(
            barbero=b,
            sucursal=sucursal,
            dia_semana=dia_semana,
            activo=True
        )
        if not turnos.exists():
            continue

        # 2. Reservas activas del barbero en este día (en CUALQUIER sucursal)
        reservas_existentes = Reserva.objects.filter(
            barbero=b,
            fecha_hora_inicio__date=fecha_consulta,
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA]
        ).values('fecha_hora_inicio', 'fecha_hora_fin')

        # 3. Bloqueos que afecten al barbero o a la sucursal en esta fecha
        bloqueos = Bloqueo.objects.filter(
            Q(barbero=b) | Q(sucursal=sucursal, barbero__isnull=True),
            fecha_inicio__date__lte=fecha_consulta,
            fecha_fin__date__gte=fecha_consulta
        )

        for turno in turnos:
            hora_actual_dt = datetime.combine(fecha_consulta, turno.hora_inicio)
            hora_fin_dt = datetime.combine(fecha_consulta, turno.hora_fin)

            # Generar intervalos cada 30 minutos
            intervalo_paso = timedelta(minutes=30)
            while hora_actual_dt + timedelta(minutes=duracion) <= hora_fin_dt:
                slot_inicio = timezone.make_aware(hora_actual_dt)
                slot_fin = slot_inicio + timedelta(minutes=duracion)

                # Validar que no esté en el pasado ni con menos de X horas de anticipación
                minimo_permitido = ahora + timedelta(hours=config.horas_minimas_anticipacion)
                if slot_inicio < minimo_permitido:
                    hora_actual_dt += intervalo_paso
                    continue

                # Validar colación / pausa
                choca_pausa = False
                if turno.pausa_inicio and turno.pausa_fin:
                    p_inicio = timezone.make_aware(datetime.combine(fecha_consulta, turno.pausa_inicio))
                    p_fin = timezone.make_aware(datetime.combine(fecha_consulta, turno.pausa_fin))
                    if slot_inicio < p_fin and slot_fin > p_inicio:
                        choca_pausa = True

                if choca_pausa:
                    hora_actual_dt += intervalo_paso
                    continue

                # Validar bloqueos
                choca_bloqueo = False
                for bloq in bloqueos:
                    if slot_inicio < bloq.fecha_fin and slot_fin > bloq.fecha_inicio:
                        choca_bloqueo = True
                        break

                if choca_bloqueo:
                    hora_actual_dt += intervalo_paso
                    continue

                # Validar citas existentes (incluyendo descanso entre citas)
                choca_reserva = False
                for res in reservas_existentes:
                    res_ini = res['fecha_hora_inicio']
                    res_fin = res['fecha_hora_fin'] + timedelta(minutes=descanso)
                    if slot_inicio < res_fin and (slot_fin + timedelta(minutes=descanso)) > res_ini:
                        choca_reserva = True
                        break

                if not choca_reserva:
                    hora_str = slot_inicio.strftime('%H:%M')
                    if hora_str not in slots_disponibles:
                        slots_disponibles[hora_str] = []
                    slots_disponibles[hora_str].append(b)

                hora_actual_dt += intervalo_paso

    # Ordenar y dar formato a los horarios
    resultado = []
    for h in sorted(slots_disponibles.keys()):
        barberos_libres = slots_disponibles[h]
        resultado.append({
            'hora': h,
            'barberos_count': len(barberos_libres),
            'barberos_ids': [b.id for b in barberos_libres],
            'barberos_nombres': [b.nombre_profesional for b in barberos_libres]
        })

    return resultado


def asignar_barbero_menor_carga(sucursal, servicio, slot_inicio, slot_fin):
    """
    Si el cliente eligió 'Cualquier barbero', selecciona automáticamente
    al barbero elegible libre que tenga la menor cantidad de citas ese día.
    """
    config = ConfiguracionSitio.get_solo()
    descanso = timedelta(minutes=config.tiempo_descanso_entre_citas_minutos)
    fecha_consulta = slot_inicio.date()

    barberos_elegibles = obtener_barberos_elegibles(sucursal, servicio)
    barberos_candidatos = []

    for b in barberos_elegibles:
        # Verificar turno
        turno = HorarioTrabajo.objects.filter(
            barbero=b, sucursal=sucursal, dia_semana=fecha_consulta.weekday(), activo=True
        ).first()
        if not turno:
            continue

        # Verificar que encaje en el horario laboral
        t_ini = timezone.make_aware(datetime.combine(fecha_consulta, turno.hora_inicio))
        t_fin = timezone.make_aware(datetime.combine(fecha_consulta, turno.hora_fin))
        if slot_inicio < t_ini or slot_fin > t_fin:
            continue

        # Verificar pausa
        if turno.pausa_inicio and turno.pausa_fin:
            p_ini = timezone.make_aware(datetime.combine(fecha_consulta, turno.pausa_inicio))
            p_fin = timezone.make_aware(datetime.combine(fecha_consulta, turno.pausa_fin))
            if slot_inicio < p_fin and slot_fin > p_ini:
                continue

        # Verificar solapamiento con otras reservas del barbero en cualquier sucursal
        solapa = Reserva.objects.filter(
            barbero=b,
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
            fecha_hora_inicio__lt=slot_fin + descanso,
            fecha_hora_fin__gt=slot_inicio - descanso
        ).exists()

        if not solapa:
            # Contar carga de trabajo del día
            citas_hoy = Reserva.objects.filter(
                barbero=b,
                fecha_hora_inicio__date=fecha_consulta,
                estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
            ).count()
            barberos_candidatos.append((citas_hoy, b))

    if not barberos_candidatos:
        return None

    # Ordenar por menor cantidad de citas hoy
    barberos_candidatos.sort(key=lambda x: x[0])
    return barberos_candidatos[0][1]


def crear_reserva_segura(sucursal, servicio, barbero, slot_inicio, slot_fin, datos_cliente, usuario=None):
    """
    Crea una reserva de manera atómica con select_for_update para prevenir doble agendamiento.
    Retorna una tupla (exito: bool, reserva_o_error: Reserva|str).
    """
    config = ConfiguracionSitio.get_solo()
    descanso = timedelta(minutes=config.tiempo_descanso_entre_citas_minutos)

    with transaction.atomic():
        # Si se eligió 'Cualquier barbero' o barbero es None
        if not barbero:
            barbero = asignar_barbero_menor_carga(sucursal, servicio, slot_inicio, slot_fin)
            if not barbero:
                return False, "Lo sentimos, no encontramos un barbero disponible en este horario. Por favor selecciona otro intervalo."

        # Validar solapamiento a nivel de base de datos con bloqueo exclusivo
        solapadas = Reserva.objects.select_for_update().filter(
            barbero=barbero,
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
            fecha_hora_inicio__lt=slot_fin + descanso,
            fecha_hora_fin__gt=slot_inicio - descanso
        )

        if solapadas.exists():
            return False, "El horario seleccionado acaba de ser reservado por otro cliente. Por favor elige otro horario cercano."

        # Calcular precio (precio específico por barbero/sucursal o precio base)
        precio_final = servicio.precio
        cfg_barb = ServicioBarbero.objects.filter(servicio=servicio, barbero=barbero).first()
        if cfg_barb and cfg_barb.precio_personalizado:
            precio_final = cfg_barb.precio_personalizado
        else:
            cfg_suc = ServicioSucursal.objects.filter(servicio=servicio, sucursal=sucursal).first()
            if cfg_suc and cfg_suc.precio_personalizado:
                precio_final = cfg_suc.precio_personalizado

        # Crear reserva
        reserva = Reserva.objects.create(
            cliente=usuario if (usuario and usuario.is_authenticated) else None,
            cliente_nombre=datos_cliente.get('nombre', ''),
            cliente_email=datos_cliente.get('email', ''),
            cliente_telefono=datos_cliente.get('telefono', ''),
            sucursal=sucursal,
            barbero=barbero,
            servicio=servicio,
            fecha_hora_inicio=slot_inicio,
            fecha_hora_fin=slot_fin,
            precio=precio_final,
            estado=Reserva.Estado.CONFIRMADA,
            notas=datos_cliente.get('notas', '')
        )

        # Enviar correos de confirmación en segundo plano o consola
        try:
            asunto_cliente = f"Confirmación de Reserva {reserva.codigo_reserva} — Demo Barber Club"
            cuerpo_cliente = (
                f"Estimado/a {reserva.cliente_nombre},\n\n"
                f"Tu cita ha sido confirmada con éxito.\n\n"
                f"Código: {reserva.codigo_reserva}\n"
                f"Servicio: {reserva.servicio.nombre}\n"
                f"Barbero: {reserva.barbero.nombre_profesional}\n"
                f"Sucursal: {reserva.sucursal.nombre} ({reserva.sucursal.direccion})\n"
                f"Fecha y Hora: {reserva.fecha_hora_inicio.strftime('%d/%m/%Y a las %H:%M')} hrs\n"
                f"Monto a pagar en el local: {reserva.precio_formateado}\n\n"
                f"¡Te esperamos con un café de especialidad de cortesía!\n"
                f"Demo Barber Club"
            )
            send_mail(
                asunto_cliente,
                cuerpo_cliente,
                settings.DEFAULT_FROM_EMAIL,
                [reserva.cliente_email],
                fail_silently=True
            )
        except Exception:
            pass

        return True, reserva
