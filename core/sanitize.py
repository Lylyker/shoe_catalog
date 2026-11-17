"""Очистка строк от суррогатных символов (surrogateescape).

Суррогаты появляются, когда байты UTF-8 декодируются кодировкой ASCII
с обработчиком surrogateescape (локаль C/POSIX). PostgreSQL такие строки
не принимает: UnicodeEncodeError — surrogates not allowed.
"""


def has_surrogates(value):
    """True, если в строке есть символы из диапазона U+D800..U+DFFF."""
    if not isinstance(value, str) or value.isascii():
        return False
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)


def strip_surrogates(value):
    """Восстанавливает исходные байты и корректно декодирует их в UTF-8."""
    if not isinstance(value, str) or value.isascii():
        return value
    try:
        value.encode('utf-8')
        return value
    except UnicodeEncodeError:
        pass
    try:
        return value.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value.encode('utf-8', 'ignore').decode('utf-8')


def sanitize_instance(instance):
    """Чистит все текстовые и файловые поля модели. Возвращает список изменённых полей."""
    from django.db.models import CharField, TextField, FileField

    changed = []
    for field in instance._meta.concrete_fields:
        if isinstance(field, (CharField, TextField)):
            current = getattr(instance, field.attname, None)
            cleaned = strip_surrogates(current)
            if cleaned != current:
                setattr(instance, field.attname, cleaned)
                changed.append(field.name)
        elif isinstance(field, FileField):
            file_field = getattr(instance, field.name, None)
            name = getattr(file_field, 'name', None)
            cleaned = strip_surrogates(name)
            if isinstance(name, str) and cleaned != name:
                file_field.name = cleaned
                changed.append(field.name)
    return changed