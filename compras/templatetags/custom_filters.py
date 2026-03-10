from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Accede a un elemento de un diccionario usando un key.
    Uso en template: {{ diccionario|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
