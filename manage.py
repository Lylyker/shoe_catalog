#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def ensure_utf8():
    """Гарантирует UTF-8 режим файловой системы.

    Если процесс запущен в локали C/POSIX, файловая система декодируется
    как ASCII с surrogateescape — источник суррогатных символов.
    В этом случае процесс один раз перезапускается в UTF-8 режиме.
    """
    enc = (sys.getfilesystemencoding() or '').lower().replace('-', '')
    if enc != 'utf8' and os.environ.get('PYTHONUTF8') != '1':
        os.environ['PYTHONUTF8'] = '1'
        os.environ.setdefault('LANG', 'C.UTF-8')
        os.environ.setdefault('LC_ALL', 'C.UTF-8')
        os.execv(sys.executable, [sys.executable] + sys.argv)

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoe_catalog.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    ensure_utf8()
    main()
