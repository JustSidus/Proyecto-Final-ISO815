from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from datetime import date
from unittest.mock import patch

from .models import (
	Articulo,
	AsientoContable,
	AsientoContableIntegracion,
	Departamento,
	OrdenCompra,
	OrdenCompraDetalle,
	Proveedor,
	UnidadMedida,
)
from .services import cambiar_estado_orden
from .ws_contable import WsContableError, construir_payload_asiento, _build_urls


User = get_user_model()


def construir_cedula_valida(base_10):
	suma = 0
	for index, char in enumerate(base_10):
		factor = 1 if index % 2 == 0 else 2
		producto = int(char) * factor
		suma += producto if producto < 10 else producto - 9
	verificador = (10 - (suma % 10)) % 10
	return f'{base_10}{verificador}'


def construir_rnc_valido(base_8):
	pesos = [7, 9, 8, 6, 5, 4, 3, 2]
	suma = sum(int(digito) * peso for digito, peso in zip(base_8, pesos))
	verificador = 11 - (suma % 11)
	if verificador == 10:
		verificador = 1
	elif verificador == 11:
		verificador = 2
	return f'{base_8}{verificador}'


class ProveedorDocumentoTests(TestCase):
	def test_valida_cedula_dominicana(self):
		cedula = construir_cedula_valida('0011234567')
		proveedor = Proveedor(
			tipo_documento=Proveedor.TIPO_CEDULA,
			cedula_rnc=cedula,
			nombre_comercial='Proveedor Cédula',
			estado=True,
		)
		proveedor.full_clean()

	def test_valida_cedula_ejemplo_compartido(self):
		proveedor = Proveedor(
			tipo_documento=Proveedor.TIPO_CEDULA,
			cedula_rnc='00100000018',
			nombre_comercial='Proveedor Cédula Ejemplo',
			estado=True,
		)
		proveedor.full_clean()

	def test_rechaza_cedula_invalida(self):
		proveedor = Proveedor(
			tipo_documento=Proveedor.TIPO_CEDULA,
			cedula_rnc='12345678901',
			nombre_comercial='Proveedor Cédula inválida',
			estado=True,
		)
		with self.assertRaises(ValidationError):
			proveedor.full_clean()

	def test_valida_rnc_dominicano(self):
		rnc = construir_rnc_valido('10100000')
		proveedor = Proveedor(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=rnc,
			nombre_comercial='Proveedor RNC',
			estado=True,
		)
		proveedor.full_clean()

	def test_documento_se_guarda_formateado(self):
		cedula = construir_cedula_valida('0011234567')
		proveedor_cedula = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_CEDULA,
			cedula_rnc=cedula,
			nombre_comercial='Proveedor Formato Cédula',
			estado=True,
		)
		esperado_cedula = f'{cedula[:3]}-{cedula[3:10]}-{cedula[10]}'
		self.assertEqual(proveedor_cedula.cedula_rnc, esperado_cedula)

		rnc = construir_rnc_valido('13181176')
		proveedor_rnc = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=rnc,
			nombre_comercial='Proveedor Formato RNC',
			estado=True,
		)
		esperado_rnc = f'{rnc[:3]}-{rnc[3:9]}'
		self.assertEqual(proveedor_rnc.cedula_rnc, esperado_rnc)

	def test_rechaza_duplicado_logico_documento(self):
		rnc = construir_rnc_valido('13181176')
		rnc_formateado = f'{rnc[:3]}-{rnc[3:9]}'
		Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=rnc_formateado,
			nombre_comercial='Proveedor Base RNC',
			estado=True,
		)

		duplicado = Proveedor(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=rnc,
			nombre_comercial='Proveedor RNC Duplicado',
			estado=True,
		)

		with self.assertRaises(ValidationError):
			duplicado.full_clean()


