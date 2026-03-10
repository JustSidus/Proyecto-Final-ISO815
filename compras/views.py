import json
from datetime import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from .forms import (
    ArticuloForm,
    ConsultaOrdenesForm,
    DepartamentoForm,
    OrdenCompraDetalleFormSet,
    OrdenCompraForm,
    ProveedorForm,
    UnidadMedidaForm,
)
from .models import (
    Articulo,
    Departamento,
    OrdenCompra,
    Proveedor,
    UnidadMedida,
)
from .services import TRANSICIONES_VALIDAS, cambiar_estado_orden, liberar_hold_si_aprobada


def _formset_tiene_detalles(formset):
    for detalle_form in formset.forms:
        cleaned_data = getattr(detalle_form, 'cleaned_data', None)
        if not cleaned_data:
            continue
        if cleaned_data.get('DELETE'):
            continue
        if cleaned_data.get('articulo') and cleaned_data.get('cantidad'):
            return True
    return False


def _normalizar_codigo_orden(valor):
    digitos = ''.join(char for char in (valor or '') if char.isdigit())
    if not digitos:
        return None
    return int(digitos)


def _aplicar_filtros_ordenes(queryset, filtro_proveedor, filtro_orden):
    if filtro_proveedor:
        if filtro_proveedor.isdigit():
            queryset = queryset.filter(proveedor_id=int(filtro_proveedor))
        else:
            queryset = queryset.none()

    if filtro_orden:
        numero_orden = _normalizar_codigo_orden(filtro_orden)
        if numero_orden is None:
            queryset = queryset.none()
        else:
            queryset = queryset.filter(pk=numero_orden)

    return queryset


def _transiciones_disponibles(estado_actual):
    orden_preferido = [
        OrdenCompra.ESTADO_PENDIENTE,
        OrdenCompra.ESTADO_APROBADA,
        OrdenCompra.ESTADO_COMPLETADA,
        OrdenCompra.ESTADO_RECHAZADA,
    ]
    etiquetas = dict(OrdenCompra.ESTADO_CHOICES)
    destinos = TRANSICIONES_VALIDAS.get(estado_actual, set())

    return [
        {'codigo': codigo, 'label': etiquetas.get(codigo, codigo)}
        for codigo in orden_preferido
        if codigo in destinos
    ]


# ── Inicio ────────────────────────────────────────────────────────────────────

class IndexView(TemplateView):
    template_name = 'compras/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_departamentos'] = Departamento.objects.filter(estado=True).count()
        ctx['total_proveedores'] = Proveedor.objects.filter(estado=True).count()
        ctx['total_articulos'] = Articulo.objects.filter(estado=True).count()
        ctx['total_ordenes'] = OrdenCompra.objects.count()
        ctx['ordenes_pendientes'] = OrdenCompra.objects.filter(
            estado=OrdenCompra.ESTADO_PENDIENTE
        ).count()
        return ctx


# ── Departamentos ─────────────────────────────────────────────────────────────

class DepartamentoListView(ListView):
    model = Departamento
    template_name = 'compras/departamento_list.html'
    context_object_name = 'departamentos'


