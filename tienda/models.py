"""
Módulo de modelos para la app 'tienda'.
Gestiona el catálogo de productos de cuidado masculino, inventario, pedidos e ítems.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from sucursales.models import Sucursal
from catalogo.models import formatear_clp


class CategoriaProducto(models.Model):
    """Categoría para agrupar productos (Pomadas, Barba, Afeitado, Accesorios)"""
    nombre = models.CharField('Nombre de Categoría', max_length=100)
    slug = models.SlugField('Slug', unique=True, blank=True)
    orden = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """
    Producto físico disponible para venta en la tienda de la barbería.
    """
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name='Categoría'
    )
    nombre = models.CharField('Nombre del Producto', max_length=150)
    slug = models.SlugField('Slug para URL', max_length=160, unique=True, blank=True)
    descripcion = models.TextField('Descripción Detallada')
    precio = models.IntegerField('Precio en CLP (ej. 14990)', default=14990)
    precio_costo = models.IntegerField('Precio de Costo CLP (para margen)', null=True, blank=True)
    sku = models.CharField('Código SKU', max_length=50, blank=True, db_index=True)
    stock = models.PositiveIntegerField('Unidades en Stock Global', default=20)
    stock_minimo_alerta = models.PositiveIntegerField('Umbral de Alerta de Stock Bajo', default=5)
    destacado = models.BooleanField('Producto Destacado en Portada', default=False)
    imagen = models.ImageField('Fotografía Principal', upload_to='productos/', blank=True, null=True)
    foto_estatica_demo = models.CharField('Ruta estática de demo', max_length=255, blank=True, default='img/productos/pomada_mate.webp')
    activo = models.BooleanField('Disponible para la Venta', default=True)
    orden = models.PositiveSmallIntegerField('Orden de Visualización', default=1)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['orden', 'nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.precio_formateado})"

    @property
    def precio_formateado(self):
        return formatear_clp(self.precio)

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        return f"/static/{self.foto_estatica_demo}"

    @property
    def en_alerta_stock(self):
        return self.stock <= self.stock_minimo_alerta


class Pedido(models.Model):
    """
    Orden de compra generada por un cliente o invitado.
    """
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Pago'
        PAGADO = 'PAGADO', 'Pagado'
        LISTO_PARA_RETIRO = 'LISTO_PARA_RETIRO', 'Listo para Retiro en Sucursal'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    class MetodoPago(models.TextChoices):
        LOCAL = 'LOCAL', 'Pago en el local al retirar'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia bancaria previa'
        WEBPAY = 'WEBPAY', 'Webpay Plus / Flow (Próximamente)'

    codigo_pedido = models.CharField('Código de Pedido', max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos'
    )
    cliente_nombre = models.CharField('Nombre Completo', max_length=120)
    cliente_email = models.EmailField('Correo Electrónico')
    cliente_telefono = models.CharField('Teléfono / WhatsApp', max_length=25)

    sucursal_retiro = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='pedidos_retiro',
        verbose_name='Sucursal de Retiro'
    )
    metodo_pago = models.CharField('Método de Pago', max_length=25, choices=MetodoPago.choices, default=MetodoPago.LOCAL)
    estado = models.CharField('Estado del Pedido', max_length=25, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.IntegerField('Monto Total CLP', default=0)
    notas = models.TextField('Notas del Pedido', blank=True)

    creado_el = models.DateTimeField('Fecha de Compra', auto_now_add=True)
    actualizado_el = models.DateTimeField('Última Actualización', auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-creado_el']

    def save(self, *args, **kwargs):
        if not self.codigo_pedido:
            import random
            num = random.randint(1000, 9999)
            self.codigo_pedido = f"PED-{num}"
            while Pedido.objects.filter(codigo_pedido=self.codigo_pedido).exists():
                num = random.randint(1000, 9999)
                self.codigo_pedido = f"PED-{num}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_pedido} - {self.cliente_nombre} ({self.total_formateado})"

    @property
    def total_formateado(self):
        return formatear_clp(self.total)


class ItemPedido(models.Model):
    """
    Línea de detalle de productos contenidos en un pedido.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='ventas')
    cantidad = models.PositiveIntegerField('Cantidad', default=1)
    precio_unitario = models.IntegerField('Precio Unitario CLP')
    subtotal = models.IntegerField('Subtotal CLP')

    class Meta:
        verbose_name = 'Ítem de Pedido'
        verbose_name_plural = 'Ítems de Pedidos'

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} ({formatear_clp(self.subtotal)})"


