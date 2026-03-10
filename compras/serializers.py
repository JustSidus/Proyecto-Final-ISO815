from rest_framework import serializers

from .models import AsientoContable


class AsientoContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsientoContable
        fields = [
            'id',
            'descripcion',
            'tipo_inventario',
            'cuenta_contable',
            'tipo_movimiento',
            'fecha',
            'monto',
            'estado',
        ]