class DepartamentoCreateView(CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'compras/departamento_form.html'
    success_url = reverse_lazy('compras:departamento-list')

    def form_valid(self, form):
        messages.success(self.request, 'Departamento creado correctamente.')
        return super().form_valid(form)


class DepartamentoUpdateView(UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'compras/departamento_form.html'
    success_url = reverse_lazy('compras:departamento-list')

    def form_valid(self, form):
        messages.success(self.request, 'Departamento actualizado correctamente.')
        return super().form_valid(form)


class DepartamentoDeleteView(DeleteView):
    model = Departamento
    template_name = 'compras/departamento_confirm_delete.html'
    success_url = reverse_lazy('compras:departamento-list')

    def form_valid(self, form):
        messages.success(self.request, 'Departamento eliminado.')
        return super().form_valid(form)


# ── Unidades de Medida ────────────────────────────────────────────────────────

class UnidadMedidaListView(ListView):
    model = UnidadMedida
    template_name = 'compras/unidadmedida_list.html'
    context_object_name = 'unidades'


class UnidadMedidaCreateView(CreateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    template_name = 'compras/unidadmedida_form.html'
    success_url = reverse_lazy('compras:unidadmedida-list')

    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida creada correctamente.')
        return super().form_valid(form)


class UnidadMedidaUpdateView(UpdateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    template_name = 'compras/unidadmedida_form.html'
    success_url = reverse_lazy('compras:unidadmedida-list')

    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida actualizada correctamente.')
        return super().form_valid(form)


class UnidadMedidaDeleteView(DeleteView):
    model = UnidadMedida
    template_name = 'compras/unidadmedida_confirm_delete.html'
    success_url = reverse_lazy('compras:unidadmedida-list')

    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida eliminada.')
        return super().form_valid(form)


# ── Proveedores ───────────────────────────────────────────────────────────────

class ProveedorListView(ListView):
    model = Proveedor
    template_name = 'compras/proveedor_list.html'
    context_object_name = 'proveedores'


class ProveedorCreateView(CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'compras/proveedor_form.html'
    success_url = reverse_lazy('compras:proveedor-list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado correctamente.')
        return super().form_valid(form)


class ProveedorUpdateView(UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'compras/proveedor_form.html'
    success_url = reverse_lazy('compras:proveedor-list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado correctamente.')
        return super().form_valid(form)


class ProveedorDeleteView(DeleteView):
    model = Proveedor
    template_name = 'compras/proveedor_confirm_delete.html'
    success_url = reverse_lazy('compras:proveedor-list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor eliminado.')
        return super().form_valid(form)


# ── Artículos ─────────────────────────────────────────────────────────────────

class ArticuloListView(ListView):
    model = Articulo
    template_name = 'compras/articulo_list.html'
    context_object_name = 'articulos'


class ArticuloCreateView(CreateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = 'compras/articulo_form.html'
    success_url = reverse_lazy('compras:articulo-list')

    def form_valid(self, form):
        messages.success(self.request, 'Artículo creado correctamente.')
        return super().form_valid(form)


class ArticuloUpdateView(UpdateView):
    model = Articulo
    form_class = ArticuloForm
    template_name = 'compras/articulo_form.html'
    success_url = reverse_lazy('compras:articulo-list')

    def form_valid(self, form):
        messages.success(self.request, 'Artículo actualizado correctamente.')
        return super().form_valid(form)


class ArticuloDeleteView(DeleteView):
    model = Articulo
    template_name = 'compras/articulo_confirm_delete.html'
    success_url = reverse_lazy('compras:articulo-list')

    def form_valid(self, form):
        messages.success(self.request, 'Artículo eliminado.')
        return super().form_valid(form)


# ── Órdenes de Compra ─────────────────────────────────────────────────────────

class OrdenCompraListView(ListView):
    model = OrdenCompra
    template_name = 'compras/orden_list.html'
    context_object_name = 'ordenes'
    limite_default = 5
    limite_opciones = (3, 5, 10, 15, 20)

    def _resolver_limite(self):
        valor = (self.request.GET.get('limite') or '').strip()
        if not valor:
            return self.limite_default
        try:
            limite = int(valor)
        except ValueError:
            return self.limite_default
        if limite not in self.limite_opciones:
            return self.limite_default
        return limite

    def get_queryset(self):
        self.filtro_proveedor = (self.request.GET.get('proveedor') or '').strip()
        self.filtro_orden = (self.request.GET.get('orden') or '').strip()
        self.kanban_visible_limit = self._resolver_limite()

        queryset = (
            OrdenCompra.objects
            .select_related('proveedor', 'departamento')
            .prefetch_related('detalles')
            .order_by('id')
        )
        return _aplicar_filtros_ordenes(queryset, self.filtro_proveedor, self.filtro_orden)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ordenes = list(ctx['ordenes'])
        for orden in ordenes:
            orden.transiciones_disponibles = _transiciones_disponibles(orden.estado)

        ctx['filtro_proveedor'] = self.filtro_proveedor
        ctx['filtro_orden'] = self.filtro_orden
        ctx['limite_actual'] = self.kanban_visible_limit
        ctx['limite_opciones'] = self.limite_opciones
        ctx['proveedores_filtro'] = (
            Proveedor.objects
            .filter(estado=True)
            .order_by('nombre_comercial')
        )

        pendientes = [o for o in ordenes if o.estado == OrdenCompra.ESTADO_PENDIENTE]
        aprobadas = [o for o in ordenes if o.estado == OrdenCompra.ESTADO_APROBADA]
        completadas = [o for o in ordenes if o.estado == OrdenCompra.ESTADO_COMPLETADA]
        rechazadas = [o for o in ordenes if o.estado == OrdenCompra.ESTADO_RECHAZADA]

        limite = self.kanban_visible_limit
        ctx['kanban_visible_limit'] = limite

        ctx['ordenes_pendientes_total'] = len(pendientes)
        ctx['ordenes_pendientes_visibles'] = pendientes[:limite]
        ctx['ordenes_pendientes_archivadas'] = pendientes[limite:]

        ctx['ordenes_aprobadas_total'] = len(aprobadas)
        ctx['ordenes_aprobadas_visibles'] = aprobadas[:limite]
        ctx['ordenes_aprobadas_archivadas'] = aprobadas[limite:]

        ctx['ordenes_completadas_total'] = len(completadas)
        ctx['ordenes_completadas_visibles'] = completadas[:limite]
        ctx['ordenes_completadas_archivadas'] = completadas[limite:]

        ctx['ordenes_rechazadas_total'] = len(rechazadas)
        ctx['ordenes_rechazadas_visibles'] = rechazadas[:limite]
        ctx['ordenes_rechazadas_archivadas'] = rechazadas[limite:]
        return ctx


class OrdenCompraAutocompleteView(View):
    max_resultados = 5

    def get(self, request):
        query = (request.GET.get('q') or '').strip().upper()
        if not query:
            return JsonResponse({'results': []})

        digitos = ''.join(char for char in query if char.isdigit())
        numero_referencia = int(digitos) if digitos else None

        candidatos = list(
            OrdenCompra.objects
            .select_related('proveedor')
            .order_by('id')
        )

        def puntaje(orden):
            codigo = f'OC-{orden.pk:05d}'
            codigo_upper = codigo.upper()
            if codigo_upper.startswith(query):
                return (0, len(codigo_upper) - len(query), orden.pk)
            if query in codigo_upper:
                return (1, codigo_upper.index(query), orden.pk)
            if numero_referencia is not None:
                return (2, abs(orden.pk - numero_referencia), orden.pk)
            return (3, orden.pk)

        ordenados = sorted(candidatos, key=puntaje)
        resultados = [
            {
                'id': orden.pk,
                'codigo': f'OC-{orden.pk:05d}',
                'proveedor': orden.proveedor.nombre_comercial,
            }
            for orden in ordenados[:self.max_resultados]
        ]
        return JsonResponse({'results': resultados})


class OrdenCompraBacklogView(ListView):
    model = OrdenCompra
    template_name = 'compras/orden_backlog.html'
    context_object_name = 'ordenes'

    def get_queryset(self):
        self.filtro_proveedor = (self.request.GET.get('proveedor') or '').strip()
        self.filtro_orden = (self.request.GET.get('orden') or '').strip()
        self.filtro_estado = (self.request.GET.get('estado') or '').strip()
        self.filtro_fecha_desde = (self.request.GET.get('fecha_desde') or '').strip()
        self.filtro_fecha_hasta = (self.request.GET.get('fecha_hasta') or '').strip()
        self.sort_by = (self.request.GET.get('sort') or 'id').strip()
        self.sort_order = (self.request.GET.get('order') or 'asc').strip()

        # Validar parámetros de ordenamiento
        campos_permitidos = ['id', 'fecha_orden', 'proveedor__nombre_comercial', 'departamento__nombre', 'estado']
        if self.sort_by not in campos_permitidos:
            self.sort_by = 'id'
        if self.sort_order not in ['asc', 'desc']:
            self.sort_order = 'asc'

        queryset = (
            OrdenCompra.objects
            .select_related('proveedor', 'departamento')
            .prefetch_related('detalles')
        )
        
        # Aplicar filtros básicos
        queryset = _aplicar_filtros_ordenes(queryset, self.filtro_proveedor, self.filtro_orden)
        
        # Filtro por estado
        if self.filtro_estado:
            queryset = queryset.filter(estado=self.filtro_estado)
        
        # Filtros por fecha
        if self.filtro_fecha_desde:
            try:
                fecha_desde = datetime.strptime(self.filtro_fecha_desde, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha_orden__gte=fecha_desde)
            except (ValueError, TypeError):
                pass
        
        if self.filtro_fecha_hasta:
            try:
                fecha_hasta = datetime.strptime(self.filtro_fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha_orden__lte=fecha_hasta)
            except (ValueError, TypeError):
                pass
        
        # Aplicar ordenamiento
        campo_orden = self.sort_by
        if self.sort_order == 'desc':
            campo_orden = f'-{campo_orden}'
        
        return queryset.order_by(campo_orden)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ordenes = list(ctx['ordenes'])
        for orden in ordenes:
            orden.transiciones_disponibles = _transiciones_disponibles(orden.estado)

        # Agrupar por estado
        ORDEN_ESTADOS = [
            ('PE', 'Pendientes', 'warning'),
            ('AP', 'Aprobadas', 'success'),
            ('CO', 'Completadas', 'primary'),
            ('RE', 'Rechazadas', 'danger'),
        ]
        
        grupos_estado = []
        for codigo, label, color in ORDEN_ESTADOS:
            ordenes_grupo = [o for o in ordenes if o.estado == codigo]
            if not ordenes_grupo:
                continue

            grupos_estado.append({
                'codigo': codigo,
                'label': label,
                'color': color,
                'ordenes': ordenes_grupo,
            })

        ctx['ordenes'] = ordenes
        ctx['grupos_estado'] = grupos_estado
        
        ctx['filtro_proveedor'] = self.filtro_proveedor
        ctx['filtro_orden'] = self.filtro_orden
        ctx['filtro_estado'] = self.filtro_estado
        ctx['filtro_fecha_desde'] = self.filtro_fecha_desde
        ctx['filtro_fecha_hasta'] = self.filtro_fecha_hasta
        ctx['sort_by'] = self.sort_by
        ctx['sort_order'] = self.sort_order
        
        ctx['proveedores_filtro'] = (
            Proveedor.objects
            .filter(estado=True)
            .order_by('nombre_comercial')
        )
        
        ctx['estado_opciones'] = [
            ('PE', 'Pendiente'),
            ('AP', 'Aprobada'),
            ('CO', 'Completada'),
            ('RE', 'Rechazada'),
        ]
        
        return ctx


class OrdenCompraDetailView(DetailView):
    model = OrdenCompra
    template_name = 'compras/orden_detail.html'
    context_object_name = 'orden'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['detalles'] = self.object.detalles.select_related('articulo', 'unidad_medida')
        ctx['total'] = self.object.total()
        ctx['puede_editar'] = self.object.estado == OrdenCompra.ESTADO_PENDIENTE
        return ctx


class OrdenCompraCreateView(View):
    """Vista para crear una Orden de Compra con sus líneas de detalle en un solo formulario."""
    template_name = 'compras/orden_form.html'

    def get(self, request):
        form = OrdenCompraForm()
        formset = OrdenCompraDetalleFormSet()
        return render(request, self.template_name, {'form': form, 'formset': formset, 'accion': 'Crear'})

    def post(self, request):
        form = OrdenCompraForm(request.POST)
        formset = OrdenCompraDetalleFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            if not _formset_tiene_detalles(formset):
                messages.error(request, 'Debes agregar al menos una línea de detalle.')
                return render(request, self.template_name, {'form': form, 'formset': formset, 'accion': 'Crear'})

            with transaction.atomic():
                orden = form.save()
                formset.instance = orden
                formset.save()

            messages.success(request, f'Orden OC-{orden.pk:05d} creada correctamente.')
            return redirect('compras:orden-detail', pk=orden.pk)
        return render(request, self.template_name, {'form': form, 'formset': formset, 'accion': 'Crear'})


class OrdenCompraUpdateView(View):
    """Vista para editar una Orden de Compra y sus líneas de detalle."""
    template_name = 'compras/orden_form.html'

    def get(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)
        if orden.estado != OrdenCompra.ESTADO_PENDIENTE:
            messages.warning(request, 'Solo puedes editar órdenes en estado Pendiente.')
            return redirect('compras:orden-detail', pk=orden.pk)

        form = OrdenCompraForm(instance=orden)
        formset = OrdenCompraDetalleFormSet(instance=orden)
        return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden, 'accion': 'Editar'})

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)
        if orden.estado != OrdenCompra.ESTADO_PENDIENTE:
            messages.warning(request, 'Solo puedes editar órdenes en estado Pendiente.')
            return redirect('compras:orden-detail', pk=orden.pk)

        form = OrdenCompraForm(request.POST, instance=orden)
        formset = OrdenCompraDetalleFormSet(request.POST, instance=orden)
        if form.is_valid() and formset.is_valid():
            if not _formset_tiene_detalles(formset):
                messages.error(request, 'Debes agregar al menos una línea de detalle.')
                return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden, 'accion': 'Editar'})

            with transaction.atomic():
                form.save()
                formset.save()

            messages.success(request, f'Orden OC-{orden.pk:05d} actualizada correctamente.')
            return redirect('compras:orden-detail', pk=orden.pk)
        return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden, 'accion': 'Editar'})


