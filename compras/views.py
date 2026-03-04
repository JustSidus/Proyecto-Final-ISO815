from django.contrib import messages
from django.db import transaction
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


class OrdenCompraDetailView(DetailView):
    model = OrdenCompra
    template_name = 'compras/orden_detail.html'
    context_object_name = 'orden'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['detalles'] = self.object.detalles.select_related('articulo', 'unidad_medida')
        ctx['total'] = self.object.total()
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
        form = OrdenCompraForm(instance=orden)
        formset = OrdenCompraDetalleFormSet(instance=orden)
        return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden, 'accion': 'Editar'})

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)
        form = OrdenCompraForm(request.POST, instance=orden)
        formset = OrdenCompraDetalleFormSet(request.POST, instance=orden)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, f'Orden OC-{orden.pk:05d} actualizada correctamente.')
            return redirect('compras:orden-detail', pk=orden.pk)
        return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden, 'accion': 'Editar'})


class OrdenCompraDeleteView(DeleteView):
    model = OrdenCompra
    template_name = 'compras/orden_confirm_delete.html'
    success_url = reverse_lazy('compras:orden-list')

    def form_valid(self, form):
        messages.success(self.request, 'Orden de compra eliminada.')
        return super().form_valid(form)


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
            if form.cleaned_data.get('fecha_desde'):
                ordenes = ordenes.filter(fecha_orden__gte=form.cleaned_data['fecha_desde'])
            if form.cleaned_data.get('fecha_hasta'):
                ordenes = ordenes.filter(fecha_orden__lte=form.cleaned_data['fecha_hasta'])

        return render(request, self.template_name, {
            'form': form,
            'ordenes': ordenes,
            'ejecutado': ejecutado,
        })
