"""
Módulo de modelos para la app 'cuentas'.
Define el modelo de Usuario personalizado con autenticación por correo electrónico
y separación estricta de roles: CLIENTE, BARBERO, ADMINISTRADOR.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class UsuarioManager(BaseUserManager):
    """
    Administrador personalizado para el modelo Usuario donde el correo electrónico
    es el identificador único para la autenticación en lugar de nombres de usuario.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('El correo electrónico es obligatorio.'))
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', Usuario.Rol.ADMIN_MAESTRO)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('El superusuario debe tener is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('El superusuario debe tener is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para la plataforma Demo Barber Club.
    Soporta autenticación por email y cuatro roles diferenciados con permisos específicos:
    CLIENTE, BARBERO, ADMIN_SUCURSAL y ADMIN_MAESTRO.
    """
    class Rol(models.TextChoices):
        CLIENTE = 'CLIENTE', _('Cliente')
        BARBERO = 'BARBERO', _('Barbero')
        ADMIN_SUCURSAL = 'ADMIN_SUCURSAL', _('Administrador de Sucursal')
        ADMIN_MAESTRO = 'ADMIN_MAESTRO', _('Administrador Maestro')

    email = models.EmailField(_('Correo Electrónico'), unique=True)
    telefono = models.CharField(_('Teléfono / WhatsApp'), max_length=20, blank=True)
    rol = models.CharField(
        _('Rol en el Sistema'),
        max_length=20,
        choices=Rol.choices,
        default=Rol.CLIENTE
    )
    sucursales_asignadas = models.ManyToManyField(
        'sucursales.Sucursal',
        blank=True,
        related_name='administradores',
        verbose_name=_('Sucursales Asignadas')
    )
    foto_perfil = models.ImageField(
        _('Foto de Perfil'),
        upload_to='usuarios/perfiles/',
        blank=True,
        null=True
    )
    intentos_fallidos_login = models.PositiveSmallIntegerField(
        _('Intentos Fallidos de Inicio de Sesión'),
        default=0
    )
    bloqueado_hasta = models.DateTimeField(
        _('Bloqueado Temporalmente Hasta'),
        blank=True,
        null=True
    )
    notas_cliente = models.TextField(
        _('Notas Internas de Preferencias de Corte'),
        blank=True,
        help_text='Preferencias del cliente (ej. degradado bajo, barba perfilada con navaja, etc.)'
    )
    fecha_nacimiento = models.DateField(
        _('Fecha de Nacimiento'),
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UsuarioManager()

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['-date_joined']

    def __str__(self):
        nombre_completo = self.get_full_name().strip()
        return nombre_completo if nombre_completo else self.email

    @property
    def es_cliente(self):
        return self.rol == self.Rol.CLIENTE

    @property
    def es_barbero(self):
        return self.rol == self.Rol.BARBERO

    @property
    def es_admin_maestro(self):
        return self.rol == self.Rol.ADMIN_MAESTRO or self.is_superuser

    @property
    def es_admin_sucursal(self):
        return self.rol == self.Rol.ADMIN_SUCURSAL

    @property
    def es_administrador(self):
        return self.es_admin_maestro or self.es_admin_sucursal