class OrdenCompraCambiarEstadoView(View):
    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)

        try:
            if request.content_type and 'application/json' in request.content_type:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            else:
                payload = request.POST
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Payload JSON inválido.'}, status=400)

        nuevo_estado = payload.get('estado')
        if not nuevo_estado:
            return JsonResponse({'ok': False, 'error': 'Debes indicar el nuevo estado.'}, status=400)

        try:
            orden_actualizada = cambiar_estado_orden(orden, nuevo_estado)
        except ValidationError as error:
            return JsonResponse({'ok': False, 'error': ' '.join(error.messages)}, status=400)

        return JsonResponse({
            'ok': True,
            'estado': orden_actualizada.estado,
            'estado_display': orden_actualizada.get_estado_display(),
        })


class OrdenCompraDeleteView(DeleteView):
    model = OrdenCompra
    template_name = 'compras/orden_confirm_delete.html'
    success_url = reverse_lazy('compras:orden-list')

    def form_valid(self, form):
        with transaction.atomic():
            liberar_hold_si_aprobada(self.object)
            response = super().form_valid(form)

        messages.success(self.request, 'Orden de compra eliminada.')
        return response


# ── Consulta por criterios ────────────────────────────────────────────────────

class ConsultaOrdenesView(View):
    template_name = 'compras/consulta_ordenes.html'

    def get(self, request):
        form = ConsultaOrdenesForm(request.GET or None)
        ordenes = OrdenCompra.objects.select_related('proveedor', 'departamento').none()
        ejecutado = False

        if request.GET and form.is_valid():
            ejecutado = True
            ordenes = OrdenCompra.objects.select_related('proveedor', 'departamento').all()
            if form.cleaned_data.get('departamento'):
                ordenes = ordenes.filter(departamento=form.cleaned_data['departamento'])
            if form.cleaned_data.get('proveedor'):
                ordenes = ordenes.filter(proveedor=form.cleaned_data['proveedor'])
            if form.cleaned_data.get('estado'):
                ordenes = ordenes.filter(estado=form.cleaned_data['estado'])
            if form.cleaned_data.get('codigo_orden'):
                numero_orden = _normalizar_codigo_orden(form.cleaned_data['codigo_orden'])
                if numero_orden is None:
                    ordenes = ordenes.none()
                else:
                    ordenes = ordenes.filter(pk=numero_orden)
            if form.cleaned_data.get('fecha_desde'):
                ordenes = ordenes.filter(fecha_orden__gte=form.cleaned_data['fecha_desde'])
            if form.cleaned_data.get('fecha_hasta'):
                ordenes = ordenes.filter(fecha_orden__lte=form.cleaned_data['fecha_hasta'])
            ordenes = ordenes.order_by('id')

        return render(request, self.template_name, {
            'form': form,
            'ordenes': ordenes,
            'ejecutado': ejecutado,
        })
