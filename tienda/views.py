"""
Vistas para la tienda online y gestión del carrito de compras en sesión
para Demo Barber Club.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from tienda.models import Producto, CategoriaProducto, Pedido, ItemPedido
from sucursales.models import Sucursal
from catalogo.models import formatear_clp


def catalogo_view(request):
    """Listado de productos con filtro por categoría"""
    categoria_slug = request.GET.get('categoria')
    categorias = CategoriaProducto.objects.all().order_by('orden')
    productos = Producto.objects.filter(activo=True).order_by('orden')

    categoria_activa = None
    if categoria_slug:
        categoria_activa = get_object_or_404(CategoriaProducto, slug=categoria_slug)
        productos = productos.filter(categoria=categoria_activa)

    return render(request, 'tienda/catalogo.html', {
        'productos': productos,
        'categorias': categorias,
        'categoria_activa': categoria_activa
    })


def producto_detalle_view(request, slug):
    """Ficha detallada de un producto"""
    producto = get_object_or_404(Producto, slug=slug, activo=True)
    relacionados = Producto.objects.filter(activo=True).exclude(id=producto.id).order_by('?')[:4]

    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'relacionados': relacionados
    })


@require_POST
def agregar_carrito_view(request, producto_id):
    """Agrega un producto al carrito almacenado en la sesión"""
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    cantidad = int(request.POST.get('cantidad', 1))

    if producto.stock < cantidad:
        messages.error(request, f'No hay suficiente stock disponible de {producto.nombre}.')
        return redirect(request.META.get('HTTP_REFERER', 'tienda:catalogo'))

    carrito = request.session.get('carrito', {})
    prod_key = str(producto.id)

    if prod_key in carrito:
        carrito[prod_key]['cantidad'] += cantidad
    else:
        carrito[prod_key] = {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': producto.precio,
            'precio_formateado': producto.precio_formateado,
            'cantidad': cantidad,
            'imagen_url': producto.imagen_url,
            'slug': producto.slug
        }

    request.session['carrito'] = carrito
    request.session.modified = True
    messages.success(request, f'Agregaste "{producto.nombre}" al carrito.')
    return redirect(request.META.get('HTTP_REFERER', 'tienda:ver_carrito'))


def ver_carrito_view(request):
    """Muestra los productos agregados al carrito con totales"""
    carrito = request.session.get('carrito', {})
    items = []
    total = 0

    for k, item in carrito.items():
        subtotal = item['cantidad'] * item['precio']
        total += subtotal
        items.append({
            'producto_id': item['id'],
            'nombre': item['nombre'],
            'precio': item['precio'],
            'precio_formateado': item['precio_formateado'],
            'cantidad': item['cantidad'],
            'subtotal': subtotal,
            'subtotal_formateado': formatear_clp(subtotal),
            'imagen_url': item['imagen_url'],
            'slug': item['slug']
        })

    return render(request, 'tienda/carrito.html', {
        'items': items,
        'total': total,
        'total_formateado': formatear_clp(total)
    })


@require_POST
def actualizar_carrito_view(request, producto_id):
    """Actualiza la cantidad de un ítem en el carrito"""
    cantidad = int(request.POST.get('cantidad', 1))
    carrito = request.session.get('carrito', {})
    prod_key = str(producto_id)

    if prod_key in carrito:
        if cantidad > 0:
            carrito[prod_key]['cantidad'] = cantidad
        else:
            del carrito[prod_key]
        request.session['carrito'] = carrito
        request.session.modified = True
        messages.info(request, 'Carrito actualizado.')

    return redirect('tienda:ver_carrito')


@require_POST
def eliminar_carrito_view(request, producto_id):
    """Elimina un ítem del carrito"""
    carrito = request.session.get('carrito', {})
    prod_key = str(producto_id)

    if prod_key in carrito:
        del carrito[prod_key]
        request.session['carrito'] = carrito
        request.session.modified = True
        messages.info(request, 'Producto eliminado del carrito.')

    return redirect('tienda:ver_carrito')


def checkout_view(request):
    """Pantalla final de checkout para retiro en sucursal"""
    carrito = request.session.get('carrito', {})
    if not carrito:
        messages.warning(request, 'Tu carrito de compras está vacío.')
        return redirect('tienda:catalogo')

    sucursales = Sucursal.objects.filter(activa=True).order_by('orden')
    total = sum(item['cantidad'] * item['precio'] for item in carrito.values())

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        sucursal_id = request.POST.get('sucursal_id')
        metodo_pago = request.POST.get('metodo_pago', Pedido.MetodoPago.LOCAL)
        notas = request.POST.get('notas', '').strip()

        if not all([nombre, email, telefono, sucursal_id]):
            messages.error(request, 'Por favor completa todos los campos requeridos.')
            return redirect('tienda:checkout')

        sucursal = get_object_or_404(Sucursal, id=sucursal_id)

        # Crear pedido de forma atómica y descontar stock
        with transaction.atomic():
            pedido = Pedido.objects.create(
                cliente=request.user if request.user.is_authenticated else None,
                cliente_nombre=nombre,
                cliente_email=email,
                cliente_telefono=telefono,
                sucursal_retiro=sucursal,
                metodo_pago=metodo_pago,
                estado=Pedido.Estado.PENDIENTE,
                total=total,
                notas=notas
            )

            for prod_id_str, item in carrito.items():
                producto = Producto.objects.select_for_update().get(id=int(prod_id_str))
                cant = item['cantidad']
                if producto.stock >= cant:
                    producto.stock -= cant
                    producto.save(update_fields=['stock'])
                else:
                    # En caso de stock insuficiente
                    cant = producto.stock
                    producto.stock = 0
                    producto.save(update_fields=['stock'])

                ItemPedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cant,
                    precio_unitario=item['precio'],
                    subtotal=cant * item['precio']
                )

        # Vaciar carrito de la sesión
        request.session['carrito'] = {}
        request.session.modified = True

        return redirect('tienda:confirmacion_pedido', codigo_pedido=pedido.codigo_pedido)

    return render(request, 'tienda/checkout.html', {
        'sucursales': sucursales,
        'total': total,
        'total_formateado': formatear_clp(total)
    })


def confirmacion_pedido_view(request, codigo_pedido):
    """Pantalla de éxito de pedido de productos"""
    pedido = get_object_or_404(Pedido.objects.prefetch_related('items__producto'), codigo_pedido=codigo_pedido)
    return render(request, 'tienda/confirmacion.html', {'pedido': pedido})
