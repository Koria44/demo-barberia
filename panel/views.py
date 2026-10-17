"""
Vistas del Dashboard de Administración (/panel/) para Demo Barber Club.
Control integral de alcance por sucursal (ADMIN_MAESTRO y ADMIN_SUCURSAL),
gestión de barberos, servicios, turnos multi-tramo, bloqueos, inventario por sede,
ventas, reportes consolidados y exportaciones CSV.
"""
import csv
import json
from datetime import datetime, date, time, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Sum, Count, Avg, Q, F
from django.db import transaction
from django.core.exceptions import PermissionDenied

from cuentas.models import Usuario
from cuentas.decorators import admin_requerido, admin_maestro_requerido, barbero_requerido
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import (
    Servicio,
    CategoriaServicio,
    ServicioSucursal,
    ServicioBarbero,
    formatear_clp,
)
from reservas.models import Reserva, HorarioTrabajo, Bloqueo, DiaSemana
from tienda.models import (
    Producto,
    CategoriaProducto,
    Pedido,
    ItemPedido,
    StockSucursal,
    MovimientoStock,
    registrar_movimiento_stock,
)
from contenido.models import ConfiguracionSitio
from panel.alcance import (
    obtener_sucursales_permitidas,
    obtener_sucursal_activa_id,
    validar_acceso_sucursal,
    aplicar_alcance_queryset,
    validar_pertenencia_objeto,
)
from panel.forms import BarberoForm, ServicioForm, ServicioSucursalForm


# ==============================================================================
# ALCANCE GLOBAL Y CAMBIO DE SUCURSAL
# ==============================================================================

@admin_requerido
def cambiar_sucursal(request):
    """
    Permite alternar la sede activa en la sesión del panel.
    - ADMIN_MAESTRO puede elegir cualquier sede o '0' para todas (consolidado).
    - ADMIN_SUCURSAL solo puede elegir entre sus sedes asignadas.
    """
    sucursal_param = request.GET.get('sucursal') or request.POST.get('sucursal')
    next_url = request.GET.get('next') or request.POST.get('next') or '/panel/'

    if not next_url.startswith('/panel/'):
        next_url = '/panel/'

    if sucursal_param is not None:
        sucursal_param = str(sucursal_param).strip()
        if request.user.es_admin_maestro and (sucursal_param in ('0', '', 'all', 'todas')):
            request.session['panel_sucursal_id'] = None
            messages.info(request, "Vista cambiada a: Todas las Sedes (Consolidado).")
        else:
            try:
                suc_id = int(sucursal_param)
                permitidas = obtener_sucursales_permitidas(request.user)
                sucursal = permitidas.filter(id=suc_id).first()
                if sucursal:
                    request.session['panel_sucursal_id'] = sucursal.id
                    messages.info(request, f"Sede activa: {sucursal.nombre}.")
                elif not request.user.es_admin_maestro:
                    raise PermissionDenied("No tienes acceso a la sede seleccionada.")
            except ValueError:
                pass

    return redirect(next_url)


# ==============================================================================
# DASHBOARD PRINCIPAL, KPIS Y COMPARATIVA
# ==============================================================================

@admin_requerido
def dashboard_view(request):
    """Vista principal de métricas, KPIs y gráficos comerciales con Chart.js"""
    ahora = timezone.now()
    hoy = ahora.date()
    hace_7_dias = ahora - timedelta(days=7)
    hace_30_dias = ahora - timedelta(days=30)

    # Filtrar según el alcance del usuario y la sede activa en sesión o parámetro
    reservas_qs = aplicar_alcance_queryset(Reserva.objects.all(), request, 'sucursal')
    pedidos_qs = aplicar_alcance_queryset(Pedido.objects.all(), request, 'sucursal_retiro')

    # 1. Ventas del Día / Semana / Mes
    ventas_hoy_servicios = reservas_qs.filter(
        fecha_hora_inicio__date=hoy,
        estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
    ).aggregate(total=Sum('precio'))['total'] or 0

    ventas_hoy_productos = pedidos_qs.filter(
        creado_el__date=hoy,
        estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.LISTO_PARA_RETIRO, Pedido.Estado.ENTREGADO]
    ).aggregate(total=Sum('total'))['total'] or 0

    ventas_hoy_total = ventas_hoy_servicios + ventas_hoy_productos

    ventas_semana_servicios = reservas_qs.filter(
        fecha_hora_inicio__gte=hace_7_dias,
        estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
    ).aggregate(total=Sum('precio'))['total'] or 0

    ventas_semana_productos = pedidos_qs.filter(
        creado_el__gte=hace_7_dias,
        estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.LISTO_PARA_RETIRO, Pedido.Estado.ENTREGADO]
    ).aggregate(total=Sum('total'))['total'] or 0

    ventas_semana_total = ventas_semana_servicios + ventas_semana_productos

    ventas_mes_servicios = reservas_qs.filter(
        fecha_hora_inicio__gte=hace_30_dias,
        estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
    ).aggregate(total=Sum('precio'))['total'] or 0

    ventas_mes_productos = pedidos_qs.filter(
        creado_el__gte=hace_30_dias,
        estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.LISTO_PARA_RETIRO, Pedido.Estado.ENTREGADO]
    ).aggregate(total=Sum('total'))['total'] or 0

    ventas_mes_total = ventas_mes_servicios + ventas_mes_productos

    # 2. Contadores de Reservas
    reservas_hoy_count = reservas_qs.filter(fecha_hora_inicio__date=hoy).count()
    citas_pendientes_count = reservas_qs.filter(estado=Reserva.Estado.PENDIENTE).count()

    # 3. Ticket Promedio (Servicios)
    ticket_promedio = reservas_qs.filter(
        estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
    ).aggregate(prom=Avg('precio'))['prom'] or 0

    # 4. Clientes Nuevos este mes
    clientes_nuevos_count = Usuario.objects.filter(
        rol=Usuario.Rol.CLIENTE,
        date_joined__gte=hace_30_dias
    ).count()

    # 5. Tasa de Cancelación (%)
    total_reservas_mes = reservas_qs.filter(fecha_hora_inicio__gte=hace_30_dias).count()
    canceladas_mes = reservas_qs.filter(fecha_hora_inicio__gte=hace_30_dias, estado=Reserva.Estado.CANCELADA).count()
    tasa_cancelacion = round((canceladas_mes / total_reservas_mes * 100), 1) if total_reservas_mes > 0 else 0

    # 6. Alertas de Stock Bajo según sedes permitidas
    sucursales_permitidas = obtener_sucursales_permitidas(request.user)
    sucursal_activa_id = obtener_sucursal_activa_id(request)
    if sucursal_activa_id:
        stocks_alerta = StockSucursal.objects.filter(
            sucursal_id=sucursal_activa_id,
            cantidad__lte=F('stock_minimo_alerta')
        ).select_related('producto', 'sucursal')
    else:
        stocks_alerta = StockSucursal.objects.filter(
            sucursal__in=sucursales_permitidas,
            cantidad__lte=F('stock_minimo_alerta')
        ).select_related('producto', 'sucursal')

    # 7. Datos para Gráficos Chart.js
    chart_dias_labels = []
    chart_ingresos_data = []
    for i in range(6, -1, -1):
        dia_iter = (ahora - timedelta(days=i)).date()
        chart_dias_labels.append(dia_iter.strftime('%d/%m'))
        ing_serv = reservas_qs.filter(
            fecha_hora_inicio__date=dia_iter,
            estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]
        ).aggregate(t=Sum('precio'))['t'] or 0
        ing_prod = pedidos_qs.filter(
            creado_el__date=dia_iter,
            estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.LISTO_PARA_RETIRO, Pedido.Estado.ENTREGADO]
        ).aggregate(t=Sum('total'))['t'] or 0
        chart_ingresos_data.append(ing_serv + ing_prod)

    # Gráfico 2: Reservas por Sucursal
    reservas_por_sucursal = reservas_qs.values('sucursal__nombre').annotate(total=Count('id')).order_by('-total')
    chart_sucursales_labels = [r['sucursal__nombre'] for r in reservas_por_sucursal if r['sucursal__nombre']]
    chart_sucursales_data = [r['total'] for r in reservas_por_sucursal if r['sucursal__nombre']]

    # Gráfico 3: Servicios más vendidos
    servicios_top = reservas_qs.values('servicio__nombre').annotate(total=Count('id')).order_by('-total')[:5]
    chart_servicios_labels = [s['servicio__nombre'] for s in servicios_top if s['servicio__nombre']]
    chart_servicios_data = [s['total'] for s in servicios_top if s['servicio__nombre']]

    # Gráfico 4: Rendimiento por Barbero (citas atendidas)
    barberos_rendimiento = reservas_qs.values('barbero__nombre_profesional').annotate(total=Count('id')).order_by('-total')
    chart_barberos_labels = [b['barbero__nombre_profesional'] for b in barberos_rendimiento if b['barbero__nombre_profesional']]
    chart_barberos_data = [b['total'] for b in barberos_rendimiento if b['barbero__nombre_profesional']]

    # 8. Comparativo entre Sucursales (Exclusivo para ADMIN_MAESTRO en vista consolidada)
    comparativa_sucursales = []
    if request.user.es_admin_maestro and not sucursal_activa_id:
        for suc in sucursales_permitidas:
            res_suc = Reserva.objects.filter(sucursal=suc, fecha_hora_inicio__gte=hace_30_dias)
            ped_suc = Pedido.objects.filter(sucursal_retiro=suc, creado_el__gte=hace_30_dias)
            
            ing_serv = res_suc.filter(estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.COMPLETADA]).aggregate(s=Sum('precio'))['s'] or 0
            ing_prod = ped_suc.filter(estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.LISTO_PARA_RETIRO, Pedido.Estado.ENTREGADO]).aggregate(s=Sum('total'))['s'] or 0
            total_ingresos = ing_serv + ing_prod
            
            total_reservas = res_suc.count()
            barberos_count = suc.barberos.filter(activo=True).count()
            stock_critico = StockSucursal.objects.filter(sucursal=suc, cantidad__lte=F('stock_minimo_alerta')).count()

            comparativa_sucursales.append({
                'sucursal': suc,
                'ingresos_mes': formatear_clp(total_ingresos),
                'reservas_mes': total_reservas,
                'barberos_activos': barberos_count,
                'stock_critico': stock_critico,
            })

    return render(request, 'panel/dashboard.html', {
        'ventas_hoy_total': formatear_clp(ventas_hoy_total),
        'ventas_semana_total': formatear_clp(ventas_semana_total),
        'ventas_mes_total': formatear_clp(ventas_mes_total),
        'ventas_mes_servicios': formatear_clp(ventas_mes_servicios),
        'ventas_mes_productos': formatear_clp(ventas_mes_productos),
        'reservas_hoy_count': reservas_hoy_count,
        'citas_pendientes_count': citas_pendientes_count,
        'ticket_promedio': formatear_clp(ticket_promedio),
        'clientes_nuevos_count': clientes_nuevos_count,
        'tasa_cancelacion': tasa_cancelacion,
        'stocks_alerta': stocks_alerta,
        'sucursales': sucursales_permitidas,
        'sucursal_seleccionada': sucursal_activa_id,
        'comparativa_sucursales': comparativa_sucursales,
        # JSON para Chart.js
        'chart_dias_labels': json.dumps(chart_dias_labels),
        'chart_ingresos_data': json.dumps(chart_ingresos_data),
        'chart_sucursales_labels': json.dumps(chart_sucursales_labels),
        'chart_sucursales_data': json.dumps(chart_sucursales_data),
        'chart_servicios_labels': json.dumps(chart_servicios_labels),
        'chart_servicios_data': json.dumps(chart_servicios_data),
        'chart_barberos_labels': json.dumps(chart_barberos_labels),
        'chart_barberos_data': json.dumps(chart_barberos_data),
    })


