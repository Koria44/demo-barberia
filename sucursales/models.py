"""
Módulo de modelos para la app 'sucursales'.
Gestiona las sedes físicas de la barbería en diferentes comunas de Chile.
"""
from django.db import models
from django.utils.text import slugify


class Sucursal(models.Model):
    """
    Representa una sede física de Demo Barber Club.
    Cada sucursal cuenta con sus propios barberos, servicios asignados y horarios de atención.
    """
    nombre = models.CharField('Nombre de Sucursal', max_length=100)
    slug = models.SlugField('Slug amigable para URL', max_length=120, unique=True, blank=True)
    direccion = models.CharField('Dirección', max_length=255)
    comuna = models.CharField('Comuna', max_length=100, default='Santiago')
    ciudad = models.CharField('Ciudad', max_length=100, default='Santiago')
    telefono = models.CharField('Teléfono Fijo / Móvil', max_length=25)
    whatsapp = models.CharField('WhatsApp directo', max_length=25, blank=True)
    email = models.EmailField('Correo de Contacto', blank=True)
    latitud = models.DecimalField('Latitud', max_digits=9, decimal_places=6, default=-33.4255)
    longitud = models.DecimalField('Longitud', max_digits=9, decimal_places=6, default=-70.6120)
    horario_atencion = models.CharField(
        'Horario de Atención',
        max_length=255,
        default='Lunes a Sábado: 10:00 - 20:00 | Domingo: Cerrado'
    )
    foto = models.ImageField('Foto de la Sucursal', upload_to='sucursales/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/sucursales/providencia.webp')
    activa = models.BooleanField('Sucursal Activa', default=True)
    orden = models.PositiveSmallIntegerField('Orden de Visualización', default=1)
    descripcion = models.TextField('Descripción e Instalaciones', blank=True, help_text='Ej. Estacionamiento privado, wifi, café de cortesía.')

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.comuna})"

    @property
    def imagen_url(self):
        if self.foto:
            return self.foto.url
        return f"/static/{self.foto_estatica_demo}"
