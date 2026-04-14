import json
import threading
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import close_old_connections, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Articulo, AsientoContable, AsientoContableIntegracion, OrdenCompra
from .ws_contable import WsContableError, construir_payload_asiento, enviar_payload


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
    actualizados = []

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
        actualizados.append(articulo)

    if actualizados:
        Articulo.objects.bulk_update(actualizados, ['cantidad_retenida'])


def _liberar_hold(articulos, cantidades):
    actualizados = []

    for articulo_id, cantidad in cantidades.items():
        articulo = articulos[articulo_id]
        articulo.cantidad_retenida = max(articulo.cantidad_retenida - cantidad, 0)
        actualizados.append(articulo)

    if actualizados:
        Articulo.objects.bulk_update(actualizados, ['cantidad_retenida'])


def _consumir_orden_aprobada(articulos, cantidades):
    actualizados = []

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
        actualizados.append(articulo)

    if actualizados:
        Articulo.objects.bulk_update(actualizados, ['cantidad_retenida', 'existencia'])


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


def _obtener_asientos_integracion(orden):
    asientos = list(AsientoContable.objects.filter(orden_compra=orden, estado=True))
    if not asientos:
        return None, None

    asiento_db = next((a for a in asientos if a.tipo_movimiento == AsientoContable.TIPO_DB), None)
    asiento_cr = next((a for a in asientos if a.tipo_movimiento == AsientoContable.TIPO_CR), None)
    return asiento_db, asiento_cr


def _actualizar_estado_ws(orden, ws_estado_envio, mensaje='', ws_asiento_id=None):
    AsientoContable.objects.filter(orden_compra=orden).update(
        ws_estado_envio=ws_estado_envio,
        ws_fecha_envio=timezone.now(),
        ws_error=str(mensaje)[:1000],
        ws_asiento_id=ws_asiento_id,
    )

    AsientoContableIntegracion.objects.filter(orden_compra=orden).update(
        ws_estado_envio=ws_estado_envio,
        ws_fecha_envio=timezone.now(),
        ws_error=str(mensaje)[:1000],
        ws_asiento_id=ws_asiento_id,
    )


def _crear_o_actualizar_integracion_ws(orden, asiento_db, asiento_cr):
    payload = construir_payload_asiento(orden, asiento_db, asiento_cr)

    registro, _ = AsientoContableIntegracion.objects.update_or_create(
        orden_compra=orden,
        defaults={
            'asiento_debito': asiento_db,
            'asiento_credito': asiento_cr,
            'auxiliar_id': int(getattr(settings, 'WS_CONTABLE_AUXILIAR_ID', 0) or 0),
            'tipo_inventario_id': TIPO_INVENTARIO_GENERAL,
            'cuenta_debito_id': int(getattr(settings, 'WS_CONTABLE_CUENTA_DEBITO_ID', 0) or 0),
            'cuenta_credito_id': int(getattr(settings, 'WS_CONTABLE_CUENTA_CREDITO_ID', 0) or 0),
            'descripcion': payload['descripcion'],
            'fecha_asiento': asiento_db.fecha,
            'monto_total': Decimal(str(payload['montoTotal'])),
            'estado': bool(payload['estado']),
            'payload_json': json.dumps(payload, ensure_ascii=False),
        },
    )

    return registro, payload


def _sincronizar_asiento_ws_contable(orden_id):
    if not getattr(settings, 'WS_CONTABLE_ENABLED', False):
        return

    orden = OrdenCompra.objects.filter(pk=orden_id).first()
    if orden is None:
        return

    asiento_db, asiento_cr = _obtener_asientos_integracion(orden)
    if asiento_db is None or asiento_cr is None:
        _actualizar_estado_ws(
            orden,
            AsientoContable.WS_ERROR,
            'Incompatibilidad de integración: la orden debe tener un débito y un crédito locales.',
        )
        return

    registro, payload = _crear_o_actualizar_integracion_ws(orden, asiento_db, asiento_cr)

    if registro.ws_estado_envio == AsientoContableIntegracion.WS_ENVIADO and registro.ws_asiento_id:
        return

    try:
        ws_asiento_id = enviar_payload(payload)
    except (ValidationError, WsContableError, ValueError) as error:
        _actualizar_estado_ws(orden, AsientoContable.WS_ERROR, error)
        return

    _actualizar_estado_ws(orden, AsientoContable.WS_ENVIADO, '', ws_asiento_id)


def _sincronizar_asiento_ws_en_hilo(orden_id):
    close_old_connections()
    try:
        _sincronizar_asiento_ws_contable(orden_id)
    finally:
        close_old_connections()


def _programar_sincronizacion_ws(orden_id):
    modo_sync = str(getattr(settings, 'WS_CONTABLE_SYNC_MODE', 'inline') or 'inline').strip().lower()
    if modo_sync == 'thread':
        hilo = threading.Thread(target=_sincronizar_asiento_ws_en_hilo, args=(orden_id,), daemon=True)
        hilo.start()
        return

    _sincronizar_asiento_ws_contable(orden_id)


def cambiar_estado_orden(orden, nuevo_estado):
    estados_validos = {codigo for codigo, _ in OrdenCompra.ESTADO_CHOICES}
    if nuevo_estado not in estados_validos:
        raise ValidationError('Estado de orden inválido.')

    with transaction.atomic():
        orden = OrdenCompra.objects.select_for_update().get(pk=orden.pk)
        estado_actual = orden.estado
        enviar_ws = False

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
            enviar_ws = True

        if enviar_ws:
            transaction.on_commit(lambda: _programar_sincronizacion_ws(orden.pk))

    return orden


def sincronizar_asientos_ordenes_completadas():
    resumen = {
        'ordenes_procesadas': 0,
        'asientos_creados': 0,
        'asientos_actualizados': 0,
    }

    ordenes = OrdenCompra.objects.filter(estado=OrdenCompra.ESTADO_COMPLETADA)
    for orden in ordenes:
        resultado = _crear_o_actualizar_asientos_orden_completada(orden)
        _sincronizar_asiento_ws_contable(orden.pk)
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
