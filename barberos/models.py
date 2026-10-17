"""
Módulo de modelos para la app 'barberos'.
Gestiona los perfiles profesionales de los barberos, sus sucursales de trabajo y especialidades.
"""
from django.db import models
from django.conf import settings
from sucursales.models import Sucursal


class Barbero(models.Model):
    """
    Perfil profesional de un barbero de Demo Barber Club.
    Está vinculado a una cuenta de Usuario y puede trabajar en una o más sucursales.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_barbero',
        verbose_name='Cuenta de Usuario'
    )
    nombre_profesional = models.CharField('Nombre Profesional / Artístico', max_length=100)
    slug = models.SlugField('Slug para URL', max_length=120, unique=True, blank=True)
    sucursales = models.ManyToManyField(
        Sucursal,
        related_name='barberos',
        verbose_name='Sucursales donde atiende',
        blank=True
    )
    foto = models.ImageField('Fotografía Profesional', upload_to='barberos/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/barberos/matias_silva.webp')
    bio = models.TextField('Biografía y Filosofía de Trabajo', blank=True)
    especialidad_principal = models.CharField('Especialidad Principal', max_length=150, default='Master Barber • Fade & Barba Clásica')
    instagram = models.CharField('Usuario de Instagram (sin @)', max_length=50, blank=True)
    anios_experiencia = models.PositiveSmallIntegerField('Años de Experiencia', default=5)
    activo = models.BooleanField('Barbero Activo para Reservas', default=True)
    orden = models.PositiveSmallIntegerField('Orden de Visualización', default=1)

    class Meta:
        verbose_name = 'Barbero'
        verbose_name_plural = 'Barberos'
        ordering = ['orden', 'nombre_profesional']

    def __str__(self):
        return self.nombre_profesional

    @property
    def imagen_url(self):
        if self.foto:
            return self.foto.url
        return f"/static/{self.foto_estatica_demo}"
