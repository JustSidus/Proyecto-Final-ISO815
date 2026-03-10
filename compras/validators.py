import re

from django.core.exceptions import ValidationError


def limpiar_documento(valor):
    return re.sub(r'\D', '', valor or '')


def formatear_documento_dominicano(tipo_documento, valor):
    documento = limpiar_documento(valor)
    if tipo_documento == 'CED' and len(documento) == 11:
        return f'{documento[:3]}-{documento[3:10]}-{documento[10]}'
    if tipo_documento == 'RNC' and len(documento) == 9:
        return f'{documento[:3]}-{documento[3:9]}'
    return documento


def _calcular_verificador_luhn_estandar(cuerpo):
    suma = 0
    for indice, char in enumerate(cuerpo):
        digito = int(char)
        if indice % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito

    return (10 - (suma % 10)) % 10


def _valida_luhn_variante(documento):
    suma = 0
    for indice, char in enumerate(reversed(documento), start=1):
        digito = int(char)
        if indice % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito

    return suma % 10 == 0


def validar_cedula_dominicana(valor):
    documento = limpiar_documento(valor)
    if len(documento) != 11 or not documento.isdigit():
        raise ValidationError('La cédula debe contener exactamente 11 dígitos.')

    verificador_estandar = _calcular_verificador_luhn_estandar(documento[:10])
    valida_estandar = verificador_estandar == int(documento[-1])
    valida_variante = _valida_luhn_variante(documento)

    if not (valida_estandar or valida_variante):
        raise ValidationError('La cédula no es válida según la verificación de Luhn.')

    return documento


def validar_rnc_dominicano(valor):
    documento = limpiar_documento(valor)
    if len(documento) != 9 or not documento.isdigit():
        raise ValidationError('El RNC debe contener exactamente 9 dígitos.')

    pesos = [7, 9, 8, 6, 5, 4, 3, 2]
    suma = sum(int(digito) * peso for digito, peso in zip(documento[:8], pesos))

    verificador = 11 - (suma % 11)
    if verificador == 10:
        verificador = 1
    elif verificador == 11:
        verificador = 2

    if verificador != int(documento[-1]):
        raise ValidationError('El RNC dominicano no es válido.')

    return documento