# ==============================================================================
# GESTIÓN DE RESERVAS
# ==============================================================================

@admin_requerido
def reservas_list_view(request):
    """Gestión integral de reservas con filtros y cambio de estado"""
    reservas = aplicar_alcance_queryset(
        Reserva.objects.select_related('sucursal', 'barbero', 'servicio'),
        request,
        'sucursal'
    ).order_by('-fecha_hora_inicio')

    estado = request.GET.get('estado')
    sucursal_filtro = request.GET.get('sucursal')
    barbero_filtro = request.GET.get('barbero')
    busqueda = request.GET.get('q', '').strip()

    if estado:
        reservas = reservas.filter(estado=estado)
    if sucursal_filtro:
        validar_acceso_sucursal(request.user, sucursal_filtro)
        reservas = reservas.filter(sucursal_id=sucursal_filtro)
    if barbero_filtro:
        reservas = reservas.filter(barbero_id=barbero_filtro)
    if busqueda:
        reservas = reservas.filter(
            Q(cliente_nombre__icontains=busqueda) |
            Q(cliente_email__icontains=busqueda) |
            Q(codigo_reserva__icontains=busqueda) |
            Q(cliente_telefono__icontains=busqueda)
        )

    permitidas = obtener_sucursales_permitidas(request.user)
    barberos = Barbero.objects.filter(sucursales__in=permitidas, activo=True).distinct()

    return render(request, 'panel/reservas_list.html', {
        'reservas': reservas[:150],
        'sucursales': permitidas,
        'barberos': barberos,
        'estado_filtro': estado,
        'sucursal_filtro': sucursal_filtro,
        'barbero_filtro': barbero_filtro,
        'busqueda': busqueda,
    })


@barbero_requerido
def cambiar_estado_reserva(request, codigo_reserva):
    """Acción rápida para cambiar el estado de una cita validando permisos de sede"""
    reserva = get_object_or_404(Reserva, codigo_reserva=codigo_reserva)
    usuario = request.user

    if not usuario.es_administrador:
        barbero_perfil = getattr(usuario, 'perfil_barbero', None)
        if not barbero_perfil or reserva.barbero != barbero_perfil:
            messages.error(request, 'No tienes permisos para modificar citas asignadas a otro barbero.')
            return redirect(request.META.get('HTTP_REFERER', 'panel:agenda_barbero'))
    else:
        validar_pertenencia_objeto(usuario, reserva, 'sucursal')

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Reserva.Estado.choices):
            reserva.estado = nuevo_estado
            reserva.save(update_fields=['estado'])
            messages.success(request, f'Reserva {reserva.codigo_reserva} actualizada a {reserva.get_estado_display()}.')
    return redirect(request.META.get('HTTP_REFERER', 'panel:reservas_list'))


