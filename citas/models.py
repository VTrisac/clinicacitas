"""Modelo de datos de ClinicaCitas.

Usuario (con rol) · Paciente y Profesional (perfiles 1:1) · Servicio · Horario · Bloqueo · Cita.
La regla principal (un profesional no tiene dos citas activas solapadas) se valida en
`Cita.clean()` y, para las reservas concurrentes, en `services.reservar()` dentro de una transacción.
"""
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        PACIENTE = 'paciente', 'Paciente'
        PROFESIONAL = 'profesional', 'Profesional'
        RECEPCION = 'recepcion', 'Recepción'
        ADMIN = 'admin', 'Administración'

    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.PACIENTE)

    @property
    def es_paciente(self):
        return self.rol == self.Rol.PACIENTE

    @property
    def es_profesional(self):
        return self.rol == self.Rol.PROFESIONAL

    @property
    def es_personal(self):
        """Recepción y administración gestionan la agenda de todos."""
        return self.rol in (self.Rol.RECEPCION, self.Rol.ADMIN) or self.is_superuser

    def __str__(self):
        return self.get_full_name() or self.username


class Paciente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='paciente')
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['usuario__last_name', 'usuario__first_name']

    def __str__(self):
        return str(self.usuario)


class Servicio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    duracion_min = models.PositiveSmallIntegerField('duración (min)')
    precio = models.DecimalField(max_digits=7, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(condition=Q(duracion_min__gte=5), name='servicio_duracion_minima'),
            models.CheckConstraint(condition=Q(precio__gte=0), name='servicio_precio_positivo'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.duracion_min} min)'


class Profesional(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='profesional')
    especialidad = models.CharField(max_length=80)
    color = models.CharField(max_length=7, default='#2f7d6d', help_text='Color en la agenda (#rrggbb)')
    servicios = models.ManyToManyField(Servicio, related_name='profesionales')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['usuario__first_name']
        verbose_name_plural = 'profesionales'

    def __str__(self):
        return str(self.usuario)


class Horario(models.Model):
    """Franja de trabajo semanal. Un profesional puede tener varias el mismo día (mañana y tarde)."""
    class Dia(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.PositiveSmallIntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ['profesional', 'dia_semana', 'hora_inicio']
        constraints = [
            models.CheckConstraint(condition=Q(hora_inicio__lt=models.F('hora_fin')),
                                   name='horario_inicio_antes_fin'),
        ]

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser anterior a la de fin.')
        if self.profesional_id and self.hora_inicio and self.hora_fin:
            solapa = Horario.objects.filter(
                profesional_id=self.profesional_id, dia_semana=self.dia_semana,
                hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio,
            ).exclude(pk=self.pk)
            if solapa.exists():
                raise ValidationError('Esta franja se solapa con otra del mismo día.')

    def __str__(self):
        return f'{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'


class Bloqueo(models.Model):
    """Periodo en el que un profesional no atiende (vacaciones, formación, festivo)."""
    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='bloqueos')
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    motivo = models.CharField(max_length=100)

    class Meta:
        ordering = ['inicio']
        constraints = [
            models.CheckConstraint(condition=Q(inicio__lt=models.F('fin')), name='bloqueo_inicio_antes_fin'),
        ]

    def clean(self):
        if self.inicio and self.fin and self.inicio >= self.fin:
            raise ValidationError('El inicio del bloqueo debe ser anterior al fin.')

    def __str__(self):
        return f'{self.profesional}: {self.motivo}'


class CitaQuerySet(models.QuerySet):
    def activas(self):
        """Citas que ocupan hueco en la agenda (las canceladas lo liberan)."""
        return self.exclude(estado=Cita.Estado.CANCELADA)

    def solapadas(self, profesional, inicio, fin):
        return self.activas().filter(profesional=profesional, inicio__lt=fin, fin__gt=inicio)


class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de confirmar'
        CONFIRMADA = 'confirmada', 'Confirmada'
        ATENDIDA = 'atendida', 'Atendida'
        NO_PRESENTADA = 'no_presentada', 'No presentada'
        CANCELADA = 'cancelada', 'Cancelada'

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name='citas')
    profesional = models.ForeignKey(Profesional, on_delete=models.PROTECT, related_name='citas')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='citas')
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=14, choices=Estado.choices, default=Estado.CONFIRMADA)
    notas = models.TextField('notas del profesional', blank=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='+')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    objects = CitaQuerySet.as_manager()

    class Meta:
        ordering = ['inicio']
        indexes = [models.Index(fields=['profesional', 'inicio'])]
        constraints = [
            models.CheckConstraint(condition=Q(inicio__lt=models.F('fin')), name='cita_inicio_antes_fin'),
        ]

    @property
    def activa(self):
        return self.estado != self.Estado.CANCELADA

    def clean(self):
        if self.inicio and self.fin and self.inicio >= self.fin:
            raise ValidationError('La cita debe terminar después de empezar.')
        if self.activa and self.profesional_id and self.inicio and self.fin:
            if Cita.objects.solapadas(self.profesional_id, self.inicio, self.fin).exclude(pk=self.pk).exists():
                raise ValidationError('El profesional ya tiene una cita en ese horario.')

    def __str__(self):
        return f'{self.inicio:%d/%m/%Y %H:%M} · {self.paciente} con {self.profesional}'
