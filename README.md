# ClinicaCitas

Aplicación web para que una clínica pequeña gestione sus citas. Los pacientes reservan online en los huecos libres reales de cada profesional; recepción y profesionales organizan la agenda del día, y administración ve la ocupación y los pacientes que no se presentan.

Proyecto Final del Máster en Desarrollo Web Full Stack (Conquer Blocks). Backend en **Django** y flujo de reserva en **React** consumiendo una **API REST** del propio backend.

- **Demo:** https://clinicacitas.onrender.com (ver usuarios de prueba abajo; la primera carga puede tardar unos 50 s)
- **Memoria:** `docs/memoria.pdf`

## Funcionalidades

| Rol | Qué puede hacer |
|---|---|
| Paciente | Registrarse, reservar en 4 pasos (servicio → profesional → día y hora → confirmar), ver y cancelar sus citas (hasta 24 h antes) |
| Profesional | Ver su agenda del día, marcar citas como atendidas o no presentadas y guardar notas |
| Recepción | Ver la agenda de todos los profesionales, dar citas por teléfono eligiendo un hueco libre, cancelar y bloquear agenda (vacaciones, formación) |
| Administración | Panel de ocupación y no presentados de los últimos 30 días; alta de servicios, profesionales y horarios en el admin de Django |

Reglas de negocio:
- Los huecos se calculan a partir del horario semanal del profesional, la duración del servicio, las citas activas y los bloqueos, en pasos de 15 minutos.
- No se puede reservar con menos de 1 hora de antelación ni a más de 60 días vista.
- Un profesional nunca tiene dos citas activas solapadas: se valida en el modelo y, en la reserva, dentro de una transacción con `SELECT … FOR UPDATE` sobre el profesional, para que dos pacientes no reserven a la vez el mismo hueco.
- El paciente cancela online hasta 24 h antes; recepción puede cancelar siempre.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework 3.18 |
| Frontend de reserva | React 19 + Vite 7 (se compila dentro de `static/reserva/`) |
| Resto de pantallas | Plantillas de Django + CSS propio (sin frameworks) |
| Base de datos | SQLite en local y en la demo; PostgreSQL con solo definir `DATABASE_URL` |
| Despliegue | Render (Blueprint `render.yaml`), Gunicorn, WhiteNoise |
| Tests | `django.test` (42 tests) y Vitest para las utilidades de fechas |

## Estructura

```
config/                 Ajustes, URLs y WSGI
citas/
  models.py             Usuario (con rol), Paciente, Profesional, Servicio, Horario, Bloqueo, Cita
  services.py           Lógica de negocio: huecos libres, reservar, cancelar, marcar, estadísticas
  api.py                API REST (DRF) que usa React
  serializers.py
  views.py, forms.py    Pantallas de Django por rol
  management/commands/seed_demo.py   Datos y usuarios de prueba
  tests/                Tests de servicios, API y vistas
frontend/               Código fuente de la app React (src/components, api.js, fechas.js)
static/                 CSS general y la build de React (static/reserva/)
templates/              Plantillas de Django
```

## API REST

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/servicios/` | Público | Servicios activos |
| GET | `/api/profesionales/?servicio=<id>` | Público | Profesionales que ofrecen el servicio |
| GET | `/api/huecos/?profesional=<id>&servicio=<id>&desde=YYYY-MM-DD&dias=7` | Público | Huecos libres por día |
| GET | `/api/yo/` | Público | Usuario conectado y si puede reservar |
| GET | `/api/citas/` | Paciente | Mis citas |
| POST | `/api/citas/` | Paciente | Reservar `{profesional, servicio, inicio}` |
| POST | `/api/citas/<id>/cancelar/` | Paciente | Cancelar una cita propia |

La autenticación es la sesión de Django; los POST llevan el token CSRF de la cookie `csrftoken`.

## Instalación en local

Requisitos: Python 3.12+ y Node 20+ (Node solo si vas a modificar React).

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo           # datos y usuarios de prueba
python manage.py runserver           # http://127.0.0.1:8000
```

La build de React ya está incluida. Para trabajar en ella:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, redirige /api a Django
npm run build    # vuelve a generar static/reserva/
npm test
```

Tests del backend: `python manage.py test citas`

## Usuarios de prueba

Los crea `seed_demo`. Contraseña de todos: `Clinica2026!`

| Usuario | Rol |
|---|---|
| `paciente` | Paciente (Lucía, con una cita próxima) |
| `laura` | Profesional (fisioterapia) |
| `marta` | Profesional (psicología) |
| `recepcion` | Recepción |
| `admin` | Administración y admin de Django (`/admin/`) |

## Despliegue en Render

1. Sube el repositorio a GitHub.
2. En Render: **New → Blueprint**, elige el repositorio y pulsa **Apply**.
3. `render.yaml` crea el servicio web; `build.sh` instala dependencias, compila React, recopila estáticos, migra y carga los datos de ejemplo.

Variables de entorno: `SECRET_KEY` (la genera Render) y `DEBUG=False`.

**Base de datos de la demo:** SQLite, que se crea y se rellena con los datos de ejemplo en cada despliegue. El plan gratuito de Render solo permite una base PostgreSQL por cuenta y la borra a los 30 días, así que para una demo que tiene que seguir en línea hasta la defensa SQLite es más fiable. Contrapartida: el disco del plan gratuito no es persistente, así que las reservas nuevas se pierden cuando Render reinicia el servicio. Para producción basta con crear una base PostgreSQL y definir `DATABASE_URL`; el código no cambia.

## Uso de IA

En el desarrollo se ha usado un asistente de IA (Claude) como apoyo para generar código, tests y documentación. Todo el código se ha revisado, probado y está explicado en la memoria. Los commits hechos con su ayuda lo indican con `Co-Authored-By`.
