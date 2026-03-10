from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import Articulo, OrdenCompra


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

    return orden


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
