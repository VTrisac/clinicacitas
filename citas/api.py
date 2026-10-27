"""API REST que consume la aplicación React de reservas (/reservar/).

Público: servicios, profesionales y huecos libres.
Paciente autenticado (sesión de Django + CSRF): sus citas, reservar y cancelar.
"""
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as ApiValidationError
from rest_framework.response import Response

from . import services
from .models import Cita, Profesional, Servicio
from .serializers import CitaSerializer, ProfesionalSerializer, ReservaSerializer, ServicioSerializer


class EsPaciente(permissions.BasePermission):
    message = 'Inicia sesión con una cuenta de paciente para reservar.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.es_paciente and hasattr(request.user, 'paciente')


class ServicioList(generics.ListAPIView):
    queryset = Servicio.objects.filter(activo=True)
    serializer_class = ServicioSerializer
    pagination_class = None


class ProfesionalList(generics.ListAPIView):
    serializer_class = ProfesionalSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Profesional.objects.filter(activo=True).select_related('usuario').prefetch_related('servicios')
        if servicio := self.request.query_params.get('servicio'):
            qs = qs.filter(servicios=servicio)
        return qs


@api_view(['GET'])
def huecos(request):
    """GET /api/huecos/?profesional=1&servicio=2&desde=2026-11-02&dias=7

    Devuelve {"dias": [{"fecha": "2026-11-02", "huecos": ["2026-11-02T09:00:00+01:00", ...]}, ...]}
    """
    profesional = get_object_or_404(Profesional, pk=request.query_params.get('profesional'), activo=True)
    servicio = get_object_or_404(Servicio, pk=request.query_params.get('servicio'), activo=True)
    try:
        desde = date.fromisoformat(request.query_params.get('desde', ''))
    except ValueError:
        desde = timezone.localdate()
    dias = min(max(int(request.query_params.get('dias', 7) or 7), 1), 14)
    hoy = timezone.localdate()
    ultimo = hoy + timedelta(days=settings.CITAS['DIAS_VISIBLES'])

    resultado = []
    for i in range(dias):
        fecha = desde + timedelta(days=i)
        libres = services.huecos_libres(profesional, servicio, fecha) if hoy <= fecha <= ultimo else []
        resultado.append({'fecha': fecha.isoformat(),
                          'huecos': [timezone.localtime(h).isoformat() for h in libres]})
    return Response({'dias': resultado, 'ultimo_dia': ultimo.isoformat()})


@api_view(['GET'])
def yo(request):
    """Quién está conectado, para que React sepa si puede reservar."""
    u = request.user
    if not u.is_authenticated:
        return Response({'autenticado': False})
    return Response({'autenticado': True, 'nombre': u.get_full_name() or u.username, 'rol': u.rol,
                     'puede_reservar': u.es_paciente and hasattr(u, 'paciente')})


class CitaListCreate(generics.ListCreateAPIView):
    permission_classes = [EsPaciente]
    serializer_class = CitaSerializer
    pagination_class = None

    def get_queryset(self):
        return (Cita.objects.filter(paciente=self.request.user.paciente)
                .select_related('profesional__usuario', 'servicio').order_by('-inicio'))

    def create(self, request, *args, **kwargs):
        datos = ReservaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        try:
            cita = services.reservar(paciente=request.user.paciente, creada_por=request.user,
                                     **datos.validated_data)
        except ValidationError as e:
            raise ApiValidationError({'detail': e.messages[0]})
        return Response(CitaSerializer(cita).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([EsPaciente])
def cancelar(request, pk):
    cita = get_object_or_404(Cita, pk=pk, paciente=request.user.paciente)
    try:
        services.cancelar(cita, request.user)
    except ValidationError as e:
        raise ApiValidationError({'detail': e.messages[0]})
    return Response(CitaSerializer(cita).data)
