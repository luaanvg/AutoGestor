from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def brl(value):
    """Exibe um número no padrão brasileiro: R$ 12.345,67."""

    try:
        number = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        return "R$ 0,00"
    formatted = f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


@register.filter
def status_class(status):
    return {
        "available": "success",
        "reserved": "warning",
        "sold": "neutral",
        "confirmed": "success",
        "canceled": "danger",
    }.get(status, "neutral")


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
