# Sistema de Compras - UNAPEC

Proyecto final de asignatura Compras e interfaz con Contabilidad. Desarrollado en Django 6.0.3 con API REST.

## Instalación y Setup

```bash
# 1. Clonar el repositorio
git clone https://github.com/JustSidus/Proyecto-Final-ISO815.git
cd Proyecto-Final-ISO815

# 2. Crear y activar el entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear superusuario (para acceder al admin)
python manage.py createsuperuser

# 6. Correr el servidor
python manage.py runserver
```

## Acceder al sistema

- **Sistema principal:** http://127.0.0.1:8000/
- **Admin Django:** http://127.0.0.1:8000/admin/
- **API Asientos Contables:** http://127.0.0.1:8000/api/asientos/

## Equipo

- **Profesor:** Juan P. Valdez
- **Asignatura:** ISO815
- **Institución:** Universidad Apec
- **Año:** 2025
