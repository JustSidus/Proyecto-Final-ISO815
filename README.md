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
- **Login web:** http://127.0.0.1:8000/login/
- **Admin Django:** http://127.0.0.1:8000/admin/
- **API Asientos Contables:** http://127.0.0.1:8000/api/asientos/
- **Login API (Browsable API):** http://127.0.0.1:8000/api-auth/login/

## Autenticación y permisos

- La app web requiere iniciar sesión para acceder a módulos de compras.
- La API de asientos permite lectura pública (`GET`, `HEAD`, `OPTIONS`).
- La escritura en API (`POST`, `PUT`, `PATCH`, `DELETE`) requiere usuario autenticado con permisos del modelo.
- Al completar una orden de compra, el sistema genera automáticamente 2 asientos contables (DB y CR).
- `GET /api/asientos/` retorna una lista directa de asientos (sin paginación), lista para consumo por WS externo.
- Para gestionar usuarios, grupos y permisos use el Admin de Django:
	- Usuarios: http://127.0.0.1:8000/admin/auth/user/
	- Grupos: http://127.0.0.1:8000/admin/auth/group/
- Puedes crear usuarios regulares (no superuser) desde Admin desmarcando `Staff status` y `Superuser status`.

## Postman (API Asientos)

- `GET http://127.0.0.1:8000/api/asientos/` no requiere autenticación.
- Para `POST/PUT/PATCH/DELETE`:
	1. En Postman, pestaña **Authorization**.
	2. Elegir **Basic Auth**.
	3. Colocar usuario y contraseña de Django.
	4. En Admin, asignar permisos del modelo `Asiento Contable` (`add/change/delete`) al usuario o grupo.

## Equipo

- **Profesor:** Juan P. Valdez
- **Asignatura:** ISO815
- **Institución:** Universidad Apec
- **Año:** 2025
