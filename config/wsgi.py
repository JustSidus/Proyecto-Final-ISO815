"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from pathlib import Path

# Cargar variables de entorno desde .env si existe (principalmente para desarrollo)
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # Si python-dotenv no está instalado, ignorar (normalmente en producción
    # las variables vienen del sistema operativo / Azure)
    pass
