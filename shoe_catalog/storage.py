"""
Безопасное файловое хранилище.

Устраняет суррогатные символы (surrogateescape) в именах загружаемых файлов,
из-за которых PostgreSQL выдаёт:
UnicodeEncodeError: 'utf-8' codec can't encode character '\udcd0' ...
"""
from django.core.files.storage import FileSystemStorage


def clean_surrogates(value: str) -> str:
    """Возвращает строку без суррогатов, восстанавливая исходные UTF-8 байты."""
    if not isinstance(value, str):
        return value
    try:
        # surrogateescape вернёт исходные байты, затем корректно декодируем их
        return value.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value.encode('utf-8', 'ignore').decode('utf-8')


class SafeFileSystemStorage(FileSystemStorage):
    def generate_filename(self, filename):
        return super().generate_filename(clean_surrogates(filename))

    def get_valid_name(self, name):
        return super().get_valid_name(clean_surrogates(name))

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(clean_surrogates(name), max_length)