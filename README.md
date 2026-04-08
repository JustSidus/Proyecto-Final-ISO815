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
python -m pip install -r requirements.txt

# 4. Configurar el entorno
# Copiar el archivo de ejemplo de variables de entorno
cp .env.example .env
# En Windows PowerShell:
# Copy-Item .env.example .env

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario (para acceder al admin)
python manage.py createsuperuser

# 7. Correr el servidor LOCAL
python manage.py runserver
```

## Acceder al sistema

- **Sistema principal:** http://127.0.0.1:8000/
- **Login web:** http://127.0.0.1:8000/login/
- **Admin Django:** http://127.0.0.1:8000/admin/
- **API Asientos Contables:** http://127.0.0.1:8000/api/asientos/
- **Login API (Browsable API):** http://127.0.0.1:8000/api-auth/login/

## Integracion con WS Contable

La app puede enviar automaticamente los asientos al WS contable cuando una orden cambia a estado `Completada`.

### Campos enviados (minimos necesarios)

- `descripcion`
- `auxiliar.id`
- `fechaAsiento`
- `montoTotal`
- `detalles` (2 lineas: Debito y Credito)
- `estado`

### Trazabilidad local

Cada `AsientoContable` guarda:

- estado de envio (`Pendiente`, `Enviado`, `Error`)
- id remoto del asiento
- fecha de envio
- mensaje de error

Esto permite detectar y corregir incompatibilidades de mapeo sin perder el asiento local.

## Equipo

- **Profesor:** Juan P. Valdez
- **Asignatura:** ISO815
- **Institución:** Universidad Apec
- **Año:** 2026