class ProductoImagen(models.Model):
    """Galería de imágenes adicionales de un producto"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes_galeria')
    imagen = models.ImageField('Fotografía de Detalle', upload_to='productos/galeria/')
    orden = models.PositiveSmallIntegerField('Orden', default=1)

    class Meta:
        verbose_name = 'Imagen de Producto'
        verbose_name_plural = 'Imágenes de Productos'
        ordering = ['orden']


class StockSucursal(models.Model):
    """
    Control de inventario de un producto en una sucursal específica.
    Permite stock independiente en cada sede.
    """
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks_sucursal', verbose_name='Producto')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='stocks_producto', verbose_name='Sucursal')
    cantidad = models.IntegerField('Cantidad en Stock', default=0)
    stock_minimo_alerta = models.PositiveIntegerField('Umbral de Alerta de Stock Bajo', default=5)

    class Meta:
        verbose_name = 'Stock por Sucursal'
        verbose_name_plural = 'Stocks por Sucursal'
        unique_together = ('producto', 'sucursal')
        ordering = ['sucursal', 'producto']

    def __str__(self):
        return f"{self.producto.nombre} en {self.sucursal.nombre}: {self.cantidad} uds"

    @property
    def en_alerta(self):
        return self.cantidad <= self.stock_minimo_alerta

    @property
    def estado_stock(self):
        if self.cantidad <= 0:
            return 'AGOTADO'
        elif self.cantidad <= self.stock_minimo_alerta:
            return 'BAJO'
        return 'OK'


class MovimientoStock(models.Model):
    """
    Registro histórico inmutable de auditoría para cada movimiento de inventario.
    El stock actual siempre se modifica a través de estos movimientos sin permitir stock negativo.
    """
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada (Compra / Reposición)'
        SALIDA = 'SALIDA', 'Salida (Merma / Uso interno)'
        AJUSTE = 'AJUSTE', 'Ajuste de Inventario'
        VENTA = 'VENTA', 'Venta en Tienda'
        DEVOLUCION = 'DEVOLUCION', 'Devolución de Pedido'
        TRASLADO = 'TRASLADO', 'Traslado entre Sucursales'

    tipo = models.CharField('Tipo de Movimiento', max_length=20, choices=Tipo.choices)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos_stock', verbose_name='Producto')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='movimientos_stock', verbose_name='Sucursal Afectada / Origen')
    sucursal_destino = models.ForeignKey(
        Sucursal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='traslados_stock_recibidos',
        verbose_name='Sucursal Destino (solo para traslados)'
    )
    cantidad = models.IntegerField('Cantidad Involucrada (positiva)')
    stock_resultante = models.IntegerField('Stock Resultante en la Sucursal', default=0)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuario Responsable'
    )
    fecha = models.DateTimeField('Fecha y Hora', auto_now_add=True)
    motivo = models.CharField('Motivo del Movimiento', max_length=200)
    nota = models.TextField('Notas de Auditoría', blank=True)

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad} uds) en {self.sucursal.nombre}"


def registrar_movimiento_stock(producto, sucursal, tipo, cantidad, usuario=None, motivo="", nota="", sucursal_destino=None):
    """
    Registra atómicamente un movimiento de stock garantizando que nunca quede negativo.
    Actualiza el stock local por sucursal y el stock global agregado del producto.
    """
    from django.db import transaction
    if cantidad <= 0 and tipo != MovimientoStock.Tipo.AJUSTE:
        raise ValueError("La cantidad involucrada debe ser un entero positivo mayor a cero.")

    with transaction.atomic():
        stock_obj, _ = StockSucursal.objects.select_for_update().get_or_create(
            producto=producto,
            sucursal=sucursal,
            defaults={'cantidad': 0, 'stock_minimo_alerta': producto.stock_minimo_alerta}
        )

        if tipo in (MovimientoStock.Tipo.ENTRADA, MovimientoStock.Tipo.DEVOLUCION):
            stock_obj.cantidad += cantidad
        elif tipo in (MovimientoStock.Tipo.SALIDA, MovimientoStock.Tipo.VENTA):
            if stock_obj.cantidad < cantidad:
                raise ValueError(f"Stock insuficiente en {sucursal.nombre}: disponible {stock_obj.cantidad}, requerido {cantidad}.")
            stock_obj.cantidad -= cantidad
        elif tipo == MovimientoStock.Tipo.AJUSTE:
            if cantidad < 0:
                raise ValueError("El nuevo stock ajustado no puede ser negativo.")
            stock_obj.cantidad = cantidad
        elif tipo == MovimientoStock.Tipo.TRASLADO:
            if not sucursal_destino:
                raise ValueError("Se requiere una sucursal destino para traslados.")
            if sucursal_destino.id == sucursal.id:
                raise ValueError("La sucursal destino debe ser distinta a la sucursal origen.")
            if stock_obj.cantidad < cantidad:
                raise ValueError(f"Stock insuficiente en {sucursal.nombre} para trasladar: disponible {stock_obj.cantidad}, requerido {cantidad}.")
            stock_obj.cantidad -= cantidad
            stock_obj.save(update_fields=['cantidad'])

            # Registrar salida por traslado en sucursal origen
            mov_origen = MovimientoStock.objects.create(
                tipo=MovimientoStock.Tipo.TRASLADO,
                producto=producto,
                sucursal=sucursal,
                sucursal_destino=sucursal_destino,
                cantidad=cantidad,
                stock_resultante=stock_obj.cantidad,
                usuario=usuario,
                motivo=motivo or f"Traslado hacia {sucursal_destino.nombre}",
                nota=nota
            )

            # Destino: sumar stock y registrar recepción
            stock_dest, _ = StockSucursal.objects.select_for_update().get_or_create(
                producto=producto,
                sucursal=sucursal_destino,
                defaults={'cantidad': 0, 'stock_minimo_alerta': producto.stock_minimo_alerta}
            )
            stock_dest.cantidad += cantidad
            stock_dest.save(update_fields=['cantidad'])

            MovimientoStock.objects.create(
                tipo=MovimientoStock.Tipo.ENTRADA,
                producto=producto,
                sucursal=sucursal_destino,
                cantidad=cantidad,
                stock_resultante=stock_dest.cantidad,
                usuario=usuario,
                motivo=f"Recepción de traslado desde {sucursal.nombre}",
                nota=nota
            )

            # Sincronizar stock total del producto
            total_stock = sum(StockSucursal.objects.filter(producto=producto).values_list('cantidad', flat=True))
            producto.stock = total_stock
            producto.save(update_fields=['stock'])
            return mov_origen

        stock_obj.save(update_fields=['cantidad'])

        mov = MovimientoStock.objects.create(
            tipo=tipo,
            producto=producto,
            sucursal=sucursal,
            sucursal_destino=sucursal_destino,
            cantidad=cantidad,
            stock_resultante=stock_obj.cantidad,
            usuario=usuario,
            motivo=motivo,
            nota=nota
        )

        total_stock = sum(StockSucursal.objects.filter(producto=producto).values_list('cantidad', flat=True))
        producto.stock = total_stock
        producto.save(update_fields=['stock'])

        return mov

