"""
Decoradores y mixins para control de acceso estricto según roles:
CLIENTE, BARBERO, ADMIN_SUCURSAL, ADMIN_MAESTRO.
"""
from functools import wraps
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from cuentas.models import Usuario


def rol_requerido(*roles_permitidos):
    """
    Decorador para vistas basadas en funciones que verifica si el usuario autenticado
    posee alguno de los roles permitidos.
    """
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('cuentas:login')
            if request.user.is_superuser or request.user.rol in roles_permitidos:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied('No tienes permisos suficientes para acceder a esta sección.')
        return _wrapped_view
    return decorador


def admin_requerido(view_func):
    """Permite el acceso a ADMIN_MAESTRO y ADMIN_SUCURSAL (y superusuarios)"""
    return rol_requerido(Usuario.Rol.ADMIN_MAESTRO, Usuario.Rol.ADMIN_SUCURSAL)(view_func)


def admin_maestro_requerido(view_func):
    """Permite el acceso exclusivamente a ADMIN_MAESTRO (y superusuarios)"""
    return rol_requerido(Usuario.Rol.ADMIN_MAESTRO)(view_func)


def barbero_requerido(view_func):
    return rol_requerido(Usuario.Rol.BARBERO, Usuario.Rol.ADMIN_SUCURSAL, Usuario.Rol.ADMIN_MAESTRO)(view_func)


def cliente_requerido(view_func):
    return rol_requerido(Usuario.Rol.CLIENTE, Usuario.Rol.ADMIN_SUCURSAL, Usuario.Rol.ADMIN_MAESTRO)(view_func)


class RolRequiredMixin(AccessMixin):
    """Mixin para vistas basadas en clases de Django que restringe por rol"""
    roles_permitidos = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser or request.user.rol in self.roles_permitidos:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied('Acceso denegado: tu rol de usuario no tiene acceso a este módulo.')


class AdminRequiredMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.ADMIN_MAESTRO, Usuario.Rol.ADMIN_SUCURSAL]


class AdminMaestroRequiredMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.ADMIN_MAESTRO]


class BarberoRequiredMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.BARBERO, Usuario.Rol.ADMIN_SUCURSAL, Usuario.Rol.ADMIN_MAESTRO]
