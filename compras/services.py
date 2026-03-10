from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import Articulo, AsientoContable, OrdenCompra


TRANSICIONES_VALIDAS = {
    OrdenCompra.ESTADO_PENDIENTE: {
        OrdenCompra.ESTADO_APROBADA,
        OrdenCompra.ESTADO_RECHAZADA,
    },
    OrdenCompra.ESTADO_APROBADA: {
        OrdenCompra.ESTADO_RECHAZADA,
        OrdenCompra.ESTADO_COMPLETADA,
    },
    OrdenCompra.ESTADO_RECHAZADA: {
        OrdenCompra.ESTADO_PENDIENTE,
    },
    OrdenCompra.ESTADO_COMPLETADA: set(),
}


TIPO_INVENTARIO_GENERAL = 1
CUENTA_CONTABLE_INVENTARIO = '110101'
CUENTA_CONTABLE_CXP = '210101'


def _resumen_detalles(orden):
    resumen = (
        orden.detalles.values('articulo_id')
        .annotate(total=Sum('cantidad'))
        .order_by('articulo_id')
    )
    return {fila['articulo_id']: int(fila['total'] or 0) for fila in resumen}


def _bloquear_articulos(articulo_ids):
    articulos = Articulo.objects.select_for_update().filter(id__in=articulo_ids)
    return {articulo.id: articulo for articulo in articulos}


def _aplicar_hold(articulos, cantidades):
    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        disponible = articulo.existencia - articulo.cantidad_retenida
        if cantidad > disponible:
            raise ValidationError(
                f'Inventario insuficiente para "{articulo.descripcion}". '
                f'Disponible: {disponible}, requerido: {cantidad}.'
            )

    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        articulo.cantidad_retenida += cantidad
        articulo.save(update_fields=['cantidad_retenida'])


def _liberar_hold(articulos, cantidades):
    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        articulo.cantidad_retenida = max(articulo.cantidad_retenida - cantidad, 0)
        articulo.save(update_fields=['cantidad_retenida'])


def _consumir_orden_aprobada(articulos, cantidades):
    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        if articulo.cantidad_retenida < cantidad:
            raise ValidationError(
                f'La orden no tiene hold suficiente para "{articulo.descripcion}".'
            )
        if articulo.existencia < cantidad:
            raise ValidationError(
                f'Inventario insuficiente para completar "{articulo.descripcion}".'
            )

    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        articulo.cantidad_retenida -= cantidad
        articulo.existencia -= cantidad
        articulo.save(update_fields=['cantidad_retenida', 'existencia'])


def _monto_total_orden(orden):
    detalles = orden.detalles.all()
    return sum((detalle.subtotal() for detalle in detalles), Decimal('0'))


def _crear_o_actualizar_asientos_orden_completada(orden):
    monto_total = _monto_total_orden(orden)
    if monto_total <= 0:
        raise ValidationError('No se puede generar asiento para una orden sin monto total válido.')

    codigo_orden = f'OC-{orden.pk:05d}'
    descripcion_db = f'{codigo_orden} - Compra inventario'[:200]
    descripcion_cr = f'{codigo_orden} - CxP proveedor'[:200]

    fecha_asiento = orden.fecha_orden

    _, db_creado = AsientoContable.objects.update_or_create(
        orden_compra=orden,
        tipo_movimiento=AsientoContable.TIPO_DB,
        defaults={
            'descripcion': descripcion_db,
            'tipo_inventario': TIPO_INVENTARIO_GENERAL,
            'cuenta_contable': CUENTA_CONTABLE_INVENTARIO,
            'fecha': fecha_asiento,
            'monto': monto_total,
            'estado': True,
        },
    )

    _, cr_creado = AsientoContable.objects.update_or_create(
        orden_compra=orden,
        tipo_movimiento=AsientoContable.TIPO_CR,
        defaults={
            'descripcion': descripcion_cr,
            'tipo_inventario': TIPO_INVENTARIO_GENERAL,
            'cuenta_contable': CUENTA_CONTABLE_CXP,
            'fecha': fecha_asiento,
            'monto': monto_total,
            'estado': True,
        },
    )

    return {
        'creados': int(db_creado) + int(cr_creado),
        'actualizados': int(not db_creado) + int(not cr_creado),
    }


def cambiar_estado_orden(orden, nuevo_estado):
    estados_validos = {codigo for codigo, _ in OrdenCompra.ESTADO_CHOICES}
    if nuevo_estado not in estados_validos:
        raise ValidationError('Estado de orden inválido.')

    with transaction.atomic():
        orden = OrdenCompra.objects.select_for_update().get(pk=orden.pk)
        estado_actual = orden.estado

        if nuevo_estado == estado_actual:
            return orden

        if nuevo_estado not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
            raise ValidationError(
                f'No se permite mover una orden de {orden.get_estado_display()} '
                f'a {dict(OrdenCompra.ESTADO_CHOICES).get(nuevo_estado, nuevo_estado)}.'
            )

        cantidades = _resumen_detalles(orden)
        articulos = _bloquear_articulos(cantidades.keys())

        if estado_actual in {OrdenCompra.ESTADO_PENDIENTE, OrdenCompra.ESTADO_RECHAZADA} and nuevo_estado == OrdenCompra.ESTADO_APROBADA:
            _aplicar_hold(articulos, cantidades)
        elif estado_actual == OrdenCompra.ESTADO_APROBADA and nuevo_estado in {OrdenCompra.ESTADO_PENDIENTE, OrdenCompra.ESTADO_RECHAZADA}:
            _liberar_hold(articulos, cantidades)
        elif estado_actual == OrdenCompra.ESTADO_APROBADA and nuevo_estado == OrdenCompra.ESTADO_COMPLETADA:
            _consumir_orden_aprobada(articulos, cantidades)

        orden.estado = nuevo_estado
        orden.save(update_fields=['estado'])

        if nuevo_estado == OrdenCompra.ESTADO_COMPLETADA:
            _crear_o_actualizar_asientos_orden_completada(orden)

    return orden


def sincronizar_asientos_ordenes_completadas():
    resumen = {'ordenes_procesadas': 0, 'asientos_creados': 0, 'asientos_actualizados': 0}

    ordenes = OrdenCompra.objects.filter(estado=OrdenCompra.ESTADO_COMPLETADA)
    for orden in ordenes:
        resultado = _crear_o_actualizar_asientos_orden_completada(orden)
        resumen['ordenes_procesadas'] += 1
        resumen['asientos_creados'] += resultado['creados']
        resumen['asientos_actualizados'] += resultado['actualizados']

    return resumen


def liberar_hold_si_aprobada(orden):
    if orden.estado != OrdenCompra.ESTADO_APROBADA:
        return

    with transaction.atomic():
        orden = OrdenCompra.objects.select_for_update().get(pk=orden.pk)
        if orden.estado != OrdenCompra.ESTADO_APROBADA:
            return

        cantidades = _resumen_detalles(orden)
        articulos = _bloquear_articulos(cantidades.keys())
        _liberar_hold(articulos, cantidades)
