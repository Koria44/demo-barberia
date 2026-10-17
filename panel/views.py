"""
Vistas del Dashboard de Administración (/panel/) para Demo Barber Club.
Control de KPIs comerciales, gráficos Chart.js, agenda de barberos,
gestión de reservas, catálogo, tienda, contenidos y exportación CSV.
"""
import csv
import json
from datetime import datetime, date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db import transaction

from cuentas.models import Usuario
from cuentas.decorators import admin_requerido, barbero_requerido
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio, CategoriaServicio, formatear_clp
from reservas.models import Reserva, HorarioTrabajo, Bloqueo, DiaSemana
from tienda.models import Producto, Pedido, ItemPedido, CategoriaProducto
from contenido.models import (
    ConfiguracionSitio,
    Testimonio,
    PreguntaFrecuente,
    ImagenGaleria,
    EntradaBlog
)


@admin_requerido
def dashboard_view(request):
    """Vista principal de métricas, KPIs y gráficos comerciales con Chart.js"""
    ahora = timezone.now()
    hoy = ahora.date()
    hace_7_dias = ahora - timedelta(days=7)
    hace_30_dias = ahora - timedelta(days=30)

    # Filtros opcionales por sucursal
    sucursal_id = request.GET.get('sucursal')
    reservas_qs = Reserva.objects.all()
    pedidos_qs = Pedido.objects.all()

    if sucursal_id:
        reservas_qs = reservas_qs.filter(sucursal_id=sucursal_id)
        pedidos_qs = pedidos_qs.filter(sucursal_retiro_id=sucursal_id)

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

    # 6. Alertas de Stock Bajo
    productos_alerta_stock = Producto.objects.filter(stock__lte=5, activo=True)

    # 7. Datos para Gráficos Chart.js
    # Gráfico 1: Ingresos de los últimos 7 días
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

    sucursales_todas = Sucursal.objects.filter(activa=True)

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
        'productos_alerta_stock': productos_alerta_stock,
        'sucursales': sucursales_todas,
        'sucursal_seleccionada': sucursal_id,
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


@admin_requerido
def reservas_list_view(request):
    """Gestión integral de reservas con filtros y cambio de estado"""
    reservas = Reserva.objects.select_related('sucursal', 'barbero', 'servicio').order_by('-fecha_hora_inicio')

    # Filtros
    estado = request.GET.get('estado')
    sucursal_id = request.GET.get('sucursal')
    barbero_id = request.GET.get('barbero')
    busqueda = request.GET.get('q', '').strip()

    if estado:
        reservas = reservas.filter(estado=estado)
    if sucursal_id:
        reservas = reservas.filter(sucursal_id=sucursal_id)
    if barbero_id:
        reservas = reservas.filter(barbero_id=barbero_id)
    if busqueda:
        reservas = reservas.filter(
            Q(cliente_nombre__icontains=busqueda) |
            Q(cliente_email__icontains=busqueda) |
            Q(codigo_reserva__icontains=busqueda) |
            Q(cliente_telefono__icontains=busqueda)
        )

    sucursales = Sucursal.objects.filter(activa=True)
    barberos = Barbero.objects.filter(activo=True)

    return render(request, 'panel/reservas_list.html', {
        'reservas': reservas[:100],
        'sucursales': sucursales,
        'barberos': barberos,
        'estado_filtro': estado,
        'sucursal_filtro': sucursal_id,
        'barbero_filtro': barbero_id,
        'busqueda': busqueda,
    })


@barbero_requerido
def cambiar_estado_reserva(request, codigo_reserva):
    """
    Acción rápida para cambiar el estado de una cita.
    Permitido para ADMINISTRADOR (cualquier reserva) y BARBERO (solo sus citas).
    """
    reserva = get_object_or_404(Reserva, codigo_reserva=codigo_reserva)
    usuario = request.user
    es_admin = (usuario.rol == Usuario.Rol.ADMINISTRADOR or usuario.is_superuser)

    # Si es barbero, verificar que la cita le pertenezca
    if not es_admin:
        barbero_perfil = getattr(usuario, 'perfil_barbero', None)
        if not barbero_perfil or reserva.barbero != barbero_perfil:
            messages.error(request, 'No tienes permisos para modificar citas asignadas a otro barbero.')
            return redirect(request.META.get('HTTP_REFERER', 'panel:agenda_barbero'))

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Reserva.Estado.choices):
            reserva.estado = nuevo_estado
            reserva.save(update_fields=['estado'])
            messages.success(request, f'Estado de la reserva {reserva.codigo_reserva} actualizado a {reserva.get_estado_display()}.')
    return redirect(request.META.get('HTTP_REFERER', 'panel:reservas_list'))


