from django import template

register = template.Library()

@register.filter
def capitalize_words(value):
    """Capitaliza cada palabra sin importar que venga en mayúsculas."""
    if not value:
        return ""
    palabras = value.split()
    return " ".join(p.capitalize() for p in palabras)
