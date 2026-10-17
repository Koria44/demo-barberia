"""
Módulo de modelos para la app 'catalogo'.
Gestiona los servicios ofrecidos por la barbería y su personalización por sucursal y por barbero.
"""
from django.db import models
from django.utils.text import slugify
from sucursales.models import Sucursal
from barberos.models import Barbero


def formatear_clp(monto):
    """Formatea un número entero a formato de moneda chilena CLP: $18.000"""
    try:
        monto_int = int(monto)
        return f"${monto_int:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return f"${monto}"


class CategoriaServicio(models.Model):
    """Categoría para agrupar servicios (Cortes, Barba, Combos, Tratamientos)"""
    nombre = models.CharField('Nombre de Categoría', max_length=100)
    slug = models.SlugField('Slug', unique=True, blank=True)
    orden = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = 'Categoría de Servicio'
        verbose_name_plural = 'Categorías de Servicios'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    """
    Servicio de barbería ofrecido a los clientes.
    Posee duración base y precio base en pesos chilenos (CLP).
    """
    categoria = models.ForeignKey(
        CategoriaServicio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios',
        verbose_name='Categoría'
    )
    nombre = models.CharField('Nombre del Servicio', max_length=120)
    slug = models.SlugField('Slug para URL', max_length=140, unique=True, blank=True)
    descripcion = models.TextField('Descripción Detallada')
    duracion_minutos = models.PositiveIntegerField('Duración Base en Minutos', default=45)
    precio = models.IntegerField('Precio Base en CLP (ej. 18000)', default=18000)
    etiqueta = models.CharField(
        'Etiqueta Destacada',
        max_length=50,
        blank=True,
        help_text='Ej: "Más Solicitado", "Signature", "Ritual Premium"'
    )
    es_destacado = models.BooleanField('Mostrar como Destacado en Inicio', default=False)
    imagen = models.ImageField('Imagen del Servicio', upload_to='servicios/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/servicios/corte_clasico.webp')
    activo = models.BooleanField('Servicio Activo', default=True)
    orden = models.PositiveSmallIntegerField('Orden de Visualización', default=1)

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.duracion_minutos} min - {self.precio_formateado})"

    @property
    def precio_formateado(self):
        return formatear_clp(self.precio)

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        return f"/static/{self.foto_estatica_demo}"


class ServicioSucursal(models.Model):
    """
    Personalización de un servicio para una sucursal específica
    (permite ajustar disponibilidad, precio o duración por sede).
    """
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='sucursal_configs')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='servicios_disponibles')
    disponible = models.BooleanField('Disponible en esta sucursal', default=True)
    precio_personalizado = models.IntegerField('Precio Específico CLP', null=True, blank=True)
    duracion_personalizada = models.PositiveIntegerField('Duración Específica (minutos)', null=True, blank=True)

    class Meta:
        verbose_name = 'Configuración de Servicio por Sucursal'
        verbose_name_plural = 'Configuraciones de Servicios por Sucursal'
        unique_together = ('servicio', 'sucursal')

    def __str__(self):
        return f"{self.servicio.nombre} en {self.sucursal.nombre}"

    def get_precio(self):
        return self.precio_personalizado if self.precio_personalizado is not None else self.servicio.precio

    def get_duracion(self):
        return self.duracion_personalizada if self.duracion_personalizada is not None else self.servicio.duracion_minutos


class ServicioBarbero(models.Model):
    """
    Personalización de un servicio para un barbero específico.
    """
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='barbero_configs')
    barbero = models.ForeignKey(Barbero, on_delete=models.CASCADE, related_name='servicios_realizados')
    disponible = models.BooleanField('El barbero realiza este servicio', default=True)
    precio_personalizado = models.IntegerField('Precio Específico CLP', null=True, blank=True)
    duracion_personalizada = models.PositiveIntegerField('Duración Específica (minutos)', null=True, blank=True)

    class Meta:
        verbose_name = 'Configuración de Servicio por Barbero'
        verbose_name_plural = 'Configuraciones de Servicios por Barbero'
        unique_together = ('servicio', 'barbero')

    def __str__(self):
        return f"{self.servicio.nombre} por {self.barbero.nombre_profesional}"

    def get_precio(self):
        return self.precio_personalizado if self.precio_personalizado is not None else self.servicio.precio

    def get_duracion(self):
        return self.duracion_personalizada if self.duracion_personalizada is not None else self.servicio.duracion_minutos