class InventarioHoldTests(TestCase):
	def setUp(self):
		self.departamento = Departamento.objects.create(nombre='Compras QA', estado=True)
		self.unidad = UnidadMedida.objects.create(descripcion='Unidad', estado=True)
		self.proveedor = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('13181176'),
			nombre_comercial='Proveedor QA',
			estado=True,
		)
		self.articulo = Articulo.objects.create(
			descripcion='Artículo QA',
			marca='Marca QA',
			unidad_medida=self.unidad,
			existencia=10,
			estado=True,
		)

	def test_hold_y_consumo_en_transiciones(self):
		orden_1 = OrdenCompra.objects.create(
			proveedor=self.proveedor,
			departamento=self.departamento,
			estado=OrdenCompra.ESTADO_PENDIENTE,
		)
		OrdenCompraDetalle.objects.create(
			orden=orden_1,
			articulo=self.articulo,
			cantidad=5,
			unidad_medida=self.unidad,
			costo_unitario=100,
		)

		cambiar_estado_orden(orden_1, OrdenCompra.ESTADO_APROBADA)

		self.articulo.refresh_from_db()
		self.assertEqual(self.articulo.cantidad_retenida, 5)
		self.assertEqual(self.articulo.disponible, 5)

		orden_2 = OrdenCompra.objects.create(
			proveedor=self.proveedor,
			departamento=self.departamento,
			estado=OrdenCompra.ESTADO_PENDIENTE,
		)
		OrdenCompraDetalle.objects.create(
			orden=orden_2,
			articulo=self.articulo,
			cantidad=6,
			unidad_medida=self.unidad,
			costo_unitario=100,
		)

		with self.assertRaises(ValidationError):
			cambiar_estado_orden(orden_2, OrdenCompra.ESTADO_APROBADA)

		cambiar_estado_orden(orden_1, OrdenCompra.ESTADO_COMPLETADA)

		self.articulo.refresh_from_db()
		self.assertEqual(self.articulo.cantidad_retenida, 0)
		self.assertEqual(self.articulo.existencia, 5)

		asientos = AsientoContable.objects.filter(orden_compra=orden_1).order_by('tipo_movimiento')
		self.assertEqual(asientos.count(), 2)
		self.assertEqual(
			set(asientos.values_list('tipo_movimiento', flat=True)),
			{AsientoContable.TIPO_DB, AsientoContable.TIPO_CR},
		)
		for asiento in asientos:
			self.assertEqual(asiento.tipo_inventario, 1)
			self.assertTrue(asiento.cuenta_contable)
			self.assertGreater(asiento.monto, 0)


class KanbanArchivadasContextTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(username='tester', password='clave-segura')
		self.client.login(username='tester', password='clave-segura')

		self.departamento = Departamento.objects.create(nombre='Depto Kanban', estado=True)
		self.unidad = UnidadMedida.objects.create(descripcion='Unidad', estado=True)
		self.proveedor = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('13181176'),
			nombre_comercial='Proveedor Kanban',
			estado=True,
		)
		self.articulo = Articulo.objects.create(
			descripcion='Articulo Kanban',
			marca='Marca Kanban',
			unidad_medida=self.unidad,
			existencia=200,
			estado=True,
		)

	def _crear_orden(self, estado):
		orden = OrdenCompra.objects.create(
			proveedor=self.proveedor,
			departamento=self.departamento,
			estado=estado,
		)
		OrdenCompraDetalle.objects.create(
			orden=orden,
			articulo=self.articulo,
			cantidad=1,
			unidad_medida=self.unidad,
			costo_unitario=10,
		)
		return orden

	def test_limite_y_archivo_por_columna_en_kanban(self):
		for _ in range(7):
			self._crear_orden(OrdenCompra.ESTADO_PENDIENTE)
			self._crear_orden(OrdenCompra.ESTADO_APROBADA)
			self._crear_orden(OrdenCompra.ESTADO_COMPLETADA)
			self._crear_orden(OrdenCompra.ESTADO_RECHAZADA)

		response = self.client.get(reverse('compras:orden-list'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['kanban_visible_limit'], 5)

		self.assertEqual(len(response.context['ordenes_pendientes_visibles']), 5)
		self.assertEqual(len(response.context['ordenes_pendientes_archivadas']), 2)

		self.assertEqual(len(response.context['ordenes_aprobadas_visibles']), 5)
		self.assertEqual(len(response.context['ordenes_aprobadas_archivadas']), 2)

		self.assertEqual(len(response.context['ordenes_completadas_visibles']), 5)
		self.assertEqual(len(response.context['ordenes_completadas_archivadas']), 2)

		self.assertEqual(len(response.context['ordenes_rechazadas_visibles']), 5)
		self.assertEqual(len(response.context['ordenes_rechazadas_archivadas']), 2)


class OrdenCompraAutocompleteTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(username='auto-user', password='clave-segura')
		self.client.login(username='auto-user', password='clave-segura')

		self.departamento = Departamento.objects.create(nombre='Depto Autocomplete', estado=True)
		self.unidad = UnidadMedida.objects.create(descripcion='Unidad', estado=True)
		self.proveedor_auto = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('20100000'),
			nombre_comercial='Proveedor Auto',
			estado=True,
		)
		self.proveedor_otro = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('20100001'),
			nombre_comercial='Proveedor Varios',
			estado=True,
		)

	def _crear_orden(self, proveedor):
		orden = OrdenCompra.objects.create(
			proveedor=proveedor,
			departamento=self.departamento,
			estado=OrdenCompra.ESTADO_PENDIENTE,
		)
		OrdenCompraDetalle.objects.create(
			orden=orden,
			articulo=Articulo.objects.create(
				descripcion=f'Articulo {orden.pk}',
				marca='Marca',
				unidad_medida=self.unidad,
				existencia=100,
				estado=True,
			),
			cantidad=1,
			unidad_medida=self.unidad,
			costo_unitario=10,
		)
		return orden

	def test_autocomplete_prioriza_codigo_exacto(self):
		for _ in range(8):
			self._crear_orden(self.proveedor_auto)

		response = self.client.get(reverse('compras:orden-autocomplete'), {'q': 'OC-00003'})

		self.assertEqual(response.status_code, 200)
		resultados = response.json()['results']
		self.assertTrue(resultados)
		self.assertEqual(resultados[0]['codigo'], 'OC-00003')

	def test_autocomplete_limita_resultados_a_cinco(self):
		for _ in range(12):
			self._crear_orden(self.proveedor_otro)

		response = self.client.get(reverse('compras:orden-autocomplete'), {'q': 'OC'})

		self.assertEqual(response.status_code, 200)
		resultados = response.json()['results']
		self.assertEqual(len(resultados), 5)


class IntegracionWsContablePayloadTests(TestCase):
	def setUp(self):
		self.departamento = Departamento.objects.create(nombre='Depto WS', estado=True)
		self.unidad = UnidadMedida.objects.create(descripcion='Unidad', estado=True)
		self.proveedor = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('10100000'),
			nombre_comercial='Proveedor WS',
			estado=True,
		)
		self.orden = OrdenCompra.objects.create(
			proveedor=self.proveedor,
			departamento=self.departamento,
			estado=OrdenCompra.ESTADO_COMPLETADA,
		)
		self.asiento_db = AsientoContable.objects.create(
			descripcion='OC-00001 - Compra inventario',
			tipo_inventario=1,
			cuenta_contable='110101',
			tipo_movimiento=AsientoContable.TIPO_DB,
			fecha=date(2026, 4, 14),
			monto='800.00',
			estado=True,
			orden_compra=self.orden,
		)
		self.asiento_cr = AsientoContable.objects.create(
			descripcion='OC-00001 - CxP proveedor',
			tipo_inventario=1,
			cuenta_contable='210101',
			tipo_movimiento=AsientoContable.TIPO_CR,
			fecha=date(2026, 4, 14),
			monto='800.00',
			estado=True,
			orden_compra=self.orden,
		)

	@override_settings(
		WS_CONTABLE_AUXILIAR_ID=7,
		WS_CONTABLE_CUENTA_DEBITO_ID=2,
		WS_CONTABLE_CUENTA_CREDITO_ID=1,
	)
	def test_payload_incluye_todos_los_campos_requeridos(self):
		payload = construir_payload_asiento(self.orden, self.asiento_db, self.asiento_cr)

		self.assertEqual(payload['descripcion'], self.asiento_db.descripcion)
		self.assertEqual(payload['auxiliar']['id'], 7)
		self.assertEqual(payload['fechaAsiento'], '2026-04-14')
		self.assertEqual(payload['montoTotal'], 800.0)
		self.assertEqual(payload['estado'], True)

		self.assertEqual(len(payload['detalles']), 2)
		self.assertEqual(payload['detalles'][0]['cuenta']['id'], 2)
		self.assertEqual(payload['detalles'][0]['tipoMovimiento'], 'Debito')
		self.assertEqual(payload['detalles'][0]['monto'], 800.0)
		self.assertEqual(payload['detalles'][1]['cuenta']['id'], 1)
		self.assertEqual(payload['detalles'][1]['tipoMovimiento'], 'Credito')
		self.assertEqual(payload['detalles'][1]['monto'], 800.0)

	@override_settings(WS_CONTABLE_BASE_URL='http://151.242.194.24')
	def test_ws_base_url_sin_puerto_habilita_fallback_3000_y_8080(self):
		urls = _build_urls('/api/asientos')
		self.assertEqual(urls[0], 'http://151.242.194.24/api/asientos')
		self.assertIn('http://151.242.194.24:3000/api/asientos', urls)
		self.assertIn('http://151.242.194.24:8080/api/asientos', urls)