@admin_requerido
def exportar_reservas_csv(request):
    """Exporta las reservas filtradas según el alcance del usuario a formato CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reservas_{date.today()}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Código Reserva', 'Fecha y Hora', 'Sucursal', 'Barbero', 'Servicio',
        'Cliente Nombre', 'Cliente Email', 'Cliente Teléfono', 'Precio CLP', 'Estado'
    ])

    reservas = aplicar_alcance_queryset(
        Reserva.objects.select_related('sucursal', 'barbero', 'servicio'),
        request,
        'sucursal'
    ).order_by('-fecha_hora_inicio')

    for r in reservas:
        writer.writerow([
            r.codigo_reserva,
            r.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M'),
            r.sucursal.nombre,
            r.barbero.nombre_profesional,
            r.servicio.nombre,
            r.cliente_nombre,
            r.cliente_email,
            r.cliente_telefono,
            r.precio,
            r.get_estado_display()
        ])

    return response


# ==============================================================================
# AGENDA DEL BARBERO: HORARIOS SEMANALES, BLOQUEOS Y CALENDARIO
# ==============================================================================

@barbero_requerido
def agenda_barbero_view(request):
    """
    Vista integral de agenda:
    Pestaña a) Horario Semanal multi-tramo
    Pestaña b) Bloqueos de intervalos
    Pestaña c) Calendario interactivo diario y semanal
    """
    usuario = request.user
    es_admin = usuario.es_administrador

    hoy = timezone.localdate()
    fecha_filtro_str = request.GET.get('fecha')
    if fecha_filtro_str:
        try:
            fecha_filtro = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_filtro = hoy
    else:
        fecha_filtro = hoy

    fecha_anterior = fecha_filtro - timedelta(days=1)
    fecha_siguiente = fecha_filtro + timedelta(days=1)

    sucursales_permitidas = obtener_sucursales_permitidas(usuario) if es_admin else (
        usuario.perfil_barbero.sucursales.filter(activa=True) if getattr(usuario, 'perfil_barbero', None) else Sucursal.objects.none()
    )

    barberos_disponibles = Barbero.objects.filter(sucursales__in=sucursales_permitidas, activo=True).distinct().order_by('orden', 'nombre_profesional')

    sucursal_filtro_id = request.GET.get('sucursal') or request.session.get('panel_sucursal_id')
    sucursal_seleccionada = None
    if sucursal_filtro_id:
        try:
            suc_id = int(sucursal_filtro_id)
            sucursal_seleccionada = sucursales_permitidas.filter(id=suc_id).first()
        except ValueError:
            pass

    if not sucursal_seleccionada and sucursales_permitidas.exists():
        sucursal_seleccionada = sucursales_permitidas.first()

    barbero = None
    if es_admin:
        barbero_id_param = request.GET.get('barbero')
        if barbero_id_param:
            try:
                b_id = int(barbero_id_param)
                if usuario.es_admin_maestro:
                    barbero = Barbero.objects.filter(id=b_id).first()
                else:
                    barbero = barberos_disponibles.filter(id=b_id).first()
                    if not barbero:
                        raise PermissionDenied("No tienes acceso a la agenda del barbero solicitado.")
            except ValueError:
                pass
        if not barbero:
            barbero = barberos_disponibles.first() or (Barbero.objects.first() if usuario.es_admin_maestro else None)
    else:
        barbero = getattr(usuario, 'perfil_barbero', None)
        if not barbero:
            return render(request, 'panel/agenda_barbero.html', {
                'es_admin': False,
                'barbero': None,
                'citas': [],
                'mensaje_sin_perfil': 'Tu cuenta de usuario no tiene un perfil profesional de barbero asignado.'
            })

    # Citas para el día seleccionado
    citas_hoy = Reserva.objects.none()
    if barbero:
        citas_qs = Reserva.objects.filter(
            barbero=barbero,
            fecha_hora_inicio__date=fecha_filtro
        )
        if sucursal_seleccionada:
            citas_qs = citas_qs.filter(sucursal=sucursal_seleccionada)
        citas_hoy = citas_qs.select_related('sucursal', 'servicio', 'cliente').order_by('fecha_hora_inicio')

    # Bloqueos vigentes o futuros
    bloqueos_qs = Bloqueo.objects.none()
    if sucursal_seleccionada:
        bloqueos_qs = Bloqueo.objects.filter(
            Q(sucursal=sucursal_seleccionada, barbero__isnull=True) |
            (Q(barbero=barbero) if barbero else Q(pk__isnull=True)),
            fecha_fin__gte=timezone.now()
        ).select_related('barbero', 'sucursal').order_by('fecha_inicio')

    # Horario semanal del barbero en la sede seleccionada
    # Organizado por día de la semana (0: Lunes, ..., 6: Domingo)
    horario_semanal = []
    if barbero and sucursal_seleccionada:
        turnos_barbero = HorarioTrabajo.objects.filter(
            barbero=barbero,
            sucursal=sucursal_seleccionada,
            activo=True
        ).order_by('dia_semana', 'hora_inicio')

        for dia_val, dia_nombre in DiaSemana.choices:
            tramos_dia = turnos_barbero.filter(dia_semana=dia_val)
            tramos_list = [
                {
                    'id': t.id,
                    'hora_inicio': t.hora_inicio.strftime('%H:%M'),
                    'hora_fin': t.hora_fin.strftime('%H:%M'),
                }
                for t in tramos_dia
            ]
            horario_semanal.append({
                'dia_val': dia_val,
                'dia_nombre': dia_nombre,
                'trabaja': bool(tramos_list),
                'tramos': tramos_list,
            })

    # Tab activa (calendario, horario, bloqueos)
    tab_activa = request.GET.get('tab', 'calendario')

    # Servicios disponibles para modal de cita manual
    servicios_barbero = Servicio.objects.filter(activo=True)
    if sucursal_seleccionada:
        excluidos_suc = ServicioSucursal.objects.filter(sucursal=sucursal_seleccionada, disponible=False).values_list('servicio_id', flat=True)
        servicios_barbero = servicios_barbero.exclude(id__in=excluidos_suc)

    return render(request, 'panel/agenda_barbero.html', {
        'es_admin': es_admin,
        'barbero': barbero,
        'barberos': barberos_disponibles,
        'sucursal_seleccionada': sucursal_seleccionada,
        'sucursales': sucursales_permitidas,
        'fecha_filtro': fecha_filtro,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
        'citas': citas_hoy,
        'bloqueos': bloqueos_qs,
        'horario_semanal': horario_semanal,
        'servicios_disponibles': servicios_barbero,
        'tab_activa': tab_activa,
    })


@admin_requerido
def guardar_horario_semanal(request):
    """
    Guarda los turnos semanales de un barbero en una sucursal específica.
    Validaciones:
    - hora_inicio < hora_fin
    - Sin solapamiento entre tramos del mismo día
    - Que el barbero no quede con turnos solapados en OTRA sucursal el mismo día
    - Si deja reservas futuras fuera de horario, advierte y pide confirmación.
    """
    if request.method != 'POST':
        return redirect('panel:agenda_barbero')

    barbero_id = request.POST.get('barbero_id')
    sucursal_id = request.POST.get('sucursal_id')
    confirmado = request.POST.get('confirmar_impacto') == 'true'

    barbero = get_object_or_404(Barbero, id=barbero_id)
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)

    # Validar permisos
    validar_acceso_sucursal(request.user, sucursal)
    validar_pertenencia_objeto(request.user, barbero)

    # Estructurar tramos por día a partir del POST
    # Formato esperado: tramos_{dia} = lista de 'HH:MM-HH:MM'
    nuevos_tramos_por_dia = {}
    errores = []

    for dia_val, _ in DiaSemana.choices:
        activo_dia = request.POST.get(f'trabaja_{dia_val}') == 'on'
        tramos_str_list = request.POST.getlist(f'tramos_{dia_val}')
        tramos_limpios = []

        if activo_dia:
            for tramo_raw in tramos_str_list:
                tramo_raw = tramo_raw.strip()
                if not tramo_raw:
                    continue
                try:
                    ini_str, fin_str = tramo_raw.split('-')
                    h_ini = datetime.strptime(ini_str.strip(), '%H:%M').time()
                    h_fin = datetime.strptime(fin_str.strip(), '%H:%M').time()

                    if h_ini >= h_fin:
                        errores.append(f"El tramo {tramo_raw} en {DiaSemana(dia_val).label} es inválido: inicio debe ser menor que fin.")
                        continue

                    tramos_limpios.append((h_ini, h_fin))
                except Exception:
                    errores.append(f"Formato de tramo inválido '{tramo_raw}'. Use formato HH:MM-HH:MM.")

            # Validar solapamientos internos en el mismo día
            tramos_limpios.sort(key=lambda x: x[0])
            for i in range(len(tramos_limpios) - 1):
                if tramos_limpios[i][1] > tramos_limpios[i + 1][0]:
                    errores.append(f"Solapamiento detectado en {DiaSemana(dia_val).label} entre tramos.")

            # Validar solapamiento con turnos del mismo barbero en OTRAS sucursales
            turnos_otras = HorarioTrabajo.objects.filter(
                barbero=barbero,
                dia_semana=dia_val,
                activo=True
            ).exclude(sucursal=sucursal)

            for t_otra in turnos_otras:
                for mi_ini, mi_fin in tramos_limpios:
                    if mi_ini < t_otra.hora_fin and mi_fin > t_otra.hora_inicio:
                        errores.append(
                            f"Solapamiento entre sedes el {DiaSemana(dia_val).label}: {barbero.nombre_profesional} "
                            f"ya tiene turno en '{t_otra.sucursal.nombre}' ({t_otra.hora_inicio.strftime('%H:%M')}–{t_otra.hora_fin.strftime('%H:%M')})."
                        )

        nuevos_tramos_por_dia[dia_val] = tramos_limpios

    if errores:
        for err in errores:
            messages.error(request, err)
        return redirect(f"/panel/agenda/?tab=horario&barbero={barbero.id}&sucursal={sucursal.id}")

    # Verificar si el cambio deja reservas futuras fuera del horario
    ahora = timezone.now()
    reservas_futuras = Reserva.objects.filter(
        barbero=barbero,
        sucursal=sucursal,
        fecha_hora_inicio__gte=ahora,
        estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA]
    )

    reservas_afectadas = []
    for res in reservas_futuras:
        dia_res = res.fecha_hora_inicio.weekday()
        hora_ini_res = res.fecha_hora_inicio.time()
        hora_fin_res = res.fecha_hora_fin.time()

        tramos_habilitados = nuevos_tramos_por_dia.get(dia_res, [])
        # Comprobar si cabe íntegramente dentro de al menos un tramo
        cabe = any(ini <= hora_ini_res and hora_fin_res <= fin for ini, fin in tramos_habilitados)
        if not cabe:
            reservas_afectadas.append(res)

    if reservas_afectadas and not confirmado:
        # Notificar al usuario con la lista de reservas afectadas y solicitar confirmación
        lista_msg = ", ".join([f"{r.codigo_reserva} ({r.fecha_hora_inicio.strftime('%d/%m %H:%M')})" for r in reservas_afectadas[:5]])
        messages.warning(
            request,
            f"Atención: El nuevo horario deja {len(reservas_afectadas)} reserva(s) futura(s) fuera de turno: {lista_msg}. "
            f"Marca la casilla de confirmación para aplicar el cambio sin borrar las reservas."
        )
        return redirect(f"/panel/agenda/?tab=horario&barbero={barbero.id}&sucursal={sucursal.id}&afectadas={len(reservas_afectadas)}")

    # Guardar turnos atómicamente
    with transaction.atomic():
        HorarioTrabajo.objects.filter(barbero=barbero, sucursal=sucursal).delete()
        for dia_val, tramos in nuevos_tramos_por_dia.items():
            for h_ini, h_fin in tramos:
                HorarioTrabajo.objects.create(
                    barbero=barbero,
                    sucursal=sucursal,
                    dia_semana=dia_val,
                    hora_inicio=h_ini,
                    hora_fin=h_fin,
                    activo=True
                )

    messages.success(request, f"Horario semanal actualizado exitosamente para {barbero.nombre_profesional} en {sucursal.nombre}.")
    return redirect(f"/panel/agenda/?tab=horario&barbero={barbero.id}&sucursal={sucursal.id}")


@admin_requerido
def copiar_horario_semana(request):
    """Copia la configuración de turnos del Lunes a todos los demás días de la semana"""
    if request.method != 'POST':
        return redirect('panel:agenda_barbero')

    barbero_id = request.POST.get('barbero_id')
    sucursal_id = request.POST.get('sucursal_id')
    barbero = get_object_or_404(Barbero, id=barbero_id)
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)

    validar_acceso_sucursal(request.user, sucursal)
    validar_pertenencia_objeto(request.user, barbero)

    tramos_lunes = HorarioTrabajo.objects.filter(
        barbero=barbero,
        sucursal=sucursal,
        dia_semana=DiaSemana.LUNES,
        activo=True
    )

    if not tramos_lunes.exists():
        messages.warning(request, "No hay tramos configurados el día Lunes para copiar.")
        return redirect(f"/panel/agenda/?tab=horario&barbero={barbero.id}&sucursal={sucursal.id}")

    with transaction.atomic():
        # Borrar martes a domingo
        HorarioTrabajo.objects.filter(
            barbero=barbero,
            sucursal=sucursal
        ).exclude(dia_semana=DiaSemana.LUNES).delete()

        # Replicar para cada día de martes a domingo
        for dia_val in [DiaSemana.MARTES, DiaSemana.MIERCOLES, DiaSemana.JUEVES, DiaSemana.VIERNES, DiaSemana.SABADO, DiaSemana.DOMINGO]:
            for t in tramos_lunes:
                HorarioTrabajo.objects.create(
                    barbero=barbero,
                    sucursal=sucursal,
                    dia_semana=dia_val,
                    hora_inicio=t.hora_inicio,
                    hora_fin=t.hora_fin,
                    pausa_inicio=t.pausa_inicio,
                    pausa_fin=t.pausa_fin,
                    activo=True
                )

    messages.success(request, f"Turnos del Lunes replicados a toda la semana para {barbero.nombre_profesional}.")
    return redirect(f"/panel/agenda/?tab=horario&barbero={barbero.id}&sucursal={sucursal.id}")


@admin_requerido
def copiar_horario_barbero(request):
    """Copia el horario semanal completo de un barbero a otro barbero en la misma sede"""
    if request.method != 'POST':
        return redirect('panel:agenda_barbero')

    barbero_origen_id = request.POST.get('barbero_origen_id')
    barbero_destino_id = request.POST.get('barbero_destino_id')
    sucursal_id = request.POST.get('sucursal_id')

    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    barbero_origen = get_object_or_404(Barbero, id=barbero_origen_id)
    barbero_destino = get_object_or_404(Barbero, id=barbero_destino_id)

    validar_acceso_sucursal(request.user, sucursal)
    validar_pertenencia_objeto(request.user, barbero_origen)
    validar_pertenencia_objeto(request.user, barbero_destino)

    horarios_origen = HorarioTrabajo.objects.filter(barbero=barbero_origen, sucursal=sucursal, activo=True)
    if not horarios_origen.exists():
        messages.warning(request, f"{barbero_origen.nombre_profesional} no tiene turnos configurados en {sucursal.nombre}.")
        return redirect(f"/panel/agenda/?tab=horario&barbero={barbero_origen.id}&sucursal={sucursal.id}")

    with transaction.atomic():
        HorarioTrabajo.objects.filter(barbero=barbero_destino, sucursal=sucursal).delete()
        for h in horarios_origen:
            HorarioTrabajo.objects.create(
                barbero=barbero_destino,
                sucursal=sucursal,
                dia_semana=h.dia_semana,
                hora_inicio=h.hora_inicio,
                hora_fin=h.hora_fin,
                pausa_inicio=h.pausa_inicio,
                pausa_fin=h.pausa_fin,
                activo=True
            )

    messages.success(request, f"Horario copiado exitosamente de {barbero_origen.nombre_profesional} a {barbero_destino.nombre_profesional}.")
    return redirect(f"/panel/agenda/?tab=horario&barbero={barbero_destino.id}&sucursal={sucursal.id}")


@barbero_requerido
def crear_bloqueo_view(request):
    """Crea un nuevo bloqueo temporal o recurrente avisando de reservas afectadas"""
    if request.method != 'POST':
        return redirect('panel:agenda_barbero')

    usuario = request.user
    es_admin = usuario.es_administrador

    barbero_id = request.POST.get('barbero_id')
    sucursal_id = request.POST.get('sucursal_id')
    f_ini_str = request.POST.get('fecha_inicio')
    f_fin_str = request.POST.get('fecha_fin')
    tipo = request.POST.get('tipo', Bloqueo.TipoBloqueo.BLOQUEO_MANUAL)
    motivo = request.POST.get('motivo', '').strip() or 'Bloqueo de agenda'
    todo_el_dia = request.POST.get('todo_el_dia') == 'on'
    es_recurrente = request.POST.get('es_recurrente') == 'on'
    dia_recurrente = request.POST.get('dia_semana_recurrente')
    accion_reservas = request.POST.get('accion_reservas', 'mantener')

    sucursal = None
    if sucursal_id:
        sucursal = get_object_or_404(Sucursal, id=sucursal_id)
        if es_admin:
            validar_acceso_sucursal(usuario, sucursal)

    barbero = None
    if barbero_id and barbero_id != 'todos':
        barbero = get_object_or_404(Barbero, id=barbero_id)
        if es_admin:
            validar_pertenencia_objeto(usuario, barbero)
    elif not es_admin:
        barbero = getattr(usuario, 'perfil_barbero', None)

    try:
        if todo_el_dia:
            d_ini = datetime.strptime(f_ini_str[:10], '%Y-%m-%d').date()
            d_fin = datetime.strptime(f_fin_str[:10], '%Y-%m-%d').date() if f_fin_str else d_ini
            dt_ini = timezone.make_aware(datetime.combine(d_ini, time.min))
            dt_fin = timezone.make_aware(datetime.combine(d_fin, time.max))
        else:
            dt_ini = timezone.make_aware(datetime.strptime(f_ini_str, '%Y-%m-%dT%H:%M'))
            dt_fin = timezone.make_aware(datetime.strptime(f_fin_str, '%Y-%m-%dT%H:%M'))

        if dt_ini >= dt_fin:
            messages.error(request, 'La fecha y hora de inicio debe ser anterior a la de término.')
            return redirect(f"/panel/agenda/?tab=bloqueos&barbero={barbero.id if barbero else ''}")

        # Comprobar si existen reservas en el intervalo a bloquear
        reservas_afectadas = Reserva.objects.filter(
            fecha_hora_inicio__lt=dt_fin,
            fecha_hora_fin__gt=dt_ini,
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA]
        )
        if barbero:
            reservas_afectadas = reservas_afectadas.filter(barbero=barbero)
        if sucursal:
            reservas_afectadas = reservas_afectadas.filter(sucursal=sucursal)

        if reservas_afectadas.exists() and accion_reservas == 'reprogramar':
            # Marcar reservas para reprogramación sin cancelarlas silenciosamente
            for r in reservas_afectadas:
                if 'REPROGRAMAR' not in r.notas:
                    r.notas = f"[PENDIENTE REPROGRAMACIÓN: Bloqueo de agenda] {r.notas}".strip()
                    r.save(update_fields=['notas'])

        dia_rec_val = int(dia_recurrente) if (es_recurrente and dia_recurrente) else None

        Bloqueo.objects.create(
            barbero=barbero,
            sucursal=sucursal,
            fecha_inicio=dt_ini,
            fecha_fin=dt_fin,
            tipo=tipo,
            motivo=motivo,
            todo_el_dia=todo_el_dia,
            es_recurrente=es_recurrente,
            dia_semana_recurrente=dia_rec_val
        )

        afectadas_count = reservas_afectadas.count()
        if afectadas_count > 0:
            messages.warning(request, f"Bloqueo registrado. Hay {afectadas_count} reserva(s) preexistente(s) en este intervalo.")
        else:
            messages.success(request, "Bloqueo de agenda creado exitosamente.")

    except Exception as e:
        messages.error(request, f"Error al crear el bloqueo: {str(e)}")

    redirect_url = f"/panel/agenda/?tab=bloqueos"
    if barbero:
        redirect_url += f"&barbero={barbero.id}"
    if sucursal:
        redirect_url += f"&sucursal={sucursal.id}"
    return redirect(redirect_url)


@barbero_requerido
def eliminar_bloqueo_view(request, bloqueo_id):
    """Elimina un bloqueo de agenda validando alcance"""
    bloqueo = get_object_or_404(Bloqueo, id=bloqueo_id)
    usuario = request.user

    if not usuario.es_administrador:
        if bloqueo.barbero != getattr(usuario, 'perfil_barbero', None):
            raise PermissionDenied("No tienes permisos para eliminar este bloqueo.")
    else:
        if bloqueo.sucursal:
            validar_acceso_sucursal(usuario, bloqueo.sucursal)
        if bloqueo.barbero:
            validar_pertenencia_objeto(usuario, bloqueo.barbero)

    if request.method == 'POST':
        bloqueo.delete()
        messages.success(request, "Bloqueo de agenda eliminado correctamente.")

    return redirect(request.META.get('HTTP_REFERER', 'panel:agenda_barbero'))


@admin_requerido
def reserva_rapida_view(request):
    """Crea una reserva manual directa desde el calendario del panel"""
    if request.method != 'POST':
        return redirect('panel:agenda_barbero')

    barbero_id = request.POST.get('barbero_id')
    sucursal_id = request.POST.get('sucursal_id')
    servicio_id = request.POST.get('servicio_id')
    fecha_hora_str = request.POST.get('fecha_hora_inicio')
    cliente_nombre = request.POST.get('cliente_nombre', '').strip()
    cliente_email = request.POST.get('cliente_email', '').strip()
    cliente_telefono = request.POST.get('cliente_telefono', '').strip()

    barbero = get_object_or_404(Barbero, id=barbero_id)
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    servicio = get_object_or_404(Servicio, id=servicio_id)

    validar_acceso_sucursal(request.user, sucursal)
    validar_pertenencia_objeto(request.user, barbero)

    try:
        dt_ini = timezone.make_aware(datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M'))
        dt_fin = dt_ini + timedelta(minutes=servicio.duracion_minutos)

        reserva = Reserva.objects.create(
            cliente=None,
            cliente_nombre=cliente_nombre or 'Cliente Presencial',
            cliente_email=cliente_email or 'presencial@demobarber.cl',
            cliente_telefono=cliente_telefono or '+56 9 0000 0000',
            sucursal=sucursal,
            barbero=barbero,
            servicio=servicio,
            fecha_hora_inicio=dt_ini,
            fecha_hora_fin=dt_fin,
            precio=servicio.precio,
            estado=Reserva.Estado.CONFIRMADA,
            notas='Reserva manual creada desde el panel administrativo'
        )
        messages.success(request, f"Reserva {reserva.codigo_reserva} creada exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al crear reserva rápida: {str(e)}")

    return redirect(f"/panel/agenda/?fecha={fecha_hora_str[:10]}&barbero={barbero.id}&sucursal={sucursal.id}")


# ==============================================================================
# GESTIÓN DE BARBEROS (CRUD)
# ==============================================================================

@admin_requerido
def barberos_panel_list(request):
    """Listado y búsqueda de barberos filtrados por el alcance del usuario"""
    permitidas = obtener_sucursales_permitidas(request.user)
    barberos = aplicar_alcance_queryset(
        Barbero.objects.filter(sucursales__in=permitidas).distinct().prefetch_related('sucursales'),
        request,
        campo_sucursal='sucursales'
    )

    busqueda = request.GET.get('q', '').strip()
    sucursal_filtro = request.GET.get('sucursal')
    estado = request.GET.get('estado')

    if busqueda:
        barberos = barberos.filter(
            Q(nombre_profesional__icontains=busqueda) |
            Q(especialidad_principal__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda)
        )
    if sucursal_filtro:
        validar_acceso_sucursal(request.user, sucursal_filtro)
        barberos = barberos.filter(sucursales__id=sucursal_filtro)
    if estado == 'activos':
        barberos = barberos.filter(activo=True)
    elif estado == 'inactivos':
        barberos = barberos.filter(activo=False)

    return render(request, 'panel/barberos_list.html', {
        'barberos': barberos,
        'sucursales': permitidas,
        'busqueda': busqueda,
        'sucursal_filtro': sucursal_filtro,
        'estado_filtro': estado,
    })


@admin_requerido
def barbero_crear_view(request):
    """Crea un nuevo barbero con cuenta de usuario asociada restringido al alcance de sedes"""
    if request.method == 'POST':
        form = BarberoForm(request.POST, request.FILES, usuario_admin=request.user)
        if form.is_valid():
            barbero = form.save()
            messages.success(request, f"Barbero '{barbero.nombre_profesional}' creado exitosamente.")
            return redirect('panel:barberos_list')
    else:
        form = BarberoForm(usuario_admin=request.user)

    return render(request, 'panel/barbero_form.html', {
        'form': form,
        'titulo': 'Nuevo Barbero Profesional',
        'subtitulo': 'Crea el perfil profesional y cuenta de acceso para el barbero.',
        'modo_edicion': False,
    })


@admin_requerido
def barbero_editar_view(request, barbero_id):
    """Edita un barbero existente validando permisos de sede"""
    barbero = get_object_or_404(Barbero, id=barbero_id)
    validar_pertenencia_objeto(request.user, barbero)

    if request.method == 'POST':
        form = BarberoForm(request.POST, request.FILES, instance=barbero, usuario_admin=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de '{barbero.nombre_profesional}' actualizados.")
            return redirect('panel:barberos_list')
    else:
        form = BarberoForm(instance=barbero, usuario_admin=request.user)

    return render(request, 'panel/barbero_form.html', {
        'form': form,
        'barbero': barbero,
        'titulo': f"Editar a {barbero.nombre_profesional}",
        'subtitulo': 'Modifica fotografía, sedes de atención y especialidades.',
        'modo_edicion': True,
    })


@admin_requerido
def barbero_toggle_activo_view(request, barbero_id):
    """Activa o desactiva un barbero para la reserva pública"""
    barbero = get_object_or_404(Barbero, id=barbero_id)
    validar_pertenencia_objeto(request.user, barbero)

    if request.method == 'POST':
        barbero.activo = not barbero.activo
        barbero.save(update_fields=['activo'])
        estado = "reactivado" if barbero.activo else "desactivado (oculto para reservas públicas)"
        messages.success(request, f"El barbero '{barbero.nombre_profesional}' ha sido {estado}.")

    return redirect('panel:barberos_list')


@admin_requerido
def barbero_eliminar_view(request, barbero_id):
    """Elimina un barbero solo si no tiene reservas; si tiene, exige desactivarlo"""
    barbero = get_object_or_404(Barbero, id=barbero_id)
    validar_pertenencia_objeto(request.user, barbero)

    if request.method == 'POST':
        if barbero.reservas.exists():
            messages.error(
                request,
                f"No es posible eliminar al barbero '{barbero.nombre_profesional}' porque cuenta con un historial de reservas asociadas. "
                "En su lugar, desactívalo para ocultarlo del público sin perder los registros históricos."
            )
            return redirect('panel:barberos_list')

        usuario_cuenta = barbero.usuario
        nombre = barbero.nombre_profesional
        barbero.delete()
        if usuario_cuenta:
            usuario_cuenta.delete()
        messages.success(request, f"El barbero '{nombre}' y su cuenta fueron eliminados exitosamente.")

    return redirect('panel:barberos_list')


# ==============================================================================
# GESTIÓN DE SERVICIOS (CRUD)
# ==============================================================================

@admin_requerido
def catalogo_servicios_panel(request):
    """CRUD de servicios del catálogo con personalizaciones por sucursal"""
    servicios = Servicio.objects.all().order_by('orden', 'nombre')
    permitidas = obtener_sucursales_permitidas(request.user)
    sucursal_activa_id = obtener_sucursal_activa_id(request)

    # Añadir configuración local por servicio para la sucursal activa
    servicios_info = []
    for serv in servicios:
        config_sucursal = None
        if sucursal_activa_id:
            config_sucursal = ServicioSucursal.objects.filter(servicio=serv, sucursal_id=sucursal_activa_id).first()
        servicios_info.append({
            'servicio': serv,
            'config_sucursal': config_sucursal,
            'disponible_local': config_sucursal.disponible if config_sucursal else serv.activo,
            'precio_local': config_sucursal.get_precio() if config_sucursal else serv.precio,
            'duracion_local': config_sucursal.get_duracion() if config_sucursal else serv.duracion_minutos,
        })

    return render(request, 'panel/servicios_list.html', {
        'servicios_info': servicios_info,
        'sucursal_activa_id': sucursal_activa_id,
        'sucursales': permitidas,
    })


@admin_maestro_requerido
def servicio_crear_view(request):
    """Crea un servicio base en el catálogo global (Solo ADMIN_MAESTRO)"""
    if request.method == 'POST':
        form = ServicioForm(request.POST, request.FILES)
        if form.is_valid():
            servicio = form.save()
            messages.success(request, f"Servicio '{servicio.nombre}' creado en el catálogo global.")
            return redirect('panel:servicios_list')
    else:
        form = ServicioForm()

    return render(request, 'panel/servicio_form.html', {
        'form': form,
        'titulo': 'Nuevo Servicio de Barbería',
        'subtitulo': 'Define el servicio base, duración y precio estándar en CLP.',
        'modo_edicion': False,
    })


@admin_maestro_requerido
def servicio_editar_view(request, servicio_id):
    """Edita un servicio base del catálogo (Solo ADMIN_MAESTRO)"""
    servicio = get_object_or_404(Servicio, id=servicio_id)

    if request.method == 'POST':
        form = ServicioForm(request.POST, request.FILES, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, f"Servicio '{servicio.nombre}' actualizado.")
            return redirect('panel:servicios_list')
    else:
        form = ServicioForm(instance=servicio)

    return render(request, 'panel/servicio_form.html', {
        'form': form,
        'servicio': servicio,
        'titulo': f"Editar Servicio: {servicio.nombre}",
        'subtitulo': 'Modifica duración, precio base o etiquetas comerciales.',
        'modo_edicion': True,
    })


@admin_requerido
def servicio_toggle_activo_view(request, servicio_id):
    """
    Alterna disponibilidad de un servicio:
    - ADMIN_MAESTRO: Activa/desactiva el servicio globalmente.
    - ADMIN_SUCURSAL: Activa/desactiva el servicio para su sucursal activa.
    """
    servicio = get_object_or_404(Servicio, id=servicio_id)
    usuario = request.user

    if request.method == 'POST':
        if usuario.es_admin_maestro and not request.session.get('panel_sucursal_id'):
            servicio.activo = not servicio.activo
            servicio.save(update_fields=['activo'])
            messages.success(request, f"Servicio '{servicio.nombre}' {'activado' if servicio.activo else 'desactivado'} globalmente.")
        else:
            sucursal_id = obtener_sucursal_activa_id(request)
            if not sucursal_id:
                messages.error(request, "Selecciona una sucursal para ajustar la disponibilidad local.")
                return redirect('panel:servicios_list')
            validar_acceso_sucursal(usuario, sucursal_id)
            sucursal = get_object_or_404(Sucursal, id=sucursal_id)

            config, _ = ServicioSucursal.objects.get_or_create(servicio=servicio, sucursal=sucursal)
            config.disponible = not config.disponible
            config.save(update_fields=['disponible'])
            messages.success(request, f"Servicio '{servicio.nombre}' {'habilitado' if config.disponible else 'inhabilitado'} en {sucursal.nombre}.")

    return redirect('panel:servicios_list')


@admin_requerido
def servicio_sucursales_view(request, servicio_id):
    """Permite ajustar disponibilidad, precio y duración específica por sucursal"""
    servicio = get_object_or_404(Servicio, id=servicio_id)
    permitidas = obtener_sucursales_permitidas(request.user)

    if request.method == 'POST':
        sucursal_id = request.POST.get('sucursal_id')
        validar_acceso_sucursal(request.user, sucursal_id)
        sucursal = get_object_or_404(Sucursal, id=sucursal_id)

        disponible = request.POST.get('disponible') == 'on'
        precio_str = request.POST.get('precio_personalizado', '').strip()
        duracion_str = request.POST.get('duracion_personalizada', '').strip()

        precio_personalizado = int(precio_str) if precio_str else None
        duracion_personalizada = int(duracion_str) if duracion_str else None

        ServicioSucursal.objects.update_or_create(
            servicio=servicio,
            sucursal=sucursal,
            defaults={
                'disponible': disponible,
                'precio_personalizado': precio_personalizado,
                'duracion_personalizada': duracion_personalizada,
            }
        )
        messages.success(request, f"Ajustes de '{servicio.nombre}' guardados para {sucursal.nombre}.")
        return redirect('panel:servicios_list')

    configs = []
    for suc in permitidas:
        conf = ServicioSucursal.objects.filter(servicio=servicio, sucursal=suc).first()
        configs.append({
            'sucursal': suc,
            'config': conf,
        })

    return render(request, 'panel/servicio_sucursales.html', {
        'servicio': servicio,
        'configs': configs,
    })


@admin_maestro_requerido
def servicio_eliminar_view(request, servicio_id):
    """Elimina un servicio solo si no posee citas agendadas"""
    servicio = get_object_or_404(Servicio, id=servicio_id)

    if request.method == 'POST':
        if servicio.reservas.exists():
            messages.error(request, f"No se puede eliminar '{servicio.nombre}' porque registra citas históricas. Desactívalo en su lugar.")
            return redirect('panel:servicios_list')
        nombre = servicio.nombre
        servicio.delete()
        messages.success(request, f"Servicio '{nombre}' eliminado.")

    return redirect('panel:servicios_list')


# ==============================================================================
# GESTIÓN DE PRODUCTOS E INVENTARIO POR SUCURSAL
# ==============================================================================

@admin_requerido
def inventario_panel_view(request):
    """
    Pantalla integral de inventario:
    - Tabla por sucursal con stock actual, mínimo, estado OK / Bajo / Agotado con colores
    - Buscador, filtro por categoría y estado
    - Historial de movimientos inmutables
    """
    permitidas = obtener_sucursales_permitidas(request.user)
    sucursal_activa_id = obtener_sucursal_activa_id(request)

    sucursales_evaluadas = permitidas.filter(id=sucursal_activa_id) if sucursal_activa_id else permitidas

    # Asegurar que existan registros StockSucursal para todos los productos en estas sucursales
    productos_activos = Producto.objects.all()
    for suc in sucursales_evaluadas:
        for prod in productos_activos:
            StockSucursal.objects.get_or_create(
                producto=prod,
                sucursal=suc,
                defaults={'cantidad': 0, 'stock_minimo_alerta': prod.stock_minimo_alerta}
            )

    stocks_qs = StockSucursal.objects.filter(
        sucursal__in=sucursales_evaluadas
    ).select_related('producto', 'producto__categoria', 'sucursal').order_by('sucursal__orden', 'producto__orden')

    # Filtros
    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria')
    estado = request.GET.get('estado')

    if busqueda:
        stocks_qs = stocks_qs.filter(
            Q(producto__nombre__icontains=busqueda) |
            Q(producto__sku__icontains=busqueda)
        )
    if categoria_id:
        stocks_qs = stocks_qs.filter(producto__categoria_id=categoria_id)
    if estado == 'bajo':
        stocks_qs = stocks_qs.filter(cantidad__gt=0, cantidad__lte=F('stock_minimo_alerta'))
    elif estado == 'agotado':
        stocks_qs = stocks_qs.filter(cantidad__lte=0)
    elif estado == 'ok':
        stocks_qs = stocks_qs.filter(cantidad__gt=F('stock_minimo_alerta'))

    # Movimientos recientes de auditoría
    movimientos = MovimientoStock.objects.filter(
        Q(sucursal__in=sucursales_evaluadas) | Q(sucursal_destino__in=sucursales_evaluadas)
    ).select_related('producto', 'sucursal', 'sucursal_destino', 'usuario')[:50]

    categorias = CategoriaProducto.objects.all()

    return render(request, 'panel/inventario.html', {
        'stocks': stocks_qs,
        'movimientos': movimientos,
        'sucursales': permitidas,
        'sucursal_activa_id': sucursal_activa_id,
        'categorias': categorias,
        'busqueda': busqueda,
        'categoria_id': categoria_id,
        'estado_filtro': estado,
    })


@admin_requerido
def registrar_movimiento_panel(request):
    """Procesa altas de stock, ajustes y traslados garantizando stock no negativo"""
    if request.method != 'POST':
        return redirect('panel:productos_list')

    producto_id = request.POST.get('producto_id')
    sucursal_id = request.POST.get('sucursal_id')
    sucursal_destino_id = request.POST.get('sucursal_destino_id')
    tipo = request.POST.get('tipo')
    cantidad_str = request.POST.get('cantidad', '0')
    motivo = request.POST.get('motivo', '').strip()
    nota = request.POST.get('nota', '').strip()

    producto = get_object_or_404(Producto, id=producto_id)
    sucursal = get_object_or_404(Sucursal, id=sucursal_id)
    validar_acceso_sucursal(request.user, sucursal)

    sucursal_destino = None
    if sucursal_destino_id:
        sucursal_destino = get_object_or_404(Sucursal, id=sucursal_destino_id)

    try:
        cantidad = int(cantidad_str)
        mov = registrar_movimiento_stock(
            producto=producto,
            sucursal=sucursal,
            tipo=tipo,
            cantidad=cantidad,
            usuario=request.user,
            motivo=motivo or f"Operación de {tipo} desde el panel",
            nota=nota,
            sucursal_destino=sucursal_destino
        )
        messages.success(request, f"Movimiento '{mov.get_tipo_display()}' registrado exitosamente para {producto.nombre}.")
    except Exception as e:
        messages.error(request, f"Error al procesar movimiento de inventario: {str(e)}")

    return redirect('panel:productos_list')


@admin_requerido
def exportar_movimientos_csv(request):
    """Exporta el historial de movimientos de inventario a CSV con formato compatible"""
    permitidas = obtener_sucursales_permitidas(request.user)
    sucursal_activa_id = obtener_sucursal_activa_id(request)
    sucursales_evaluadas = permitidas.filter(id=sucursal_activa_id) if sucursal_activa_id else permitidas

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="movimientos_stock_{date.today()}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'ID', 'Fecha y Hora', 'Tipo', 'Producto', 'SKU', 'Sucursal',
        'Sucursal Destino', 'Cantidad', 'Stock Resultante', 'Usuario', 'Motivo', 'Notas'
    ])

    movimientos = MovimientoStock.objects.filter(
        Q(sucursal__in=sucursales_evaluadas) | Q(sucursal_destino__in=sucursales_evaluadas)
    ).select_related('producto', 'sucursal', 'sucursal_destino', 'usuario').order_by('-fecha')

    for m in movimientos:
        writer.writerow([
            m.id,
            m.fecha.strftime('%d/%m/%Y %H:%M'),
            m.get_tipo_display(),
            m.producto.nombre,
            m.producto.sku or '-',
            m.sucursal.nombre,
            m.sucursal_destino.nombre if m.sucursal_destino else '-',
            m.cantidad,
            m.stock_resultante,
            m.usuario.get_full_name() or m.usuario.email if m.usuario else 'Sistema',
            m.motivo,
            m.nota
        ])

    return response


@admin_maestro_requerido
def producto_crear_view(request):
    """Crea un nuevo producto en el catálogo global (Solo ADMIN_MAESTRO)"""
    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        sku = request.POST.get('sku', '').strip()
        categoria_id = request.POST.get('categoria')
        descripcion = request.POST.get('descripcion', '').strip()
        precio = int(request.POST.get('precio', 0))
        precio_costo_str = request.POST.get('precio_costo', '').strip()
        precio_costo = int(precio_costo_str) if precio_costo_str else None
        stock_minimo_alerta = int(request.POST.get('stock_minimo_alerta', 5))
        destacado = request.POST.get('destacado') == 'on'
        activo = request.POST.get('activo') == 'on'
        imagen = request.FILES.get('imagen')

        if not nombre or precio < 0:
            messages.error(request, "Nombre y precio válido son obligatorios.")
        else:
            cat = CategoriaProducto.objects.filter(id=categoria_id).first() if categoria_id else None
            producto = Producto.objects.create(
                nombre=nombre,
                slug=slugify(nombre),
                sku=sku,
                categoria=cat,
                descripcion=descripcion,
                precio=precio,
                precio_costo=precio_costo,
                stock_minimo_alerta=stock_minimo_alerta,
                destacado=destacado,
                activo=activo,
                imagen=imagen
            )
            # Inicializar registros de stock por sucursal
            for suc in Sucursal.objects.filter(activa=True):
                StockSucursal.objects.get_or_create(
                    producto=producto,
                    sucursal=suc,
                    defaults={'cantidad': 0, 'stock_minimo_alerta': stock_minimo_alerta}
                )
            messages.success(request, f"Producto '{producto.nombre}' creado en el catálogo global.")
            return redirect('panel:productos_list')

    return render(request, 'panel/producto_form.html', {
        'categorias': categorias,
        'titulo': 'Nuevo Producto de Cuidado Masculino',
        'subtitulo': 'Registra SKU, margen comercial, imágenes y umbral de alerta.',
        'modo_edicion': False,
    })


@admin_maestro_requerido
def producto_editar_view(request, producto_id):
    """Edita atributos globales de un producto (Solo ADMIN_MAESTRO)"""
    producto = get_object_or_404(Producto, id=producto_id)
    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre', producto.nombre).strip()
        producto.sku = request.POST.get('sku', '').strip()
        cat_id = request.POST.get('categoria')
        producto.categoria = CategoriaProducto.objects.filter(id=cat_id).first() if cat_id else None
        producto.descripcion = request.POST.get('descripcion', '').strip()
        producto.precio = int(request.POST.get('precio', producto.precio))
        costo_str = request.POST.get('precio_costo', '').strip()
        producto.precio_costo = int(costo_str) if costo_str else None
        producto.stock_minimo_alerta = int(request.POST.get('stock_minimo_alerta', producto.stock_minimo_alerta))
        producto.destacado = request.POST.get('destacado') == 'on'
        producto.activo = request.POST.get('activo') == 'on'

        if 'imagen' in request.FILES:
            producto.imagen = request.FILES['imagen']

        producto.save()
        messages.success(request, f"Producto '{producto.nombre}' actualizado.")
        return redirect('panel:productos_list')

    return render(request, 'panel/producto_form.html', {
        'producto': producto,
        'categorias': categorias,
        'titulo': f"Editar Producto: {producto.nombre}",
        'subtitulo': 'Modifica precio de venta, costo, SKU y alertas.',
        'modo_edicion': True,
    })


@admin_maestro_requerido
def producto_eliminar_view(request, producto_id):
    """Elimina un producto si no registra ventas"""
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        if producto.ventas.exists():
            messages.error(request, f"No es posible eliminar '{producto.nombre}' porque registra ventas históricas. Desactívalo en su lugar.")
            return redirect('panel:productos_list')
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f"Producto '{nombre}' eliminado del catálogo.")

    return redirect('panel:productos_list')


@admin_maestro_requerido
def categorias_producto_view(request):
    """CRUD de categorías de productos para la tienda"""
    if request.method == 'POST' and 'crear_categoria' in request.POST:
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            CategoriaProducto.objects.create(nombre=nombre, slug=slugify(nombre))
            messages.success(request, f"Categoría '{nombre}' creada.")
            return redirect('panel:categorias_producto')

    if request.method == 'POST' and 'eliminar_categoria' in request.POST:
        cat_id = request.POST.get('categoria_id')
        cat = get_object_or_404(CategoriaProducto, id=cat_id)
        if cat.productos.exists():
            messages.error(request, f"No puedes eliminar '{cat.nombre}' mientras tenga productos asociados.")
        else:
            cat.delete()
            messages.success(request, "Categoría eliminada.")
        return redirect('panel:categorias_producto')

    categorias = CategoriaProducto.objects.annotate(total_productos=Count('productos'))
    return render(request, 'panel/categorias_producto.html', {'categorias': categorias})


# ==============================================================================
# GESTIÓN DE PEDIDOS Y VENTAS
# ==============================================================================

@admin_requerido
def pedidos_list_view(request):
    """Gestión de pedidos de la tienda online con control de alcance"""
    pedidos = aplicar_alcance_queryset(
        Pedido.objects.select_related('sucursal_retiro').prefetch_related('items__producto'),
        request,
        'sucursal_retiro'
    ).order_by('-creado_el')

    estado = request.GET.get('estado')
    if estado:
        pedidos = pedidos.filter(estado=estado)

    permitidas = obtener_sucursales_permitidas(request.user)
    productos_en_alerta = StockSucursal.objects.filter(
        sucursal__in=permitidas,
        cantidad__lte=F('stock_minimo_alerta')
    ).select_related('producto', 'sucursal')

    return render(request, 'panel/pedidos_list.html', {
        'pedidos': pedidos,
        'productos_alerta': productos_en_alerta,
        'estado_filtro': estado,
    })


@admin_requerido
def cambiar_estado_pedido(request, codigo_pedido):
    """
    Actualiza el estado de un pedido.
    Si se cancela un pedido, devuelve el stock correspondiente a la sucursal de retiro como DEVOLUCION.
    """
    pedido = get_object_or_404(Pedido, codigo_pedido=codigo_pedido)
    validar_pertenencia_objeto(request.user, pedido, 'sucursal_retiro')

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Pedido.Estado.choices):
            if nuevo_estado == Pedido.Estado.CANCELADO and pedido.estado != Pedido.Estado.CANCELADO:
                with transaction.atomic():
                    for item in pedido.items.select_related('producto').all():
                        registrar_movimiento_stock(
                            producto=item.producto,
                            sucursal=pedido.sucursal_retiro,
                            tipo=MovimientoStock.Tipo.DEVOLUCION,
                            cantidad=item.cantidad,
                            usuario=request.user,
                            motivo=f'Devolución por cancelación de Pedido {pedido.codigo_pedido}'
                        )
                    pedido.estado = Pedido.Estado.CANCELADO
                    pedido.save(update_fields=['estado'])
                messages.success(request, f"Pedido {pedido.codigo_pedido} cancelado y stock retornado a la sede {pedido.sucursal_retiro.nombre}.")
            else:
                pedido.estado = nuevo_estado
                pedido.save(update_fields=['estado'])
                messages.success(request, f"Pedido {pedido.codigo_pedido} actualizado a {pedido.get_estado_display()}.")

    return redirect('panel:pedidos_list')


@admin_requerido
def exportar_ventas_csv(request):
    """Exporta los pedidos de la tienda a formato CSV según el alcance del usuario"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="ventas_{date.today()}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Código Pedido', 'Fecha Compra', 'Cliente', 'Email', 'Teléfono',
        'Sucursal Retiro', 'Método Pago', 'Total CLP', 'Estado'
    ])

    pedidos = aplicar_alcance_queryset(
        Pedido.objects.select_related('sucursal_retiro'),
        request,
        'sucursal_retiro'
    ).order_by('-creado_el')

    for p in pedidos:
        writer.writerow([
            p.codigo_pedido,
            p.creado_el.strftime('%d/%m/%Y %H:%M'),
            p.cliente_nombre,
            p.cliente_email,
            p.cliente_telefono,
            p.sucursal_retiro.nombre,
            p.get_metodo_pago_display(),
            p.total,
            p.get_estado_display()
        ])

    return response


