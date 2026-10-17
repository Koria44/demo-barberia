"""
URL configuration for demo_barber project.
Define el enrutamiento principal para el sitio público, reservas, tienda, cuentas,
dashboard de administración propio (/panel/), sitemap.xml y robots.txt.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from sucursales.models import Sucursal
from catalogo.models import Servicio
from tienda.models import Producto
from contenido.models import EntradaBlog


def robots_txt(request):
    """Genera dinámicamente robots.txt bloqueando áreas administrativas y APIs"""
    lines = [
        "User-agent: *",
        "Disallow: /panel/",
        "Disallow: /cuenta/",
        "Disallow: /mi-cuenta/",
        "Disallow: /reservas/api/",
        "Disallow: /admin/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    """Sitemap dinámico en formato XML para motores de búsqueda (Google, Bing)"""
    dominio = f"{request.scheme}://{request.get_host()}"
    urls = [
        {'loc': f"{dominio}/", 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': f"{dominio}/reservas/agendar/", 'priority': '0.9', 'changefreq': 'weekly'},
        {'loc': f"{dominio}/tienda/", 'priority': '0.8', 'changefreq': 'weekly'},
        {'loc': f"{dominio}/blog/", 'priority': '0.7', 'changefreq': 'weekly'},
    ]

    # Sucursales
    for s in Sucursal.objects.filter(activa=True):
        urls.append({
            'loc': f"{dominio}/sucursales/{s.slug}/",
            'priority': '0.8',
            'changefreq': 'monthly'
        })

    # Productos
    for p in Producto.objects.filter(activo=True):
        urls.append({
            'loc': f"{dominio}/tienda/producto/{p.slug}/",
            'priority': '0.7',
            'changefreq': 'weekly'
        })

    # Artículos de blog
    for art in EntradaBlog.objects.filter(publicado=True):
        urls.append({
            'loc': f"{dominio}/blog/{art.slug}/",
            'priority': '0.6',
            'changefreq': 'monthly'
        })

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        xml_lines.append('  <url>')
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append('  </url>')
    xml_lines.append('</urlset>')

    return HttpResponse("\n".join(xml_lines), content_type="application/xml")


# Manejadores de error personalizados
handler404 = 'contenido.views.error_404_view'
handler500 = 'contenido.views.error_500_view'

urlpatterns = [
    # Panel técnico de Django (restringido a superusuario técnico)
    path('admin/', admin.site.urls),

    # SEO: robots.txt y sitemap.xml
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),

    # Dashboard propio de la barbería
    path('panel/', include('panel.urls', namespace='panel')),

    # Cuentas, autenticación y perfil
    path('', include('cuentas.urls', namespace='cuentas')),

    # Sistema de agendamiento y reservas
    path('reservas/', include('reservas.urls', namespace='reservas')),

    # Tienda online y productos
    path('tienda/', include('tienda.urls', namespace='tienda')),

    # Sitio público principal (One-page, blog, sucursales, contacto)
    path('', include('contenido.urls', namespace='sitio_publico')),
]

# Servir archivos subidos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
