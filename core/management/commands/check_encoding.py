"""Проверка исходников: кодировка, синтаксис, суррогаты в строковых константах.

    python manage.py check_encoding
Код возврата 1 при ошибках — используется в git pre-commit hook.
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SKIP_DIRS = {'myvenv', '.venv', '.venv312', 'venv', '__pycache__', '.git',
             'node_modules', 'media', 'backup', '.idea'}
TEXT_EXT = {'.py', '.html', '.css', '.js', '.txt', '.md'}
SURROGATE_HINT = re.compile(r'\\u[dD][89a-fA-F][0-9a-fA-F]{2}')


def iter_constants(code):
    for const in code.co_consts:
        if isinstance(const, str):
            yield const
        elif hasattr(const, 'co_consts'):
            yield from iter_constants(const)


def contains_surrogates(text):
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


class Command(BaseCommand):
    help = 'Проверяет исходники на битую кодировку и суррогатные символы'

    def add_arguments(self, parser):
        parser.add_argument('--quiet', action='store_true', help='Печатать только проблемы')

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR)
        errors, hints, checked = [], [], 0

        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.suffix not in TEXT_EXT:
                continue
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            checked += 1
            rel = path.relative_to(root)
            raw = path.read_bytes()

            try:
                source = raw.decode('utf-8')
            except UnicodeDecodeError as exc:
                errors.append(f'{rel}: невалидный UTF-8 на байте {exc.start}')
                continue

            if contains_surrogates(source):
                errors.append(f'{rel}: суррогатный символ в тексте файла')

            if path.suffix != '.py':
                continue

            try:
                code = compile(source, str(rel), 'exec')
            except SyntaxError as exc:
                errors.append(f'{rel}:{exc.lineno}: {exc.msg}')
                continue
            except (UnicodeEncodeError, ValueError) as exc:
                errors.append(f'{rel}: {exc}')
                continue

            for const in iter_constants(code):
                if contains_surrogates(const):
                    errors.append(
                        f'{rel}: escape-последовательность суррогата в строке '
                        f'({const[:40]!r}). Используйте raw-строку r"..." или уберите её.'
                    )
                    break

            for num, line in enumerate(source.splitlines(), 1):
                if SURROGATE_HINT.search(line):
                    hints.append(f'{rel}:{num}: похоже на суррогатный escape')

        for item in hints:
            self.stdout.write(self.style.WARNING('HINT ' + item))
        for item in errors:
            self.stdout.write(self.style.ERROR('FAIL ' + item))

        if errors:
            self.stdout.write(self.style.ERROR(
                f'Проверено файлов: {checked}. Ошибок: {len(errors)}.'))
            raise SystemExit(1)

        if not options['quiet']:
            self.stdout.write(self.style.SUCCESS(
                f'Проверено файлов: {checked}. Проблем кодировки не найдено.'))