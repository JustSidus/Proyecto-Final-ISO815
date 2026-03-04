from rest_framework import serializers

from .models import AsientoContable


class AsientoContableSerializer(serializers.ModelSerializer):
    tipo_movimiento_display = serializers.CharField(
        source='get_tipo_movimiento_display', read_only=True
    )

    class Meta:
        model = AsientoContable
        fields = [
            'id',
            'descripcion',
            'tipo_inventario',
            'cuenta_contable',
            'tipo_movimiento',
            'tipo_movimiento_display',
            'fecha',
            'monto',
            'estado',
        ]
