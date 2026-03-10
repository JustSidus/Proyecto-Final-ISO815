from rest_framework import viewsets, filters, permissions

from .models import AsientoContable
from .serializers import AsientoContableSerializer


class AsientoContableViewSet(viewsets.ModelViewSet):
    """
    API REST para Asientos Contables.

    Soporta operaciones CRUD completas:
      - GET    /api/asientos/         → listar todos
      - POST   /api/asientos/         → crear asiento
      - GET    /api/asientos/{id}/    → detalle de uno
      - PUT    /api/asientos/{id}/    → actualizar completo
      - PATCH  /api/asientos/{id}/    → actualizar parcial
      - DELETE /api/asientos/{id}/    → eliminar

    Filtros disponibles por query params:
      - ?tipo_movimiento=DB          → solo débitos
      - ?tipo_movimiento=CR          → solo créditos
      - ?estado=true                 → solo activos
      - ?search=descripcion          → búsqueda en descripción y cuenta contable
    """

    queryset = AsientoContable.objects.all().order_by('-fecha')
    serializer_class = AsientoContableSerializer

    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descripcion', 'cuenta_contable']
    ordering_fields = ['fecha', 'monto', 'tipo_movimiento']

    def get_queryset(self):
        qs = super().get_queryset()
        tipo = self.request.query_params.get('tipo_movimiento')
        estado = self.request.query_params.get('estado')
        if tipo:
            qs = qs.filter(tipo_movimiento=tipo)
        if estado is not None:
            qs = qs.filter(estado=estado.lower() in ('true', '1', 'yes'))
        return qs
