"""Системные проверки окружения: кодировка ФС и безопасное хранилище."""
import sys

from django.conf import settings
from django.core.checks import Tags, Warning, register

SAFE_STORAGE = 'shoe_catalog.storage.SafeFileSystemStorage'


@register(Tags.compatibility)
def check_filesystem_encoding(app_configs, **kwargs):
    enc = (sys.getfilesystemencoding() or '').lower().replace('-', '')
    if enc == 'utf8':
        return []
    return [Warning(
        'Файловая система использует кодировку %s вместо UTF-8.' % (enc or 'неизвестно'),
        hint='Задайте переменные окружения LANG=C.UTF-8 и LC_ALL=C.UTF-8 '
             'либо PYTHONUTF8=1. Иначе кириллические имена файлов породят '
             'суррогатные символы и ошибки записи в PostgreSQL.',
        id='core.W001',
    )]


@register(Tags.compatibility)
def check_storage_backend(app_configs, **kwargs):
    backend = settings.STORAGES.get('default', {}).get('BACKEND', '')
    if backend == SAFE_STORAGE:
        return []
    return [Warning(
        'Хранилище файлов по умолчанию не защищает от суррогатных символов.',
        hint='Установите STORAGES["default"]["BACKEND"] = "%s".' % SAFE_STORAGE,
        id='core.W002',
    )]