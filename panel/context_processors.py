"""
Context Processors para el Dashboard de Administración (/panel/).
Inyecta automáticamente información del alcance por sucursal, rol de usuario
y contadores de alerta para el menú lateral y selector global del panel.
"""
from panel.alcance import obtener_sucursales_permitidas, obtener_sucursal_activa_id
from sucursales.models import Sucursal


def panel_scope_context(request):
    """Contexto global para plantillas del panel"""
    if not request.path.startswith('/panel/'):
        return {}

    usuario = request.user
    if not usuario.is_authenticated or not usuario.es_administrador:
        return {}

    permitidas = obtener_sucursales_permitidas(usuario)
    activa_id = obtener_sucursal_activa_id(request)
    sucursal_activa = None
    if activa_id:
        sucursal_activa = permitidas.filter(id=activa_id).first()

    # Contador de productos en stock bajo según sedes permitidas
    from tienda.models import Producto
    stock_bajo_count = 0
    try:
        # Si existe modelo StockSucursal, contar según sucursal
        from tienda.models import StockSucursal
        if activa_id:
            stock_bajo_count = StockSucursal.objects.filter(
                sucursal_id=activa_id,
                cantidad__lte=5
            ).count()
        elif usuario.es_admin_sucursal:
            stock_bajo_count = StockSucursal.objects.filter(
                sucursal__in=permitidas,
                cantidad__lte=5
            ).count()
        else:
            stock_bajo_count = StockSucursal.objects.filter(cantidad__lte=5).count()
    except Exception:
        stock_bajo_count = Producto.objects.filter(stock__lte=5, activo=True).count()

    return {
        'panel_sucursales_permitidas': permitidas,
        'panel_sucursal_activa_id': activa_id,
        'panel_sucursal_activa': sucursal_activa,
        'es_admin_maestro': usuario.es_admin_maestro,
        'es_admin_sucursal': usuario.es_admin_sucursal,
        'stock_bajo_total_count': stock_bajo_count,
    }
