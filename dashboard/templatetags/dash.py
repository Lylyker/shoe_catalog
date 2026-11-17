from django import template

register = template.Library()


@register.filter
def get_attr(obj, path):
    """Разрешает точечный путь, включая вызов методов без аргументов."""
    cur = obj
    for bit in str(path).split('.'):
        if cur is None:
            return ''
        try:
            cur = getattr(cur, bit)
        except AttributeError:
            try:
                cur = cur[bit]
            except Exception:
                return ''
        if callable(cur):
            try:
                cur = cur()
            except Exception:
                return ''
    if cur is True:
        return 'Да'
    if cur is False:
        return 'Нет'
    return '' if cur is None else cur


@register.filter
def money(value):
    try:
        return '{:,.2f}'.format(float(value)).replace(',', ' ')
    except (TypeError, ValueError):
        return value