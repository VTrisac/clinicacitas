"""Datos mínimos para los tests."""
from datetime import date, time, timedelta

from citas.models import Horario, Paciente, Profesional, Servicio, Usuario


def proximo(dia_semana, desde=None):
    """Próxima fecha (a partir de mañana) que cae en `dia_semana` (0 = lunes)."""
    d = (desde or date.today()) + timedelta(days=1)
    while d.weekday() != dia_semana:
        d += timedelta(days=1)
    return d


def crear_usuario(username, rol, **extra):
    return Usuario.objects.create_user(username=username, password='Clave-de-test-1', rol=rol,
                                       first_name=username.capitalize(), **extra)


def crear_paciente(username='paciente'):
    return Paciente.objects.create(usuario=crear_usuario(username, Usuario.Rol.PACIENTE), telefono='600000000')


def crear_servicio(nombre='Fisioterapia', duracion=45, precio=40):
    return Servicio.objects.create(nombre=nombre, duracion_min=duracion, precio=precio)


def crear_profesional(username='ana', servicios=(), franjas=((0, time(9), time(13)),)):
    prof = Profesional.objects.create(usuario=crear_usuario(username, Usuario.Rol.PROFESIONAL),
                                      especialidad='Fisioterapia')
    prof.servicios.set(servicios)
    for dia, ini, fin in franjas:
        Horario.objects.create(profesional=prof, dia_semana=dia, hora_inicio=ini, hora_fin=fin)
    return prof
