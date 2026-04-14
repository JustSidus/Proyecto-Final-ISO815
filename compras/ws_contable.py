import json
from decimal import Decimal
from urllib import error, request
from urllib.parse import urlparse, urlunparse

from django.conf import settings


class WsContableError(Exception):
    """Error funcional o técnico al consumir el WS contable."""


class WsContableConfigError(WsContableError):
    """Configuración local inválida para integrar con el WS contable."""


def _build_urls(path):
    base_url = getattr(settings, 'WS_CONTABLE_BASE_URL', '').strip().rstrip('/')
    if not base_url:
        raise WsContableConfigError('WS_CONTABLE_BASE_URL no está configurado.')

    parsed = urlparse(base_url if '://' in base_url else f'http://{base_url}')
    if not parsed.netloc:
        raise WsContableConfigError('WS_CONTABLE_BASE_URL debe incluir un host válido.')

    def _join(base_parsed):
        return f'{urlunparse(base_parsed).rstrip("/")}{path}'

    urls = [_join(parsed)]

    # Compatibilidad con despliegues del WS que exponen API en puertos alternos.
    if parsed.port is None and parsed.hostname:
        for port in (3000, 8080):
            host = parsed.hostname
            if ':' in host and not host.startswith('['):
                host = f'[{host}]'

            auth = ''
            if parsed.username:
                auth = parsed.username
                if parsed.password:
                    auth += f':{parsed.password}'
                auth = f'{auth}@'

            alternate = parsed._replace(netloc=f'{auth}{host}:{port}')
            url = _join(alternate)
            if url not in urls:
                urls.append(url)

    return urls


def _validate_positive_int(value, setting_name):
    if not isinstance(value, int) or value <= 0:
        raise WsContableConfigError(
            f'{setting_name} debe ser un entero mayor que cero para enviar asientos.'
        )


def construir_payload_asiento(orden, asiento_db, asiento_cr):
    auxiliar_id = getattr(settings, 'WS_CONTABLE_AUXILIAR_ID', None)
    cuenta_debito_id = getattr(settings, 'WS_CONTABLE_CUENTA_DEBITO_ID', None)
    cuenta_credito_id = getattr(settings, 'WS_CONTABLE_CUENTA_CREDITO_ID', None)

    _validate_positive_int(auxiliar_id, 'WS_CONTABLE_AUXILIAR_ID')
    _validate_positive_int(cuenta_debito_id, 'WS_CONTABLE_CUENTA_DEBITO_ID')
    _validate_positive_int(cuenta_credito_id, 'WS_CONTABLE_CUENTA_CREDITO_ID')

    monto_db = Decimal(asiento_db.monto)
    monto_cr = Decimal(asiento_cr.monto)

    if monto_db <= 0 or monto_cr <= 0:
        raise WsContableError('Los montos de débito y crédito deben ser mayores que cero.')

    if monto_db != monto_cr:
        raise WsContableError(
            f'Asiento desbalanceado para OC-{orden.pk:05d}: '
            f'DB={monto_db} y CR={monto_cr}.'
        )

    return {
        'descripcion': asiento_db.descripcion,
        'auxiliar': {'id': auxiliar_id},
        'fechaAsiento': asiento_db.fecha.isoformat(),
        'montoTotal': float(monto_db),
        'detalles': [
            {
                'cuenta': {'id': cuenta_debito_id},
                'tipoMovimiento': 'Debito',
                'monto': float(monto_db),
            },
            {
                'cuenta': {'id': cuenta_credito_id},
                'tipoMovimiento': 'Credito',
                'monto': float(monto_cr),
            },
        ],
        'estado': bool(asiento_db.estado and asiento_cr.estado),
    }


def _post_json(path, payload):
    timeout = float(getattr(settings, 'WS_CONTABLE_TIMEOUT', 10))
    last_error = None

    for url in _build_urls(path):
        req = request.Request(
            url=url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            method='POST',
        )

        try:
            with request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode('utf-8', errors='replace').strip()
                if not body:
                    return {}
                return json.loads(body)
        except error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace').strip()
            raise WsContableError(f'WS contable respondió HTTP {exc.code}: {detail[:500]}') from exc
        except error.URLError as exc:
            last_error = WsContableError(
                f'No se pudo conectar con WS contable en {url}: {exc.reason}'
            )
            continue
        except TimeoutError as exc:
            last_error = WsContableError(
                f'No se pudo conectar con WS contable en {url}: timeout de red.'
            )
            continue
        except json.JSONDecodeError as exc:
            raise WsContableError('El WS contable respondió JSON inválido.') from exc

    if last_error is not None:
        raise last_error

    raise WsContableError('No se pudo construir una URL válida para el WS contable.')


def enviar_payload(payload):
    respuesta = _post_json('/api/asientos', payload)
    remoto_id = respuesta.get('id') if isinstance(respuesta, dict) else None
    return remoto_id


def enviar_asiento(orden, asiento_db, asiento_cr):
    payload = construir_payload_asiento(orden, asiento_db, asiento_cr)
    return enviar_payload(payload)
