"""
Vistas públicas del sitio web para Demo Barber Club.
Renderiza la portada principal editorial de alta gama, landings por sucursal,
blog y formulario de contacto.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from contenido.models import (
    ConfiguracionSitio,
    Testimonio,
    PreguntaFrecuente,
    ImagenGaleria,
    EntradaBlog
)
from sucursales.models import Sucursal
from barberos.models import Barbero
from catalogo.models import Servicio
from tienda.models import Producto


def inicio_view(request):
    """
    Página principal editorial de lujo (One-Page integrada con todas las secciones).
    """
    config = ConfiguracionSitio.get_solo()
    sucursales = Sucursal.objects.filter(activa=True).order_by('orden')
    servicios = Servicio.objects.filter(activo=True).order_by('orden')
    barberos = Barbero.objects.filter(activo=True).select_related('usuario').prefetch_related('sucursales').order_by('orden')
    productos_destacados = Producto.objects.filter(activo=True, destacado=True).order_by('orden')[:4]
    testimonios = Testimonio.objects.filter(activo=True).order_by('orden')
    faqs = PreguntaFrecuente.objects.filter(activa=True).order_by('orden')
    galeria = ImagenGaleria.objects.filter(activa=True).order_by('orden')
    articulos_blog = EntradaBlog.objects.filter(publicado=True).order_by('-creado_el')[:3]

    return render(request, 'sitio/inicio.html', {
        'sitio': config,
        'sucursales': sucursales,
        'servicios': servicios,
        'barberos': barberos,
        'productos_destacados': productos_destacados,
        'testimonios': testimonios,
        'faqs': faqs,
        'galeria': galeria,
        'articulos_blog': articulos_blog,
    })


def sucursal_detalle_view(request, slug):
    """
    Landing SEO optimizada para cada sucursal física (/sucursales/<slug>/).
    Incluye datos locales, mapa y barberos de la sede.
    """
    sucursal = get_object_or_404(Sucursal, slug=slug, activa=True)
    barberos = sucursal.barberos.filter(activo=True)
    servicios = Servicio.objects.filter(activo=True).order_by('orden')
    config = ConfiguracionSitio.get_solo()

    return render(request, 'sitio/sucursal_detalle.html', {
        'sucursal': sucursal,
        'barberos': barberos,
        'servicios': servicios,
        'sitio': config,
    })


def blog_lista_view(request):
    """Listado completo de artículos de blog y visagismo"""
    articulos = EntradaBlog.objects.filter(publicado=True).order_by('-creado_el')
    config = ConfiguracionSitio.get_solo()
    return render(request, 'sitio/blog_lista.html', {
        'articulos': articulos,
        'sitio': config,
    })


def blog_detalle_view(request, slug):
    """Detalle de un artículo de blog con marcado Schema BlogPosting"""
    articulo = get_object_or_404(EntradaBlog, slug=slug, publicado=True)
    articulos_recientes = EntradaBlog.objects.filter(publicado=True).exclude(id=articulo.id).order_by('-creado_el')[:3]
    config = ConfiguracionSitio.get_solo()

    return render(request, 'sitio/blog_detalle.html', {
        'articulo': articulo,
        'articulos_recientes': articulos_recientes,
        'sitio': config,
    })


def contacto_submit_view(request):
    """Procesamiento de formulario de contacto de la portada"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        if nombre and email and mensaje:
            messages.success(request, f'¡Gracias {nombre}! Hemos recibido tu consulta. Nos pondremos en contacto contigo a la brevedad.')
        else:
            messages.error(request, 'Por favor completa todos los campos requeridos del formulario de contacto.')

    return redirect('sitio_publico:inicio')
