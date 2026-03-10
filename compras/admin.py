from django.contrib import admin

from .models import (
    Articulo,
    AsientoContable,
    Departamento,
    OrdenCompra,
    OrdenCompraDetalle,
    Proveedor,
    UnidadMedida,
)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    list_editable = ('estado',)


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('id', 'descripcion', 'estado')
    list_filter = ('estado',)
    search_fields = ('descripcion',)
    list_editable = ('estado',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo_documento', 'cedula_rnc', 'nombre_comercial', 'estado')
    list_filter = ('tipo_documento', 'estado')
    search_fields = ('cedula_rnc', 'nombre_comercial')
    list_editable = ('estado',)


@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'descripcion',
        'marca',
        'unidad_medida',
        'existencia',
        'cantidad_retenida',
        'disponible',
        'estado',
    )
    list_filter = ('estado', 'unidad_medida')
    search_fields = ('descripcion', 'marca')
    list_editable = ('estado',)


class OrdenCompraDetalleInline(admin.TabularInline):
    model = OrdenCompraDetalle
    extra = 1
    fields = ('articulo', 'cantidad', 'unidad_medida', 'costo_unitario')


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_orden', 'proveedor', 'departamento', 'estado')
    list_filter = ('estado', 'departamento', 'proveedor')
    search_fields = ('proveedor__nombre_comercial', 'departamento__nombre')
    inlines = [OrdenCompraDetalleInline]


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'descripcion', 'cuenta_contable', 'tipo_movimiento',
        'fecha', 'monto', 'estado',
    )
    list_filter = ('estado', 'tipo_movimiento')
    search_fields = ('descripcion', 'cuenta_contable')
