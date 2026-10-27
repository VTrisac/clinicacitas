from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import Cita, Profesional, Servicio


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ['id', 'nombre', 'descripcion', 'duracion_min', 'precio']


class ProfesionalSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='usuario.get_full_name')
    servicios = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Profesional
        fields = ['id', 'nombre', 'especialidad', 'color', 'servicios']


class CitaSerializer(serializers.ModelSerializer):
    profesional_nombre = serializers.CharField(source='profesional.usuario.get_full_name', read_only=True)
    servicio_nombre = serializers.CharField(source='servicio.nombre', read_only=True)
    estado_texto = serializers.CharField(source='get_estado_display', read_only=True)
    cancelable = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = ['id', 'profesional', 'profesional_nombre', 'servicio', 'servicio_nombre',
                  'inicio', 'fin', 'estado', 'estado_texto', 'cancelable']
        read_only_fields = ['fin', 'estado']

    def get_cancelable(self, cita):
        margen = timedelta(hours=settings.CITAS['MARGEN_CANCELACION_H'])
        return cita.estado in (Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA) and \
            cita.inicio - timezone.now() >= margen


class ReservaSerializer(serializers.Serializer):
    """Datos que envía el paciente desde React para reservar."""
    profesional = serializers.PrimaryKeyRelatedField(queryset=Profesional.objects.filter(activo=True))
    servicio = serializers.PrimaryKeyRelatedField(queryset=Servicio.objects.filter(activo=True))
    inicio = serializers.DateTimeField()
