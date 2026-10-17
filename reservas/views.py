"""
Vistas y Endpoints API del Sistema de Reservas para Demo Barber Club.
Soporta flujo por pasos interactivo sin recarga, cálculo dinámico y confirmación atómica.
"""
import json
from datetime import datetime, date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.utils import timezone

from sucursales.models import Sucursal
from catalogo.models import Servicio, ServicioSucursal, ServicioBarbero, formatear_clp
from barberos.models import Barbero
from reservas.models import Reserva
from reservas.motor import (
    obtener_barberos_elegibles,
    calcular_horarios_disponibles,
    crear_reserva_segura
)
from contenido.models import ConfiguracionSitio


def agendar_view(request):
    """
    Vista principal del flujo de agendamiento por pasos.
    Soporta preselección opcional por URL (ej: /reservas/agendar/?sucursal=providencia&barbero=matias-silva).
    """
    sucursales = Sucursal.objects.filter(activa=True).order_by('orden')
    servicios = Servicio.objects.filter(activo=True).order_by('orden')
    config = ConfiguracionSitio.get_solo()

    # Preselecciones opcionales
    pre_sucursal = request.GET.get('sucursal')
    pre_servicio = request.GET.get('servicio')
    pre_barbero = request.GET.get('barbero')

    # Datos iniciales para el cliente si está autenticado
    cliente_inicial = {
        'autenticado': request.user.is_authenticated,
        'nombre': request.user.get_full_name() if request.user.is_authenticated else '',
        'email': request.user.email if request.user.is_authenticated else '',
        'telefono': request.user.telefono if request.user.is_authenticated else '',
        'notas': request.user.notas_cliente if request.user.is_authenticated else '',
    }

    return render(request, 'reservas/agendar.html', {
        'sucursales': sucursales,
        'servicios': servicios,
        'config': config,
        'pre_sucursal': pre_sucursal,
        'pre_servicio': pre_servicio,
        'pre_barbero': pre_barbero,
        'cliente_inicial': json.dumps(cliente_inicial)
    })


@require_GET
def api_servicios_sucursal(request):
    """Devuelve los servicios disponibles para una sucursal específica"""
    sucursal_id = request.GET.get('sucursal_id')
    if not sucursal_id:
        return JsonResponse({'error': 'sucursal_id es obligatorio'}, status=400)

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    # Excluir los servicios explícitamente desactivados en ServicioSucursal
    excluidos = ServicioSucursal.objects.filter(sucursal=sucursal, disponible=False).values_list('servicio_id', flat=True)
    servicios = Servicio.objects.filter(activo=True).exclude(id__in=excluidos).order_by('orden')

    data = []
    for s in servicios:
        data.append({
            'id': s.id,
            'nombre': s.nombre,
            'descripcion': s.descripcion,
            'duracion': s.duracion_minutos,
            'precio': s.precio,
            'precio_formateado': s.precio_formateado,
            'etiqueta': s.etiqueta,
            'imagen_url': s.imagen_url
        })
    return JsonResponse({'servicios': data})


@require_GET
def api_barberos_disponibles(request):
    """Devuelve los barberos de una sucursal que realizan el servicio indicado"""
    sucursal_id = request.GET.get('sucursal_id')
    servicio_id = request.GET.get('servicio_id')

    if not sucursal_id or not servicio_id:
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)

    barberos = obtener_barberos_elegibles(sucursal, servicio)
    data = []
    for b in barberos:
        data.append({
            'id': b.id,
            'nombre': b.nombre_profesional,
            'especialidad': b.especialidad_principal,
            'imagen_url': b.imagen_url,
            'anios_experiencia': b.anios_experiencia
        })
    return JsonResponse({'barberos': data})


@require_GET
def api_dias_disponibles(request):
    """Devuelve los días de la semana activos y rango de fechas válidas para sucursal y barbero"""
    sucursal_id = request.GET.get('sucursal_id')
    barbero_id = request.GET.get('barbero_id')
    servicio_id = request.GET.get('servicio_id')

    if not sucursal_id:
        return JsonResponse({'error': 'sucursal_id es obligatorio'}, status=400)

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    config = ConfiguracionSitio.get_solo()
    hoy_local = timezone.localdate()
    fecha_max = hoy_local + timedelta(days=config.dias_maximos_futuro)

    servicio = None
    if servicio_id:
        servicio = Servicio.objects.filter(id=servicio_id, activo=True).first()

    barbero = None
    if barbero_id and barbero_id != 'cualquiera' and barbero_id != '':
        barbero = Barbero.objects.filter(id=barbero_id, activo=True).first()

    if barbero:
        barberos_elegibles = [barbero]
    else:
        barberos_elegibles = list(obtener_barberos_elegibles(sucursal, servicio))

    from reservas.models import HorarioTrabajo
    dias_activos = list(HorarioTrabajo.objects.filter(
        sucursal=sucursal,
        barbero__in=barberos_elegibles,
        activo=True
    ).values_list('dia_semana', flat=True).distinct())

    return JsonResponse({
        'dias_semana_activos': sorted(dias_activos),
        'fecha_min': hoy_local.strftime('%Y-%m-%d'),
        'fecha_max': fecha_max.strftime('%Y-%m-%d')
    })


