from django.db import models


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    descripcion = models.CharField(max_length=100, verbose_name='Descripción')
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Unidad de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion


class Proveedor(models.Model):
    cedula_rnc = models.CharField(
        max_length=15, unique=True, verbose_name='Cédula / RNC'
    )
    nombre_comercial = models.CharField(max_length=150, verbose_name='Nombre Comercial')
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre_comercial']

    def __str__(self):
        return f'{self.nombre_comercial} ({self.cedula_rnc})'


class Articulo(models.Model):
    descripcion = models.CharField(max_length=200, verbose_name='Descripción')
    marca = models.CharField(max_length=100, verbose_name='Marca')
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        verbose_name='Unidad de Medida',
        related_name='articulos',
    )
    existencia = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Existencia'
    )
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'
        ordering = ['descripcion']

    def __str__(self):
        return f'{self.descripcion} — {self.marca}'


class OrdenCompra(models.Model):
    ESTADO_PENDIENTE = 'PE'
    ESTADO_APROBADA = 'AP'
    ESTADO_RECHAZADA = 'RE'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    ]

    fecha_orden = models.DateField(auto_now_add=True, verbose_name='Fecha de Orden')
    estado = models.CharField(
        max_length=2,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        verbose_name='Estado',
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        verbose_name='Proveedor',
        related_name='ordenes',
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        verbose_name='Departamento',
        related_name='ordenes',
    )

    class Meta:
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'
        ordering = ['-fecha_orden']

    def __str__(self):
        return f'OC-{self.pk:05d} | {self.get_estado_display()} | {self.fecha_orden}'

    def total(self):
        return sum(d.subtotal() for d in self.detalles.all())


class OrdenCompraDetalle(models.Model):
    orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Orden de Compra',
    )
    articulo = models.ForeignKey(
        Articulo,
        on_delete=models.PROTECT,
        verbose_name='Artículo',
    )
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Cantidad'
    )
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        verbose_name='Unidad de Medida',
    )
    costo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Costo Unitario'
    )

    class Meta:
        verbose_name = 'Detalle de Orden'
        verbose_name_plural = 'Detalles de Orden'

    def __str__(self):
        return f'{self.articulo} x {self.cantidad}'

    def subtotal(self):
        return self.cantidad * self.costo_unitario


class AsientoContable(models.Model):
    TIPO_DB = 'DB'
    TIPO_CR = 'CR'
    TIPO_MOVIMIENTO_CHOICES = [
        (TIPO_DB, 'Débito'),
        (TIPO_CR, 'Crédito'),
    ]

    descripcion = models.CharField(max_length=200, verbose_name='Descripción')
    tipo_inventario = models.IntegerField(verbose_name='ID Tipo de Inventario')
    cuenta_contable = models.CharField(max_length=20, verbose_name='Cuenta Contable')
    tipo_movimiento = models.CharField(
        max_length=2,
        choices=TIPO_MOVIMIENTO_CHOICES,
        verbose_name='Tipo de Movimiento',
    )
    fecha = models.DateField(verbose_name='Fecha del Asiento')
    monto = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Monto'
    )
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'
        ordering = ['-fecha']

    def __str__(self):
        return f'AC-{self.pk:05d} | {self.descripcion} | {self.get_tipo_movimiento_display()}'
