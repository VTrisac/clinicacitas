"""Carga datos de ejemplo y usuarios de prueba (uno por rol). Se puede ejecutar varias veces."""
import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from citas import services
from citas.models import Bloqueo, Cita, Horario, Paciente, Profesional, Servicio, Usuario

CLAVE_DEMO = 'Clinica2026!'

SERVICIOS = [
    ('Fisioterapia', 'Sesión de tratamiento manual y ejercicios', 45, 40),
    ('Primera valoración', 'Exploración inicial y plan de tratamiento', 60, 50),
    ('Masaje descontracturante', 'Masaje de espalda, cuello y hombros', 30, 30),
    ('Psicología', 'Sesión individual de terapia', 50, 55),
    ('Nutrición', 'Consulta y plan de alimentación', 30, 35),
]

PROFESIONALES = [
    # usuario, nombre, apellidos, especialidad, color, servicios, franjas (día, inicio, fin)
    ('laura', 'Laura', 'Martín Ruiz', 'Fisioterapeuta', '#2f7d6d',
     ['Fisioterapia', 'Primera valoración', 'Masaje descontracturante'],
     [(d, time(9), time(14)) for d in range(5)] + [(1, time(16), time(19)), (3, time(16), time(19))]),
    ('javier', 'Javier', 'Soler Pérez', 'Fisioterapeuta deportivo', '#3a6ea5',
     ['Fisioterapia', 'Masaje descontracturante'],
     [(d, time(15), time(20)) for d in range(5)]),
    ('marta', 'Marta', 'Gil Navarro', 'Psicóloga sanitaria', '#8a5a9e',
     ['Psicología'],
     [(0, time(10), time(14)), (2, time(10), time(14)), (4, time(10), time(14)), (2, time(16), time(19))]),
    ('sergio', 'Sergio', 'Ortega Vidal', 'Dietista-nutricionista', '#c07a2c',
     ['Nutrición', 'Primera valoración'],
     [(1, time(9), time(13)), (3, time(9), time(13))]),
]

PACIENTES = [
    ('paciente', 'Lucía', 'Fernández López', '611223344'),
    ('pablo', 'Pablo', 'García Sanz', '622334455'),
    ('elena', 'Elena', 'Romero Díaz', '633445566'),
    ('david', 'David', 'Moreno Castro', '644556677'),
    ('carmen', 'Carmen', 'Jiménez Ruiz', '655667788'),
    ('andres', 'Andrés', 'Muñoz Gómez', '666778899'),
    ('sofia', 'Sofía', 'Álvarez Torres', '677889900'),
    ('raul', 'Raúl', 'Navarro Ibáñez', '688990011'),
]


def usuario(username, nombre, apellidos, rol, **extra):
    u, creado = Usuario.objects.get_or_create(username=username, defaults={
        'first_name': nombre, 'last_name': apellidos, 'rol': rol,
        'email': f'{username}@clinicacitas.demo', **extra})
    if creado:
        u.set_password(CLAVE_DEMO)
        u.save()
    return u


class Command(BaseCommand):
    help = 'Crea servicios, profesionales, pacientes, citas y usuarios de prueba.'

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(2026)
        servicios = {}
        for nombre, desc, dur, precio in SERVICIOS:
            servicios[nombre], _ = Servicio.objects.get_or_create(
                nombre=nombre, defaults={'descripcion': desc, 'duracion_min': dur, 'precio': precio})

        profesionales = []
        for user, nombre, apellidos, esp, color, servs, franjas in PROFESIONALES:
            u = usuario(user, nombre, apellidos, Usuario.Rol.PROFESIONAL)
            prof, creado = Profesional.objects.get_or_create(usuario=u, defaults={'especialidad': esp, 'color': color})
            if creado:
                prof.servicios.set([servicios[s] for s in servs])
                for dia, ini, fin in franjas:
                    Horario.objects.create(profesional=prof, dia_semana=dia, hora_inicio=ini, hora_fin=fin)
            profesionales.append(prof)

        usuario('recepcion', 'Nuria', 'Campos Gil', Usuario.Rol.RECEPCION)
        usuario('admin', 'Admin', 'Clínica', Usuario.Rol.ADMIN, is_staff=True, is_superuser=True)

        pacientes = []
        for user, nombre, apellidos, tel in PACIENTES:
            u = usuario(user, nombre, apellidos, Usuario.Rol.PACIENTE)
            pacientes.append(Paciente.objects.get_or_create(usuario=u, defaults={'telefono': tel})[0])

        if Cita.objects.exists():
            self.stdout.write(self.style.WARNING('Ya hay citas: no se generan más.'))
            return

        hoy = timezone.localdate()
        # Vacaciones de Javier dentro de dos semanas (se ve en recepción y quita huecos)
        inicio_vac = timezone.make_aware(datetime.combine(hoy + timedelta(days=14), time(0)))
        Bloqueo.objects.create(profesional=profesionales[1], inicio=inicio_vac,
                               fin=inicio_vac + timedelta(days=3), motivo='Vacaciones')

        creadas = 0
        for prof in profesionales:
            servs = list(prof.servicios.all())
            for offset in range(-30, 21):
                dia = hoy + timedelta(days=offset)
                for franja in prof.horarios.filter(dia_semana=dia.weekday()):
                    actual = timezone.make_aware(datetime.combine(dia, franja.hora_inicio))
                    fin_franja = timezone.make_aware(datetime.combine(dia, franja.hora_fin))
                    while True:
                        serv = random.choice(servs)
                        fin = actual + timedelta(minutes=serv.duracion_min)
                        if fin > fin_franja:
                            break
                        ocupar = random.random() < (0.7 if offset < 0 else 0.45)
                        if ocupar and not Cita.objects.solapadas(prof, actual, fin).exists() \
                                and not prof.bloqueos.filter(inicio__lt=fin, fin__gt=actual).exists():
                            estado = Cita.Estado.CONFIRMADA
                            if fin <= timezone.now():
                                estado = random.choices(
                                    [Cita.Estado.ATENDIDA, Cita.Estado.NO_PRESENTADA, Cita.Estado.CANCELADA],
                                    weights=[82, 8, 10])[0]
                            Cita.objects.create(paciente=random.choice(pacientes), profesional=prof, servicio=serv,
                                                inicio=actual, fin=fin, estado=estado, creada_por=None)
                            creadas += 1
                        actual = fin if ocupar else actual + timedelta(minutes=15)

        # Una cita próxima garantizada para el paciente de prueba, reservada con la lógica real
        lucia = pacientes[0]
        fisio = servicios['Fisioterapia']
        for offset in range(3, 15):
            huecos = services.huecos_libres(profesionales[0], fisio, hoy + timedelta(days=offset))
            if huecos:
                services.reservar(paciente=lucia, profesional=profesionales[0], servicio=fisio,
                                  inicio=huecos[len(huecos) // 2], creada_por=lucia.usuario)
                creadas += 1
                break

        self.stdout.write(self.style.SUCCESS(
            f'Datos de ejemplo creados: {len(profesionales)} profesionales, {len(pacientes)} pacientes, '
            f'{creadas} citas. Contraseña de todos los usuarios de prueba: {CLAVE_DEMO}'))
