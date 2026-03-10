from django import forms
from django.forms import inlineformset_factory

from .models import (
    Articulo,
    Departamento,
    OrdenCompra,
    OrdenCompraDetalle,
    Proveedor,
    UnidadMedida,
)
from .validators import (
    formatear_documento_dominicano,
    limpiar_documento,
    validar_cedula_dominicana,
    validar_rnc_dominicano,
)


class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nombre', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['descripcion', 'estado']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProveedorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipo_documento = self._obtener_tipo_documento_actual()

        if tipo_documento == Proveedor.TIPO_CEDULA:
            self.fields['cedula_rnc'].label = 'Cédula'
            placeholder = '000-0000000-0'
            maxlength = 13
        else:
            self.fields['cedula_rnc'].label = 'RNC'
            placeholder = '000-000000'
            maxlength = 10

        self.fields['cedula_rnc'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'maxlength': str(maxlength),
            'placeholder': placeholder,
        })

    def _obtener_tipo_documento_actual(self):
        tipo_documento = self.initial.get('tipo_documento')

        if self.instance and self.instance.pk:
            tipo_documento = self.instance.tipo_documento

        if self.data:
            tipo_documento = self.data.get('tipo_documento', tipo_documento)

        if tipo_documento not in {Proveedor.TIPO_CEDULA, Proveedor.TIPO_RNC}:
            return Proveedor.TIPO_RNC
        return tipo_documento

    def clean_cedula_rnc(self):
        tipo_documento = self.cleaned_data.get('tipo_documento')
        documento = limpiar_documento(self.cleaned_data.get('cedula_rnc'))

        if tipo_documento == Proveedor.TIPO_CEDULA:
            digitos = validar_cedula_dominicana(documento)
        elif tipo_documento == Proveedor.TIPO_RNC:
            digitos = validar_rnc_dominicano(documento)
        else:
            raise forms.ValidationError('Selecciona un tipo de documento válido.')

        return formatear_documento_dominicano(tipo_documento, digitos)

    class Meta:
        model = Proveedor
        fields = ['tipo_documento', 'cedula_rnc', 'nombre_comercial', 'estado']
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'cedula_rnc': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_comercial': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'cedula_rnc': 'Documento',
        }


class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['descripcion', 'marca', 'unidad_medida', 'existencia', 'estado']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'existencia': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ['proveedor', 'departamento']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
        }


class OrdenCompraDetalleForm(forms.ModelForm):
    class Meta:
        model = OrdenCompraDetalle
        fields = ['articulo', 'cantidad', 'unidad_medida', 'costo_unitario']
        widgets = {
            'articulo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


# Formset para ingresar múltiples líneas de detalle en la misma vista de OrdenCompra
OrdenCompraDetalleFormSet = inlineformset_factory(
    OrdenCompra,
    OrdenCompraDetalle,
    form=OrdenCompraDetalleForm,
    extra=1,
    can_delete=True,
)


class ConsultaOrdenesForm(forms.Form):
    """Formulario de consulta/filtrado de órdenes de compra."""
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.filter(estado=True),
        required=False,
        empty_label='Todos los departamentos',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(estado=True),
        required=False,
        empty_label='Todos los proveedores',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + OrdenCompra.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    codigo_orden = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'list': 'ordenes-autocomplete',
            'autocomplete': 'off',
            'placeholder': 'Ej: OC-00021',
        }),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
