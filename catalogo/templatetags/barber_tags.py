"""
Template tags y filtros de utilidad para Demo Barber Club.
"""
from django import template
from catalogo.models import formatear_clp

register = template.Library()


@register.filter(name='clp')
def clp_filter(valor):
    """Convierte un número a formato de moneda chilena: 18000 -> $18.000"""
    return formatear_clp(valor)


@register.filter(name='formatear_clp_tag')
def formatear_clp_tag_filter(valor):
    """Convierte un número a formato de moneda chilena: 18000 -> $18.000"""
    return formatear_clp(valor)


@register.filter(name='rango')
def rango_filter(valor):
    """Genera una lista para iterar en plantillas: 5 -> [0, 1, 2, 3, 4]"""
    try:
        return range(int(valor))
    except (ValueError, TypeError):
        return []


@register.filter(name='split')
def split_filter(value, delimiter=" "):
    """Divide un texto por un delimitador"""
    if not value:
        return []
    return value.split(delimiter)
