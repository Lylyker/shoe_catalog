"""Безопасное файловое хранилище для загружаемых изображений.

Устраняет суррогатные символы (surrogateescape) в именах файлов на всех
точках входа: сохранение, генерация имени, проверка доступности, удаление.
"""
from django.core.files.storage import FileSystemStorage

from core.sanitize import strip_surrogates


class SafeFileSystemStorage(FileSystemStorage):
    """FileSystemStorage с очисткой имён файлов от суррогатных символов."""

    def save(self, name, content, max_length=None):
        return super().save(strip_surrogates(name), content, max_length)

    def generate_filename(self, filename):
        return super().generate_filename(strip_surrogates(filename))

    def get_valid_name(self, name):
        return super().get_valid_name(strip_surrogates(name))

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(strip_surrogates(name), max_length)

    def delete(self, name):
        return super().delete(strip_surrogates(name))

    def exists(self, name):
        return super().exists(strip_surrogates(name))

    def url(self, name):
        return super().url(strip_surrogates(name))

    def path(self, name):
        return super().path(strip_surrogates(name))