"""
Módulo de modelos para la app 'contenido'.
Gestiona la configuración global de la barbería (marca, colores, teléfonos, redes sociales),
banners, testimonios de clientes, preguntas frecuentes, galería de fotos y artículos de blog.
"""
from django.db import models
from django.utils.text import slugify


class ConfiguracionSitio(models.Model):
    """
    Configuración global del sitio web (Singleton editable desde el Dashboard).
    Permite personalizar rápidamente la marca, redes sociales, textos del Hero y parámetros de reservas.
    """
    nombre_negocio = models.CharField('Nombre del Negocio', max_length=100, default='Demo Barber Club')
    eslogan = models.CharField('Eslogan / Subtítulo Corto', max_length=200, default='El Arte de la Barbería Tradicional & Contemporánea')
    descripcion_corta = models.TextField(
        'Descripción para SEO y Pie de Página',
        default='Atelier de barbería premium en Santiago de Chile. Cortes de cabello de precisión, afeitado tradicional con toalla caliente y productos exclusivos de cuidado masculino.'
    )
    
    # Contacto y Redes Sociales
    telefono_principal = models.CharField('Teléfono Principal', max_length=25, default='+56 2 2345 6789')
    whatsapp_numero = models.CharField(
        'Número WhatsApp (con código de país, ej: +56912345678)',
        max_length=25,
        default='+56912345678',
        help_text='Si se deja vacío, el botón flotante de WhatsApp no se mostrará.'
    )
    whatsapp_mensaje = models.CharField(
        'Mensaje predeterminado de WhatsApp',
        max_length=255,
        default='Hola, vengo del sitio web y quería hacer una consulta sobre los servicios y reservas.'
    )
    instagram_usuario = models.CharField(
        'Usuario de Instagram (sin @)',
        max_length=50,
        default='demobarberclub.cl',
        help_text='Si se deja vacío, el botón flotante de Instagram no se mostrará.'
    )
    facebook_url = models.URLField('URL de Facebook', blank=True, default='https://facebook.com')
    tiktok_usuario = models.CharField('Usuario de TikTok (sin @)', max_length=50, blank=True)
    email_contacto = models.EmailField('Correo de Contacto', default='contacto@demobarberclub.cl')
    
    # Textos del Hero
    hero_antetitulo = models.CharField('Antetítulo del Hero', max_length=100, default='EXPERIENCIA EXCLUSIVA EN SANTIAGO')
    hero_titulo_parte1 = models.CharField('Título Hero (Parte 1)', max_length=100, default='EL ARTE DE LA')
    hero_titulo_acento = models.CharField('Título Hero en Cursiva Acento', max_length=100, default='Barbería Clásica')
    hero_subtitulo = models.TextField(
        'Subtítulo del Hero',
        default='Cortes de precisión, afeitados con toalla caliente y un espacio diseñado para el confort del caballero moderno.'
    )
    hero_cta_primario = models.CharField('Texto Botón Agendar', max_length=50, default='Agendar Hora')
    hero_cta_secundario = models.CharField('Texto Botón Secundario', max_length=50, default='Ver Servicios')
    
    # Banner Superior de Anuncio
    banner_anuncio_activo = models.BooleanField('Mostrar Banner Superior de Anuncio', default=True)
    banner_anuncio_texto = models.CharField(
        'Texto del Banner de Anuncio',
        max_length=255,
        default='⚡ AGENDA ONLINE Y RECIBE UN CAFÉ DE ESPECIALIDAD DE CORTESÍA EN TU VISITA'
    )
    banner_anuncio_link = models.CharField('Enlace opcional del banner', max_length=255, blank=True, default='#reservas')

    # Parámetros del Motor de Reservas
    horas_minimas_anticipacion = models.PositiveSmallIntegerField(
        'Horas mínimas de anticipación para agendar',
        default=2,
        help_text='No se mostrarán horarios con menos de X horas respecto al momento actual.'
    )
    horas_minimas_cancelacion = models.PositiveSmallIntegerField(
        'Horas mínimas para cancelar o reprogramar sin costo',
        default=4,
        help_text='Tiempo límite en que un cliente puede cancelar su cita.'
    )
    dias_maximos_futuro = models.PositiveSmallIntegerField(
        'Días máximos a futuro permitidos para agendar',
        default=30
    )
    tiempo_descanso_entre_citas_minutos = models.PositiveSmallIntegerField(
        'Minutos de descanso/limpieza entre citas',
        default=10
    )
    
    # Colores y Personalización de Estilo
    color_fondo = models.CharField('Color de Fondo (Hex)', max_length=10, default='#0A0A0A')
    color_acento = models.CharField('Color Acento Dorado (Hex)', max_length=10, default='#C9A24B')
    color_texto = models.CharField('Color Texto Marfil (Hex)', max_length=10, default='#F5F0E6')
    
    # Contadores de Prestigio (Métricas de impacto)
    stat_anios = models.PositiveSmallIntegerField('Años de Trayectoria', default=8)
    stat_clientes = models.PositiveIntegerField('Clientes Atendidos', default=15000)
    stat_cortes = models.PositiveIntegerField('Servicios Realizados', default=32000)
    stat_barberos = models.PositiveSmallIntegerField('Master Barbers', default=9)

    class Meta:
        verbose_name = 'Configuración del Sitio'
        verbose_name_plural = 'Configuración del Sitio'

    def __str__(self):
        return f"Configuración de {self.nombre_negocio}"

    @classmethod
    def get_solo(cls):
        """Retorna la instancia única o la crea si no existe"""
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class Testimonio(models.Model):
    """Reseñas de clientes para generar prueba social"""
    cliente_nombre = models.CharField('Nombre del Cliente', max_length=100)
    cliente_ocupacion = models.CharField('Profesión u Ocupación', max_length=100, blank=True, default='Cliente Frecuente')
    calificacion = models.PositiveSmallIntegerField('Calificación en Estrellas (1-5)', default=5)
    comentario = models.TextField('Testimonio / Comentario')
    servicio_mencionado = models.CharField('Servicio Recibido', max_length=100, default='Combo Signature: Corte + Barba')
    activo = models.BooleanField('Visible en la Web', default=True)
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Testimonio'
        verbose_name_plural = 'Testimonios'
        ordering = ['orden', '-creado_el']

    def __str__(self):
        return f"{self.cliente_nombre} - {'★' * self.calificacion}"


