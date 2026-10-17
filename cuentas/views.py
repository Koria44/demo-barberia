"""
Vistas de autenticación y gestión de perfil de usuario para Demo Barber Club.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from cuentas.models import Usuario
from cuentas.forms import LoginForm, RegistroForm, PerfilUsuarioForm, RecuperarClaveForm
from reservas.models import Reserva
from contenido.models import ConfiguracionSitio


def login_view(request):
    """Vista de inicio de sesión con email y contraseña"""
    if request.user.is_authenticated:
        return redirect('cuentas:redirect_por_rol')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            # Restablecer contador de fallos
            user.intentos_fallidos_login = 0
            user.save(update_fields=['intentos_fallidos_login'])
            login(request, user)
            messages.success(request, f'¡Bienvenido de vuelta, {user.first_name or user.email}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('cuentas:redirect_por_rol')
    else:
        form = LoginForm()

    return render(request, 'cuentas/login.html', {'form': form})


def registro_view(request):
    """Vista de registro para nuevos clientes"""
    if request.user.is_authenticated:
        return redirect('cuentas:redirect_por_rol')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada con éxito! Bienvenido al club, {user.first_name}.')
            return redirect('cuentas:mi_cuenta')
    else:
        form = RegistroForm()

    return render(request, 'cuentas/registro.html', {'form': form})


def logout_view(request):
    """Cierra la sesión del usuario"""
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente. ¡Te esperamos pronto!')
    return redirect('sitio_publico:inicio')


@login_required
def redirect_por_rol_view(request):
    """
    Redirige inteligentemente al usuario tras identificarse según su rol:
    - ADMIN_MAESTRO y ADMIN_SUCURSAL -> Dashboard /panel/
    - BARBERO -> Su agenda diaria /panel/agenda/
    - CLIENTE -> Su historial /mi-cuenta/
    """
    if request.user.es_administrador:
        return redirect('panel:dashboard')
    elif request.user.es_barbero:
        return redirect('panel:agenda_barbero')
    else:
        return redirect('cuentas:mi_cuenta')


@login_required
def mi_cuenta_view(request):
    """
    Panel personal del cliente:
    - Pestaña 'Mis Reservas': historial con estados y opción de cancelación según política
    - Pestaña 'Mis Datos': formulario editable de perfil
    """
    usuario = request.user
    config = ConfiguracionSitio.get_solo()
    ahora = timezone.now()

    # Reservas del cliente ordenadas
    reservas = Reserva.objects.filter(cliente=usuario).select_related('sucursal', 'barbero', 'servicio').order_by('-fecha_hora_inicio')

    # Añadir a cada reserva si es cancelable
    horas_cancelacion = config.horas_minimas_cancelacion
    for res in reservas:
        limite = res.fecha_hora_inicio - timedelta(hours=horas_cancelacion)
        res.es_cancelable = (ahora < limite) and (res.estado in [Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA])

    if request.method == 'POST' and 'actualizar_perfil' in request.POST:
        form = PerfilUsuarioForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tus datos de perfil han sido actualizados correctamente.')
            return redirect('cuentas:mi_cuenta')
    else:
        form = PerfilUsuarioForm(instance=usuario)

    return render(request, 'cuentas/mi_cuenta.html', {
        'form': form,
        'reservas': reservas,
        'horas_cancelacion': horas_cancelacion
    })


@login_required
def cancelar_reserva_cliente(request, codigo_reserva):
    """Permite al cliente cancelar una reserva propia si cumple con la anticipación mínima"""
    reserva = get_object_or_404(Reserva, codigo_reserva=codigo_reserva, cliente=request.user)
    config = ConfiguracionSitio.get_solo()
    ahora = timezone.now()
    limite = reserva.fecha_hora_inicio - timedelta(hours=config.horas_minimas_cancelacion)

    if ahora > limite:
        messages.error(request, f'No es posible cancelar con menos de {config.horas_minimas_cancelacion} horas de anticipación. Por favor comunícate directamente con la sucursal.')
        return redirect('cuentas:mi_cuenta')

    if reserva.estado in [Reserva.Estado.COMPLETADA, Reserva.Estado.CANCELADA]:
        messages.warning(request, 'Esta reserva ya no puede ser cancelada.')
        return redirect('cuentas:mi_cuenta')

    reserva.estado = Reserva.Estado.CANCELADA
    reserva.save(update_fields=['estado'])
    messages.success(request, f'La reserva {reserva.codigo_reserva} ha sido cancelada exitosamente.')
    return redirect('cuentas:mi_cuenta')


def recuperar_clave_view(request):
    """Vista de solicitud de recuperación de clave por correo"""
    if request.method == 'POST':
        form = RecuperarClaveForm(request.POST)
        if form.is_valid():
            # En entorno de desarrollo imprime en consola
            form.save(
                request=request,
                use_https=request.is_secure(),
                from_email='Demo Barber Club <contacto@demobarberclub.cl>',
                email_template_name='cuentas/email_recuperar_clave.html',
                subject_template_name='cuentas/email_recuperar_asunto.txt'
            )
            messages.success(request, 'Hemos enviado las instrucciones para restablecer tu contraseña al correo indicado.')
            return redirect('cuentas:login')
    else:
        form = RecuperarClaveForm()

    return render(request, 'cuentas/recuperar_clave.html', {'form': form})