@barbero_requerido
def agenda_barbero_view(request):
    """
    Vista de agenda de citas:
    - Si el usuario es ADMINISTRADOR (o superuser):
      Permite seleccionar sucursal y barbero (y fecha con navegación día/semana).
      Muestra las citas correspondientes con opciones para cambiar estado y crear bloqueos.
    - Si el usuario es BARBERO:
      Muestra únicamente su agenda personal. Un barbero nunca puede ver la agenda de otro.
    - Si el usuario no tiene perfil de barbero (caso de excepción para barbero),
      se maneja amigablemente sin romper la página.
    """
    usuario = request.user
    es_admin = (usuario.rol == Usuario.Rol.ADMINISTRADOR or usuario.is_superuser)

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

    barbero = None
    sucursales_disponibles = Sucursal.objects.filter(activa=True).order_by('orden')
    barberos_disponibles = Barbero.objects.filter(activo=True).order_by('orden')
    sucursal_filtro_id = request.GET.get('sucursal')
    sucursal_seleccionada = None

    if sucursal_filtro_id:
        sucursal_seleccionada = Sucursal.objects.filter(id=sucursal_filtro_id, activa=True).first()
        if sucursal_seleccionada:
            barberos_disponibles = barberos_disponibles.filter(sucursales=sucursal_seleccionada)

    if es_admin:
        # Administrador puede ver cualquier barbero
        barbero_id_param = request.GET.get('barbero')
        if barbero_id_param:
            barbero = Barbero.objects.filter(id=barbero_id_param, activo=True).first()

        # Si no seleccionó barbero o no existe, toma el primero de la lista disponible
        if not barbero:
            barbero = barberos_disponibles.first()
    else:
        # Es barbero: solo puede ver su propia agenda
        barbero = getattr(usuario, 'perfil_barbero', None)
        if not barbero:
            # Manejar caso de usuario con rol BARBERO pero sin perfil asociado
            return render(request, 'panel/agenda_barbero.html', {
                'es_admin': False,
                'barbero': None,
                'citas': [],
                'fecha_filtro': fecha_filtro,
                'fecha_anterior': fecha_anterior,
                'fecha_siguiente': fecha_siguiente,
                'bloqueos': [],
                'mensaje_sin_perfil': 'Tu cuenta de usuario tiene asignado el rol de barbero pero aún no se le ha vinculado un perfil profesional. Contacta al administrador del sistema.'
            })

    # Si aún no hay ningún barbero registrado en el sistema
    if not barbero:
        return render(request, 'panel/agenda_barbero.html', {
            'es_admin': es_admin,
            'barbero': None,
            'citas': [],
            'fecha_filtro': fecha_filtro,
            'fecha_anterior': fecha_anterior,
            'fecha_siguiente': fecha_siguiente,
            'bloqueos': [],
            'sucursales': sucursales_disponibles,
            'barberos': barberos_disponibles,
            'sucursal_seleccionada': sucursal_filtro_id,
            'barbero_seleccionado': None,
            'mensaje_sin_perfil': 'No se encontraron barberos activos registrados en el sistema.'
        })

    # Citas para el barbero en la fecha seleccionada
    citas_qs = Reserva.objects.filter(
        barbero=barbero,
        fecha_hora_inicio__date=fecha_filtro
    )
    if sucursal_seleccionada:
        citas_qs = citas_qs.filter(sucursal=sucursal_seleccionada)

    citas_hoy = citas_qs.select_related('sucursal', 'servicio', 'cliente').order_by('fecha_hora_inicio')

    bloqueos_barbero = Bloqueo.objects.filter(
        barbero=barbero,
        fecha_inicio__date__gte=hoy
    ).order_by('fecha_inicio')

    # Gestión de nuevo bloqueo por parte del barbero o administrador
    if request.method == 'POST' and 'crear_bloqueo' in request.POST:
        f_ini_str = request.POST.get('fecha_inicio')
        f_fin_str = request.POST.get('fecha_fin')
        motivo = request.POST.get('motivo', 'Bloqueo administrativo' if es_admin else 'Bloqueo personal')
        if f_ini_str and f_fin_str:
            try:
                dt_ini = timezone.make_aware(datetime.strptime(f_ini_str, '%Y-%m-%dT%H:%M'))
                dt_fin = timezone.make_aware(datetime.strptime(f_fin_str, '%Y-%m-%dT%H:%M'))
                Bloqueo.objects.create(
                    barbero=barbero,
                    fecha_inicio=dt_ini,
                    fecha_fin=dt_fin,
                    tipo=Bloqueo.TipoBloqueo.BLOQUEO_MANUAL,
                    motivo=motivo
                )
                messages.success(request, f'Horas bloqueadas exitosamente para {barbero.nombre_profesional}.')
                redirect_url = request.path + f"?fecha={fecha_filtro.strftime('%Y-%m-%d')}"
                if es_admin and barbero:
                    redirect_url += f"&barbero={barbero.id}"
                if es_admin and sucursal_filtro_id:
                    redirect_url += f"&sucursal={sucursal_filtro_id}"
                return redirect(redirect_url)
            except Exception as e:
                messages.error(request, f'Error al registrar bloqueo: {str(e)}')

    return render(request, 'panel/agenda_barbero.html', {
        'es_admin': es_admin,
        'barbero': barbero,
        'citas': citas_hoy,
        'fecha_filtro': fecha_filtro,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
        'bloqueos': bloqueos_barbero,
        'sucursales': sucursales_disponibles,
        'barberos': barberos_disponibles,
        'sucursal_seleccionada': sucursal_filtro_id,
        'barbero_seleccionado': str(barbero.id) if barbero else '',
    })