@require_GET
def api_horarios_disponibles(request):
    """Calcula y devuelve los slots de horario disponibles para una fecha"""
    sucursal_id = request.GET.get('sucursal_id')
    servicio_id = request.GET.get('servicio_id')
    fecha_str = request.GET.get('fecha')
    barbero_id = request.GET.get('barbero_id')

    if not sucursal_id or not servicio_id or not fecha_str:
        return JsonResponse({'error': 'Parámetros insuficientes'}, status=400)

    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido. Usar YYYY-MM-DD'}, status=400)

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)

    barbero = None
    if barbero_id and barbero_id != 'cualquiera' and barbero_id != '':
        barbero = get_object_or_404(Barbero, id=barbero_id)

    horarios = calcular_horarios_disponibles(sucursal, servicio, fecha_obj, barbero)
    return JsonResponse({'horarios': horarios})


@require_POST
def api_confirmar_reserva(request):
    """Crea la reserva de forma atómica y segura"""
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST

    sucursal_id = body.get('sucursal_id')
    servicio_id = body.get('servicio_id')
    barbero_id = body.get('barbero_id')
    fecha_str = body.get('fecha')
    hora_str = body.get('hora')
    cliente_nombre = body.get('cliente_nombre', '').strip()
    cliente_email = body.get('cliente_email', '').strip()
    cliente_telefono = body.get('cliente_telefono', '').strip()
    cliente_notas = body.get('cliente_notas', '').strip()

    if not all([sucursal_id, servicio_id, fecha_str, hora_str, cliente_nombre, cliente_email, cliente_telefono]):
        return JsonResponse({'exito': False, 'error': 'Por favor completa todos los campos requeridos.'}, status=400)

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)

    barbero = None
    if barbero_id and barbero_id != 'cualquiera':
        barbero = get_object_or_404(Barbero, id=barbero_id)

    try:
        hora_split = [int(p) for p in hora_str.split(':')]
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        dt_inicio = timezone.make_aware(datetime.combine(fecha_obj, datetime.min.time().replace(hour=hora_split[0], minute=hora_split[1])))
        dt_fin = dt_inicio + timedelta(minutes=servicio.duracion_minutos)
    except Exception as e:
        return JsonResponse({'exito': False, 'error': f'Error en formato de fecha u hora: {str(e)}'}, status=400)

    datos_cliente = {
        'nombre': cliente_nombre,
        'email': cliente_email,
        'telefono': cliente_telefono,
        'notas': cliente_notas
    }

    exito, res_o_error = crear_reserva_segura(
        sucursal=sucursal,
        servicio=servicio,
        barbero=barbero,
        slot_inicio=dt_inicio,
        slot_fin=dt_fin,
        datos_cliente=datos_cliente,
        usuario=request.user
    )

    if not exito:
        return JsonResponse({'exito': False, 'error': res_o_error}, status=409)

    reserva = res_o_error
    return JsonResponse({
        'exito': True,
        'codigo_reserva': reserva.codigo_reserva,
        'token_invitado': str(reserva.token_invitado),
        'redirect_url': f"/reservas/confirmacion/{reserva.codigo_reserva}/"
    })


def reserva_confirmacion_view(request, codigo_reserva):
    """Pantalla final de confirmación con check animado y botones de Google Calendar y WhatsApp"""
    reserva = get_object_or_404(
        Reserva.objects.select_related('sucursal', 'barbero', 'servicio'),
        codigo_reserva=codigo_reserva
    )
    config = ConfiguracionSitio.get_solo()

    # Enlace para WhatsApp del local con mensaje prellenado
    whatsapp_msg = f"Hola {config.nombre_negocio}, tengo confirmada la reserva {reserva.codigo_reserva} para el {reserva.fecha_hora_inicio.strftime('%d/%m/%Y a las %H:%M')} con {reserva.barbero.nombre_profesional}."
    clean_phone = config.whatsapp_numero.replace(' ', '').replace('+', '').replace('-', '')
    whatsapp_url = f"https://wa.me/{clean_phone}?text={whatsapp_msg}"

    # Fechas formateadas para Google Calendar (formato YYYYMMDDTHHMMSSZ)
    dt_start = reserva.fecha_hora_inicio.strftime('%Y%m%dT%H%M%S')
    dt_end = reserva.fecha_hora_fin.strftime('%Y%m%dT%H%M%S')
    google_calendar_url = (
        f"https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={reserva.servicio.nombre} - Demo Barber Club"
        f"&dates={dt_start}/{dt_end}"
        f"&details=Cita con {reserva.barbero.nombre_profesional} en {reserva.sucursal.nombre}."
        f"&location={reserva.sucursal.direccion}, {reserva.sucursal.comuna}"
    )

    return render(request, 'reservas/confirmacion.html', {
        'reserva': reserva,
        'whatsapp_url': whatsapp_url,
        'google_calendar_url': google_calendar_url
    })


def cancelar_reserva_invitado_view(request, token_invitado):
    """Permite al cliente invitado cancelar su cita mediante su token privado único"""
    reserva = get_object_or_404(Reserva, token_invitado=token_invitado)
    config = ConfiguracionSitio.get_solo()
    ahora = timezone.now()
    limite = reserva.fecha_hora_inicio - timedelta(hours=config.horas_minimas_cancelacion)

    if request.method == 'POST':
        if ahora > limite:
            messages.error(request, f'No es posible cancelar con menos de {config.horas_minimas_cancelacion} horas de anticipación.')
            return redirect('sitio_publico:inicio')

        reserva.estado = Reserva.Estado.CANCELADA
        reserva.save(update_fields=['estado'])
        messages.success(request, f'Tu reserva {reserva.codigo_reserva} ha sido cancelada exitosamente.')
        return redirect('sitio_publico:inicio')

    es_cancelable = (ahora < limite) and (reserva.estado in [Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA])
    return render(request, 'reservas/cancelar_invitado.html', {
        'reserva': reserva,
        'es_cancelable': es_cancelable,
        'horas_cancelacion': config.horas_minimas_cancelacion
    })
