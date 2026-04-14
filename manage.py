#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env si existe (para desarrollo)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        has_addrport = any(not arg.startswith('-') for arg in sys.argv[2:])
        if not has_addrport:
            default_addrport = os.environ.get('DJANGO_RUNSERVER_ADDRPORT', '127.0.0.1:8010').strip()
            if default_addrport:
                sys.argv.append(default_addrport)

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
    main()
