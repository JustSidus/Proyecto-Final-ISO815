from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
	Articulo,
	Departamento,
	OrdenCompra,
	OrdenCompraDetalle,
	Proveedor,
	UnidadMedida,
)
from .services import cambiar_estado_orden


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


class KanbanArchivadasContextTests(TestCase):
	def setUp(self):
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
