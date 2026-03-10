from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Value
from django.db.models.functions import Replace

from .validators import (
    formatear_documento_dominicano,
    limpiar_documento,
    validar_cedula_dominicana,
    validar_rnc_dominicano,
)


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
    TIPO_CEDULA = 'CED'
    TIPO_RNC = 'RNC'
    TIPO_DOCUMENTO_CHOICES = [
        (TIPO_CEDULA, 'Cédula'),
        (TIPO_RNC, 'RNC'),
    ]

    tipo_documento = models.CharField(
        max_length=3,
        choices=TIPO_DOCUMENTO_CHOICES,
        default=TIPO_RNC,
        verbose_name='Tipo de Documento',
    )
    cedula_rnc = models.CharField(
        max_length=13,
        unique=True,
        verbose_name='Documento',
    )
    nombre_comercial = models.CharField(max_length=150, verbose_name='Nombre Comercial')
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre_comercial']

    def _normalizar_documento(self):
        documento_limpio = limpiar_documento(self.cedula_rnc)

        if self.tipo_documento == self.TIPO_CEDULA:
            documento_limpio = validar_cedula_dominicana(documento_limpio)
        elif self.tipo_documento == self.TIPO_RNC:
            documento_limpio = validar_rnc_dominicano(documento_limpio)
        else:
            raise ValidationError({'tipo_documento': 'Tipo de documento no válido.'})

        existe_documento = (
            Proveedor.objects
            .exclude(pk=self.pk)
            .annotate(documento_limpio=Replace('cedula_rnc', Value('-'), Value('')))
            .filter(documento_limpio=documento_limpio)
            .exists()
        )
        if existe_documento:
            raise ValidationError({'cedula_rnc': 'Ya existe un proveedor con este documento.'})

        self.cedula_rnc = formatear_documento_dominicano(self.tipo_documento, documento_limpio)

    def clean(self):
        self._normalizar_documento()

    def save(self, *args, **kwargs):
        self._normalizar_documento()
        return super().save(*args, **kwargs)

    @property
    def documento_formateado(self):
        return formatear_documento_dominicano(self.tipo_documento, self.cedula_rnc)

    def __str__(self):
        return f'{self.nombre_comercial} ({self.documento_formateado})'


class Articulo(models.Model):
    descripcion = models.CharField(max_length=200, verbose_name='Descripción')
    marca = models.CharField(max_length=100, verbose_name='Marca')
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        verbose_name='Unidad de Medida',
        related_name='articulos',
    )
    existencia = models.PositiveIntegerField(
        default=0,
        verbose_name='Existencia',
    )
    cantidad_retenida = models.PositiveIntegerField(
        default=0,
        verbose_name='Cantidad en Hold',
    )
    estado = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'
        ordering = ['descripcion']

    @property
    def disponible(self):
        return max(self.existencia - self.cantidad_retenida, 0)

    def __str__(self):
        return f'{self.descripcion} - {self.marca}'


class OrdenCompra(models.Model):
    ESTADO_PENDIENTE = 'PE'
    ESTADO_APROBADA = 'AP'
    ESTADO_COMPLETADA = 'CO'
    ESTADO_RECHAZADA = 'RE'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_COMPLETADA, 'Completada'),
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
    cantidad = models.PositiveIntegerField(
        verbose_name='Cantidad'
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
    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asientos_contables',
        verbose_name='Orden de Compra Relacionada',
    )

    class Meta:
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'
        ordering = ['-fecha']

    def __str__(self):
        return f'AC-{self.pk:05d} | {self.descripcion} | {self.get_tipo_movimiento_display()}'