class IntegracionWsContableFlujoTests(TestCase):
	def setUp(self):
		self.departamento = Departamento.objects.create(nombre='Depto Flujo WS', estado=True)
		self.unidad = UnidadMedida.objects.create(descripcion='Unidad', estado=True)
		self.proveedor = Proveedor.objects.create(
			tipo_documento=Proveedor.TIPO_RNC,
			cedula_rnc=construir_rnc_valido('13181176'),
			nombre_comercial='Proveedor Flujo WS',
			estado=True,
		)
		self.articulo = Articulo.objects.create(
			descripcion='Articulo Flujo WS',
			marca='Marca WS',
			unidad_medida=self.unidad,
			existencia=100,
			estado=True,
		)

	def _crear_orden(self):
		orden = OrdenCompra.objects.create(
			proveedor=self.proveedor,
			departamento=self.departamento,
			estado=OrdenCompra.ESTADO_PENDIENTE,
		)
		OrdenCompraDetalle.objects.create(
			orden=orden,
			articulo=self.articulo,
			cantidad=3,
			unidad_medida=self.unidad,
			costo_unitario=100,
		)
		return orden

	@override_settings(
		WS_CONTABLE_ENABLED=True,
		WS_CONTABLE_AUXILIAR_ID=7,
		WS_CONTABLE_CUENTA_DEBITO_ID=2,
		WS_CONTABLE_CUENTA_CREDITO_ID=1,
	)
	@patch('compras.services.enviar_payload', return_value=1234)
	def test_completar_orden_envia_ws_y_actualiza_estados(self, mock_enviar):
		orden = self._crear_orden()
		cambiar_estado_orden(orden, OrdenCompra.ESTADO_APROBADA)

		with self.captureOnCommitCallbacks(execute=True):
			cambiar_estado_orden(orden, OrdenCompra.ESTADO_COMPLETADA)

		self.assertEqual(mock_enviar.call_count, 1)
		payload = mock_enviar.call_args.args[0]
		self.assertEqual(payload['auxiliar']['id'], 7)
		self.assertIn('descripcion', payload)
		self.assertIn('fechaAsiento', payload)
		self.assertEqual(len(payload['detalles']), 2)

		integracion = AsientoContableIntegracion.objects.get(orden_compra=orden)
		self.assertEqual(integracion.ws_estado_envio, AsientoContableIntegracion.WS_ENVIADO)
		self.assertEqual(integracion.ws_asiento_id, 1234)
		self.assertTrue(integracion.payload_json)

		asientos = AsientoContable.objects.filter(orden_compra=orden)
		self.assertEqual(asientos.count(), 2)
		for asiento in asientos:
			self.assertEqual(asiento.ws_estado_envio, AsientoContable.WS_ENVIADO)
			self.assertEqual(asiento.ws_asiento_id, 1234)

	@override_settings(
		WS_CONTABLE_ENABLED=True,
		WS_CONTABLE_AUXILIAR_ID=7,
		WS_CONTABLE_CUENTA_DEBITO_ID=2,
		WS_CONTABLE_CUENTA_CREDITO_ID=1,
	)
	@patch('compras.services.enviar_payload', side_effect=WsContableError('Falla de integración WS'))
	def test_completar_orden_con_error_ws_guarda_trazabilidad(self, mock_enviar):
		orden = self._crear_orden()
		cambiar_estado_orden(orden, OrdenCompra.ESTADO_APROBADA)

		with self.captureOnCommitCallbacks(execute=True):
			cambiar_estado_orden(orden, OrdenCompra.ESTADO_COMPLETADA)

		self.assertEqual(mock_enviar.call_count, 1)

		integracion = AsientoContableIntegracion.objects.get(orden_compra=orden)
		self.assertEqual(integracion.ws_estado_envio, AsientoContableIntegracion.WS_ERROR)
		self.assertIn('Falla de integración WS', integracion.ws_error)

		for asiento in AsientoContable.objects.filter(orden_compra=orden):
			self.assertEqual(asiento.ws_estado_envio, AsientoContable.WS_ERROR)
			self.assertIn('Falla de integración WS', asiento.ws_error)

	@override_settings(WS_CONTABLE_ENABLED=False)
	@patch('compras.services.enviar_payload')
	def test_completar_orden_con_ws_deshabilitado_no_envia(self, mock_enviar):
		orden = self._crear_orden()
		cambiar_estado_orden(orden, OrdenCompra.ESTADO_APROBADA)

		with self.captureOnCommitCallbacks(execute=True):
			cambiar_estado_orden(orden, OrdenCompra.ESTADO_COMPLETADA)

		mock_enviar.assert_not_called()
		self.assertFalse(AsientoContableIntegracion.objects.filter(orden_compra=orden).exists())

		for asiento in AsientoContable.objects.filter(orden_compra=orden):
			self.assertEqual(asiento.ws_estado_envio, AsientoContable.WS_PENDIENTE)


class AutenticacionSistemaTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_user(username='apiuser', password='clave-segura')
		self.payload_asiento = {
			'descripcion': 'Asiento API Test',
			'tipo_inventario': 1,
			'cuenta_contable': '1-01-01',
			'tipo_movimiento': 'DB',
			'fecha': '2026-03-10',
			'monto': '100.00',
			'estado': True,
		}

	def test_login_web_esta_disponible(self):
		response = self.client.get(reverse('login'))
		self.assertEqual(response.status_code, 200)

	def test_vistas_web_redirigen_si_no_hay_login(self):
		response = self.client.get(reverse('compras:index'))
		self.assertEqual(response.status_code, 302)
		self.assertIn('/login/?next=/', response.url)

	def test_api_asientos_get_publico(self):
		api_client = APIClient()
		response = api_client.get('/api/asientos/')
		self.assertEqual(response.status_code, 200)
		self.assertIsInstance(response.json(), list)

	def test_api_asientos_post_requiere_credenciales(self):
		api_client = APIClient()
		response = api_client.post('/api/asientos/', self.payload_asiento, format='json')
		self.assertIn(response.status_code, (401, 403))

	def test_api_asientos_post_sin_permiso_rechaza(self):
		api_client = APIClient()
		api_client.force_authenticate(user=self.usuario)
		response = api_client.post('/api/asientos/', self.payload_asiento, format='json')
		self.assertEqual(response.status_code, 403)

	def test_api_asientos_post_con_permiso_add_permite(self):
		permiso_agregar = Permission.objects.get(codename='add_asientocontable')
		self.usuario.user_permissions.add(permiso_agregar)

		api_client = APIClient()
		api_client.force_authenticate(user=self.usuario)
		response = api_client.post('/api/asientos/', self.payload_asiento, format='json')
		self.assertEqual(response.status_code, 201)

	def test_login_browsable_api_esta_disponible(self):
		response = self.client.get(reverse('rest_framework:login'))
		self.assertEqual(response.status_code, 200)