class PreguntaFrecuente(models.Model):
    """Preguntas frecuentes para la sección de acordeón y marcado SEO FAQPage"""
    pregunta = models.CharField('Pregunta', max_length=255)
    respuesta = models.TextField('Respuesta Detallada')
    categoria = models.CharField('Categoría', max_length=50, default='General')
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    activa = models.BooleanField('Visible', default=True)

    class Meta:
        verbose_name = 'Pregunta Frecuente'
        verbose_name_plural = 'Preguntas Frecuentes'
        ordering = ['orden']

    def __str__(self):
        return self.pregunta


class ImagenGaleria(models.Model):
    """Fotografías para la galería y el comparador antes/después"""
    titulo = models.CharField('Título o Estilo', max_length=120)
    categoria = models.CharField('Categoría', max_length=50, default='Cortes')
    imagen = models.ImageField('Fotografía', upload_to='galeria/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/galeria/galeria_1.webp')
    es_antes_despues = models.BooleanField('¿Incluye foto de Antes/Después?', default=False)
    imagen_antes = models.ImageField('Foto Antes (opcional)', upload_to='galeria/antes/', blank=True, null=True)
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    activa = models.BooleanField('Visible', default=True)

    class Meta:
        verbose_name = 'Imagen de Galería'
        verbose_name_plural = 'Galería de Trabajos'
        ordering = ['orden']

    def __str__(self):
        return self.titulo

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        return f"/static/{self.foto_estatica_demo}"


class EntradaBlog(models.Model):
    """Artículos informativos y de visagismo con SEO optimizado"""
    titulo = models.CharField('Título del Artículo', max_length=200)
    slug = models.SlugField('Slug para URL', max_length=220, unique=True, blank=True)
    extracto = models.TextField('Extracto / Resumen corto')
    contenido = models.TextField('Contenido Completo (HTML o Texto)')
    imagen_portada = models.ImageField('Imagen de Portada', upload_to='blog/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/blog/guia_cuidado_barba.webp')
    autor = models.CharField('Autor del Artículo', max_length=100, default='Equipo Demo Barber Club')
    tiempo_lectura_minutos = models.PositiveSmallIntegerField('Tiempo de Lectura (min)', default=4)
    publicado = models.BooleanField('Publicado', default=True)
    creado_el = models.DateTimeField('Fecha de Publicación', auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrada de Blog'
        verbose_name_plural = 'Entradas de Blog'
        ordering = ['-creado_el']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        return f"/static/{self.foto_estatica_demo}"
