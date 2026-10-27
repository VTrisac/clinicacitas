"""Vistas web (plantillas de Django): inicio, registro, agenda, recepción y panel."""
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from . import services
from .forms import BloqueoForm, CitaRecepcionForm, RegistroPacienteForm
from .models import Cita, Profesional, Servicio


def inicio(request):
    return render(request, 'citas/inicio.html', {
        'servicios': Servicio.objects.filter(activo=True),
        'profesionales': Profesional.objects.filter(activo=True).select_related('usuario'),
    })


def registro(request):
    form = RegistroPacienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, 'Cuenta creada. Ya puedes reservar tu cita.')
        return redirect('reservar')
    return render(request, 'registration/registro.html', {'form': form})


def inicio_rol(request):
    """Tras iniciar sesión, cada rol va a su pantalla."""
    u = request.user
    if not u.is_authenticated:
        return redirect('login')
    if u.es_profesional:
        return redirect('agenda')
    if u.es_personal:
        return redirect('recepcion')
    return redirect('reservar')


@ensure_csrf_cookie
def reservar(request):
    """Página que monta la aplicación React. La cookie CSRF permite a React hacer POST a la API."""
    return render(request, 'citas/reservar.html', {'login_url': f"{reverse('login')}?next={reverse('reservar')}"})


# ---------------------------------------------------------------------------
# Personal de la clínica: agenda del profesional, recepción y panel
# ---------------------------------------------------------------------------

def solo_profesional(vista):
    return login_required(user_passes_test(lambda u: u.es_profesional and hasattr(u, 'profesional'))(vista))


def solo_personal(vista):
    return login_required(user_passes_test(lambda u: u.es_personal)(vista))


def _fecha_param(request):
    try:
        return date.fromisoformat(request.GET.get('fecha', ''))
    except ValueError:
        return timezone.localdate()


def _volver(request, defecto='inicio_rol'):
    """Vuelve a la página desde la que se envió el formulario (solo URLs de esta web)."""
    destino = request.POST.get('volver', '')
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(destino)
    return redirect(defecto)


def _nav_fechas(fecha):
    return {'fecha': fecha, 'anterior': fecha - timedelta(days=1), 'siguiente': fecha + timedelta(days=1),
            'hoy': timezone.localdate()}


@solo_profesional
def agenda(request):
    """Agenda del día del profesional conectado."""
    fecha = _fecha_param(request)
    citas = (Cita.objects.filter(profesional=request.user.profesional, inicio__date=fecha)
             .select_related('paciente__usuario', 'servicio'))
    return render(request, 'citas/agenda.html', {**_nav_fechas(fecha), 'citas': citas, 'ahora': timezone.now()})


@login_required
@require_POST
def marcar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    try:
        services.marcar(cita, request.user, request.POST.get('estado'), notas=request.POST.get('notas'))
        messages.success(request, f'Cita de las {timezone.localtime(cita.inicio):%H:%M}: {cita.get_estado_display().lower()}.')
    except ValidationError as e:
        messages.error(request, e.messages[0])
    except PermissionDenied:
        messages.error(request, 'No puedes modificar esta cita.')
    return _volver(request)


@login_required
@require_POST
def cancelar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    try:
        services.cancelar(cita, request.user)
        messages.success(request, 'Cita cancelada.')
    except ValidationError as e:
        messages.error(request, e.messages[0])
    except PermissionDenied:
        messages.error(request, 'No puedes cancelar esta cita.')
    return _volver(request)


@solo_personal
def recepcion(request):
    """Agenda de todos los profesionales para un día, con alta de citas y bloqueos."""
    fecha = _fecha_param(request)
    columnas = []
    for prof in Profesional.objects.filter(activo=True).select_related('usuario'):
        columnas.append({
            'profesional': prof,
            'citas': prof.citas.filter(inicio__date=fecha).select_related('paciente__usuario', 'servicio'),
            'bloqueos': prof.bloqueos.filter(inicio__date__lte=fecha, fin__date__gte=fecha),
        })
    return render(request, 'citas/recepcion.html', {
        **_nav_fechas(fecha), 'columnas': columnas,
        'form': CitaRecepcionForm(initial={'fecha': fecha}), 'form_bloqueo': BloqueoForm(),
    })


@solo_personal
def nueva_cita(request):
    """Recepción da una cita por teléfono. Paso 1: datos; paso 2: elegir uno de los huecos libres."""
    form = CitaRecepcionForm(request.POST or request.GET or None)
    huecos = None
    if form.is_bound and form.is_valid():
        d = form.cleaned_data
        if request.method == 'POST' and request.POST.get('inicio'):
            try:
                inicio = timezone.make_aware(datetime.fromisoformat(request.POST['inicio']))
                cita = services.reservar(paciente=d['paciente'], profesional=d['profesional'],
                                         servicio=d['servicio'], inicio=inicio, creada_por=request.user)
                messages.success(request, f'Cita creada para {cita.paciente} el {timezone.localtime(cita.inicio):%d/%m a las %H:%M}.')
                return redirect(f"{reverse('recepcion')}?fecha={d['fecha'].isoformat()}")
            except (ValidationError, ValueError) as e:
                messages.error(request, getattr(e, 'messages', [str(e)])[0])
        huecos = [timezone.localtime(h) for h in services.huecos_libres(d['profesional'], d['servicio'], d['fecha'])]
    return render(request, 'citas/nueva_cita.html', {'form': form, 'huecos': huecos})


@solo_personal
@require_POST
def nuevo_bloqueo(request):
    form = BloqueoForm(request.POST)
    if form.is_valid():
        bloqueo = form.save()
        afectadas = Cita.objects.solapadas(bloqueo.profesional, bloqueo.inicio, bloqueo.fin).count()
        messages.success(request, f'Bloqueo creado para {bloqueo.profesional}.')
        if afectadas:
            messages.warning(request, f'Atención: hay {afectadas} cita(s) dentro del bloqueo. Avisa a los pacientes y cancélalas.')
    else:
        messages.error(request, ' '.join(e for errs in form.errors.values() for e in errs))
    return _volver(request, 'recepcion')


@solo_personal
def panel(request):
    """Estadísticas de los últimos 30 días."""
    hasta = timezone.localdate()
    desde = hasta - timedelta(days=29)
    filas = services.estadisticas(desde, hasta)
    proximas = Cita.objects.activas().filter(inicio__gte=timezone.now(), inicio__date__lte=hasta + timedelta(days=7))
    total = sum(f['citas'] for f in filas)
    no_pres = sum(f['no_presentados'] for f in filas)
    return render(request, 'citas/panel.html', {
        'filas': filas, 'desde': desde, 'hasta': hasta,
        'total_citas': total, 'total_no_presentados': no_pres,
        'ocupacion_media': round(sum(f['ocupacion'] for f in filas) / len(filas)) if filas else 0,
        'proximos_7_dias': proximas.count(),
    })
