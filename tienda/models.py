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
    stock = models.PositiveIntegerField('Unidades en Stock', default=20)
    stock_minimo_alerta = models.PositiveIntegerField('Umbral de Alerta de Stock Bajo', default=5)
    destacado = models.BooleanField('Producto Destacado en Portada', default=False)
    imagen = models.ImageField('Fotografía del Producto', upload_to='productos/', blank=True, null=True)
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
