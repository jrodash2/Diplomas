from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money_gtq(value):
    if value is None:
        amount = Decimal('0.00')
    elif isinstance(value, Decimal):
        amount = value
    else:
        try:
            amount = Decimal(str(value).replace(',', ''))
        except (InvalidOperation, ValueError, TypeError):
            amount = Decimal('0.00')
    return f"Q {amount:,.2f}"