@admin_requerido
def pedidos_list_view(request):
    """Gestión de pedidos de la tienda online con control de stock"""
    pedidos = Pedido.objects.select_related('sucursal_retiro').prefetch_related('items__producto').order_by('-creado_el')
    estado = request.GET.get('estado')
    if estado:
        pedidos = pedidos.filter(estado=estado)

    productos_en_alerta = Producto.objects.filter(stock__lte=5, activo=True)

    return render(request, 'panel/pedidos_list.html', {
        'pedidos': pedidos,
        'productos_alerta': productos_en_alerta,
        'estado_filtro': estado,
    })


@admin_requerido
def cambiar_estado_pedido(request, codigo_pedido):
    """Actualiza el estado de un pedido (Pagado, Listo para retiro, etc.)"""
    pedido = get_object_or_404(Pedido, codigo_pedido=codigo_pedido)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Pedido.Estado.choices):
            pedido.estado = nuevo_estado
            pedido.save(update_fields=['estado'])
            messages.success(request, f'Pedido {pedido.codigo_pedido} actualizado a {pedido.get_estado_display()}.')
    return redirect('panel:pedidos_list')


@admin_requerido
def exportar_reservas_csv(request):
    """Exporta las reservas a formato CSV estándar compatible con Excel"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reservas_demo_barber_{date.today()}.csv"'

    # Escribir BOM UTF-8 para que Excel abra acentos en español sin problemas
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Código Reserva', 'Fecha y Hora', 'Sucursal', 'Barbero', 'Servicio',
        'Cliente Nombre', 'Cliente Email', 'Cliente Teléfono', 'Precio CLP', 'Estado'
    ])

    reservas = Reserva.objects.select_related('sucursal', 'barbero', 'servicio').order_by('-fecha_hora_inicio')
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


@admin_requerido
def exportar_ventas_csv(request):
    """Exporta los pedidos de la tienda a formato CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="ventas_tienda_barber_{date.today()}.csv"'

    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Código Pedido', 'Fecha Compra', 'Cliente', 'Email', 'Teléfono',
        'Sucursal Retiro', 'Método Pago', 'Total CLP', 'Estado'
    ])

    pedidos = Pedido.objects.select_related('sucursal_retiro').order_by('-creado_el')
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


@admin_requerido
def configuracion_sitio_view(request):
    """Edición integral de la configuración de la barbería (marca, colores, redes, políticas)"""
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


@admin_requerido
def catalogo_servicios_panel(request):
    """CRUD de servicios del catálogo en el dashboard"""
    servicios = Servicio.objects.all().order_by('orden')
    return render(request, 'panel/servicios_list.html', {'servicios': servicios})


@admin_requerido
def catalogo_productos_panel(request):
    """CRUD de productos de la tienda en el dashboard"""
    productos = Producto.objects.all().order_by('orden')
    return render(request, 'panel/productos_list.html', {'productos': productos})


@admin_requerido
def barberos_panel_list(request):
    """Listado y gestión de barberos en el dashboard"""
    barberos = Barbero.objects.prefetch_related('sucursales').order_by('orden')
    return render(request, 'panel/barberos_list.html', {'barberos': barberos})


@admin_requerido
def sucursales_panel_list(request):
    """Listado y gestión de sedes en el dashboard"""
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