# ==============================================================================
# SUCURSALES, CLIENTES Y CONFIGURACIÓN GLOBAL
# ==============================================================================

@admin_maestro_requerido
def sucursales_panel_list(request):
    """Listado y gestión de sedes físicas (Exclusivo ADMIN_MAESTRO)"""
    sucursales = Sucursal.objects.all().order_by('orden')
    return render(request, 'panel/sucursales_list.html', {'sucursales': sucursales})


@admin_requerido
def clientes_panel_list(request):
    """Historial de clientes con métricas de visitas y gasto total"""
    clientes = Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).annotate(
        total_citas=Count('reservas', filter=Q(reservas__estado=Reserva.Estado.COMPLETADA)),
        gasto_total=Sum('reservas__precio', filter=Q(reservas__estado=Reserva.Estado.COMPLETADA))
    ).order_by('-date_joined')
    return render(request, 'panel/clientes_list.html', {'clientes': clientes})


@admin_maestro_requerido
def configuracion_sitio_view(request):
    """Edición integral de la configuración de la barbería (Solo ADMIN_MAESTRO)"""
    config = ConfiguracionSitio.get_solo()

    if request.method == 'POST':
        config.nombre_negocio = request.POST.get('nombre_negocio', config.nombre_negocio)
        config.eslogan = request.POST.get('eslogan', config.eslogan)
        config.descripcion_corta = request.POST.get('descripcion_corta', config.descripcion_corta)
        config.telefono_principal = request.POST.get('telefono_principal', config.telefono_principal)
        config.whatsapp_numero = request.POST.get('whatsapp_numero', config.whatsapp_numero)
        config.whatsapp_mensaje = request.POST.get('whatsapp_mensaje', config.whatsapp_mensaje)
        config.instagram_usuario = request.POST.get('instagram_usuario', config.instagram_usuario)
        config.email_contacto = request.POST.get('email_contacto', config.email_contacto)

        # Hero
        config.hero_antetitulo = request.POST.get('hero_antetitulo', config.hero_antetitulo)
        config.hero_titulo_parte1 = request.POST.get('hero_titulo_parte1', config.hero_titulo_parte1)
        config.hero_titulo_acento = request.POST.get('hero_titulo_acento', config.hero_titulo_acento)
        config.hero_subtitulo = request.POST.get('hero_subtitulo', config.hero_subtitulo)
        config.hero_cta_primario = request.POST.get('hero_cta_primario', config.hero_cta_primario)
        config.hero_cta_secundario = request.POST.get('hero_cta_secundario', config.hero_cta_secundario)

        # Parámetros motor
        config.horas_minimas_anticipacion = int(request.POST.get('horas_minimas_anticipacion', config.horas_minimas_anticipacion))
        config.horas_minimas_cancelacion = int(request.POST.get('horas_minimas_cancelacion', config.horas_minimas_cancelacion))
        config.dias_maximos_futuro = int(request.POST.get('dias_maximos_futuro', config.dias_maximos_futuro))
        config.tiempo_descanso_entre_citas_minutos = int(request.POST.get('tiempo_descanso_entre_citas_minutos', config.tiempo_descanso_entre_citas_minutos))

        # Colores
        config.color_fondo = request.POST.get('color_fondo', config.color_fondo)
        config.color_acento = request.POST.get('color_acento', config.color_acento)
        config.color_texto = request.POST.get('color_texto', config.color_texto)

        # Banner anuncio
        config.banner_anuncio_activo = 'banner_anuncio_activo' in request.POST
        config.banner_anuncio_texto = request.POST.get('banner_anuncio_texto', config.banner_anuncio_texto)

        config.save()
        messages.success(request, 'Configuración de la barbería actualizada exitosamente.')
        return redirect('panel:configuracion')

    return render(request, 'panel/configuracion.html', {'sitio': config})
