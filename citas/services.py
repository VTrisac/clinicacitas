"""Lógica de negocio de la agenda: cálculo de huecos libres y operaciones sobre citas.

Se mantiene fuera de las vistas para que la usen igual la web (plantillas), la API (React)
y los tests.
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Bloqueo, Cita, Horario, Profesional


def _conf(clave):
    return settings.CITAS[clave]


def _aware(fecha, hora):
    return timezone.make_aware(datetime.combine(fecha, hora))


def huecos_libres(profesional, servicio, fecha, ahora=None):
    """Horas de inicio posibles para `servicio` con `profesional` el día `fecha`.

    Recorre cada franja del horario de ese día en pasos de PASO_MINUTOS y descarta los
    huecos que no caben en la franja, que se solapan con una cita activa o un bloqueo,
    o que empiezan antes de ahora + MARGEN_RESERVA_MIN.
    """
    if not profesional.activo or not servicio.activo:
        return []
    if not profesional.servicios.filter(pk=servicio.pk).exists():
        return []

    ahora = ahora or timezone.now()
    limite = ahora + timedelta(minutes=_conf('MARGEN_RESERVA_MIN'))
    paso = timedelta(minutes=_conf('PASO_MINUTOS'))
    duracion = timedelta(minutes=servicio.duracion_min)

    inicio_dia = _aware(fecha, datetime.min.time())
    fin_dia = inicio_dia + timedelta(days=1)
    ocupado = [(c.inicio, c.fin) for c in Cita.objects.activas().filter(
        profesional=profesional, inicio__lt=fin_dia, fin__gt=inicio_dia)]
    ocupado += [(b.inicio, b.fin) for b in Bloqueo.objects.filter(
        profesional=profesional, inicio__lt=fin_dia, fin__gt=inicio_dia)]

    huecos = []
    for franja in Horario.objects.filter(profesional=profesional, dia_semana=fecha.weekday()):
        actual = _aware(fecha, franja.hora_inicio)
        fin_franja = _aware(fecha, franja.hora_fin)
        while actual + duracion <= fin_franja:
            fin = actual + duracion
            libre = all(not (actual < o_fin and fin > o_ini) for o_ini, o_fin in ocupado)
            if actual >= limite and libre:
                huecos.append(actual)
            actual += paso
    return sorted(huecos)


@transaction.atomic
def reservar(*, paciente, profesional, servicio, inicio, creada_por, estado=Cita.Estado.CONFIRMADA):
    """Crea una cita si `inicio` es un hueco libre. Lanza ValidationError si no lo es.

    Se bloquea la fila del profesional (SELECT ... FOR UPDATE) para que dos reservas
    simultáneas del mismo hueco no pasen las dos la comprobación.
    """
    Profesional.objects.select_for_update().get(pk=profesional.pk)
    inicio = timezone.localtime(inicio)
    if inicio.date() > timezone.localdate() + timedelta(days=_conf('DIAS_VISIBLES')):
        raise ValidationError('Todavía no se pueden reservar citas para esa fecha.')
    if inicio not in huecos_libres(profesional, servicio, inicio.date()):
        raise ValidationError('Ese hueco ya no está disponible. Elige otra hora.')
    cita = Cita(paciente=paciente, profesional=profesional, servicio=servicio, inicio=inicio,
                fin=inicio + timedelta(minutes=servicio.duracion_min), estado=estado, creada_por=creada_por)
    cita.full_clean()
    cita.save()
    return cita


def puede_gestionar(usuario, cita):
    """Quién puede ver y modificar una cita."""
    if usuario.es_personal:
        return True
    if usuario.es_profesional:
        return cita.profesional.usuario_id == usuario.pk
    return cita.paciente.usuario_id == usuario.pk


def cancelar(cita, usuario, ahora=None):
    if not puede_gestionar(usuario, cita):
        raise PermissionDenied
    if cita.estado not in (Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA):
        raise ValidationError('Solo se pueden cancelar citas pendientes o confirmadas.')
    ahora = ahora or timezone.now()
    if usuario.es_paciente and cita.inicio - ahora < timedelta(hours=_conf('MARGEN_CANCELACION_H')):
        raise ValidationError(
            f'Solo puedes cancelar online hasta {_conf("MARGEN_CANCELACION_H")} horas antes. Llama a la clínica.')
    cita.estado = Cita.Estado.CANCELADA
    cita.save(update_fields=['estado', 'actualizada_en'])
    return cita


def marcar(cita, usuario, estado, notas=None, ahora=None):
    """El profesional (o recepción) marca la cita como atendida o no presentada."""
    if usuario.es_paciente or not puede_gestionar(usuario, cita):
        raise PermissionDenied
    if estado not in (Cita.Estado.ATENDIDA, Cita.Estado.NO_PRESENTADA, Cita.Estado.CONFIRMADA,
                      Cita.Estado.PENDIENTE):
        raise ValidationError('Estado no válido.')
    if cita.estado == Cita.Estado.CANCELADA:
        raise ValidationError('La cita está cancelada.')
    ahora = ahora or timezone.now()
    if estado in (Cita.Estado.ATENDIDA, Cita.Estado.NO_PRESENTADA) and cita.inicio > ahora:
        raise ValidationError('No se puede marcar una cita que aún no ha empezado.')
    cita.estado = estado
    if notas is not None:
        cita.notas = notas
    cita.save(update_fields=['estado', 'notas', 'actualizada_en'])
    return cita


def estadisticas(desde, hasta):
    """Ocupación y no presentados por profesional entre dos fechas (inclusive)."""
    filas = []
    for prof in Profesional.objects.filter(activo=True).select_related('usuario'):
        minutos_disponibles = 0
        dia = desde
        while dia <= hasta:
            for franja in prof.horarios.filter(dia_semana=dia.weekday()):
                ini, fin = _aware(dia, franja.hora_inicio), _aware(dia, franja.hora_fin)
                bloqueado = sum(
                    (min(b.fin, fin) - max(b.inicio, ini)).total_seconds() / 60
                    for b in prof.bloqueos.filter(inicio__lt=fin, fin__gt=ini))
                minutos_disponibles += (fin - ini).total_seconds() / 60 - bloqueado
            dia += timedelta(days=1)
        citas = prof.citas.activas().filter(inicio__date__gte=desde, inicio__date__lte=hasta)
        minutos_ocupados = sum((c.fin - c.inicio).total_seconds() / 60 for c in citas)
        cerradas = citas.filter(estado__in=[Cita.Estado.ATENDIDA, Cita.Estado.NO_PRESENTADA])
        no_pres = cerradas.filter(estado=Cita.Estado.NO_PRESENTADA).count()
        filas.append({
            'profesional': prof,
            'citas': citas.count(),
            'ocupacion': round(100 * minutos_ocupados / minutos_disponibles) if minutos_disponibles else 0,
            'no_presentados': no_pres,
            'tasa_no_presentados': round(100 * no_pres / cerradas.count()) if cerradas.count() else 0,
        })
    return filas
