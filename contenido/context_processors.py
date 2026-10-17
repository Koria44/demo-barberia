"""
Procesadores de contexto globales para Demo Barber Club.
Inyecta la configuración del sitio (teléfonos, WhatsApp, Instagram, logo, textos)
y los datos del carrito de compras en todas las plantillas.
"""
from contenido.models import ConfiguracionSitio


def site_context(request):
    """
    Inyecta la instancia única de ConfiguracionSitio y el estado del carrito
    para que el header, footer y botones flotantes siempre dispongan de información.
    """
    try:
        config = ConfiguracionSitio.get_solo()
    except Exception:
        config = None

    # Carrito guardado en la sesión
    carrito = request.session.get('carrito', {})
    total_items_carrito = sum(item.get('cantidad', 1) for item in carrito.values())
    total_monto_carrito = sum(item.get('cantidad', 1) * item.get('precio', 0) for item in carrito.values())

    return {
        'sitio': config,
        'carrito_items_count': total_items_carrito,
        'carrito_total_monto': total_monto_carrito,
    }
