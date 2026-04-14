from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import AsientoContableViewSet

app_name = 'compras'

# ── DRF Router ────────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'asientos', AsientoContableViewSet, basename='asiento')

urlpatterns = [
    # ── Página de inicio ──────────────────────────────────────────────────────
    path('', views.IndexView.as_view(), name='index'),

    # ── Departamentos ─────────────────────────────────────────────────────────
    path('departamentos/', views.DepartamentoListView.as_view(), name='departamento-list'),
    path('departamentos/nuevo/', views.DepartamentoCreateView.as_view(), name='departamento-create'),
    path('departamentos/<int:pk>/editar/', views.DepartamentoUpdateView.as_view(), name='departamento-update'),
    path('departamentos/<int:pk>/eliminar/', views.DepartamentoDeleteView.as_view(), name='departamento-delete'),

    # ── Unidades de Medida ────────────────────────────────────────────────────
    path('unidades-medida/', views.UnidadMedidaListView.as_view(), name='unidadmedida-list'),
    path('unidades-medida/nueva/', views.UnidadMedidaCreateView.as_view(), name='unidadmedida-create'),
    path('unidades-medida/<int:pk>/editar/', views.UnidadMedidaUpdateView.as_view(), name='unidadmedida-update'),
    path('unidades-medida/<int:pk>/eliminar/', views.UnidadMedidaDeleteView.as_view(), name='unidadmedida-delete'),

    # ── Proveedores ───────────────────────────────────────────────────────────
    path('proveedores/', views.ProveedorListView.as_view(), name='proveedor-list'),
    path('proveedores/nuevo/', views.ProveedorCreateView.as_view(), name='proveedor-create'),
    path('proveedores/<int:pk>/editar/', views.ProveedorUpdateView.as_view(), name='proveedor-update'),
    path('proveedores/<int:pk>/eliminar/', views.ProveedorDeleteView.as_view(), name='proveedor-delete'),

    # ── Artículos ─────────────────────────────────────────────────────────────
    path('articulos/', views.ArticuloListView.as_view(), name='articulo-list'),
    path('articulos/nuevo/', views.ArticuloCreateView.as_view(), name='articulo-create'),
    path('articulos/<int:pk>/editar/', views.ArticuloUpdateView.as_view(), name='articulo-update'),
    path('articulos/<int:pk>/eliminar/', views.ArticuloDeleteView.as_view(), name='articulo-delete'),

    # ── Órdenes de Compra ─────────────────────────────────────────────────────
    path('ordenes/', views.OrdenCompraListView.as_view(), name='orden-list'),
    path('ordenes/backlog/', views.OrdenCompraBacklogView.as_view(), name='orden-backlog'),
    path('ordenes/autocomplete/', views.OrdenCompraAutocompleteView.as_view(), name='orden-autocomplete'),
    path('ordenes/archivadas/', views.OrdenCompraArchivadasView.as_view(), name='orden-archivadas'),
    path('ordenes/nueva/', views.OrdenCompraCreateView.as_view(), name='orden-create'),
    path('ordenes/<int:pk>/', views.OrdenCompraDetailView.as_view(), name='orden-detail'),
    path('ordenes/<int:pk>/editar/', views.OrdenCompraUpdateView.as_view(), name='orden-update'),
    path('ordenes/<int:pk>/estado/', views.OrdenCompraCambiarEstadoView.as_view(), name='orden-estado-update'),
    path('ordenes/<int:pk>/eliminar/', views.OrdenCompraDeleteView.as_view(), name='orden-delete'),

    # ── Consulta por criterios ────────────────────────────────────────────────
    path('consulta/', views.ConsultaOrdenesView.as_view(), name='consulta-ordenes'),

    # ── API REST ──────────────────────────────────────────────────────────────
    path('api/', include(router.urls)),
]
