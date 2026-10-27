from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from citas import services
from citas.models import Cita

from .factories import crear_paciente, crear_profesional, crear_servicio, proximo


def local(fecha, h, m=0):
    return timezone.make_aware(datetime.combine(fecha, time(h, m)))


class ApiPublicaTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=60)
        self.prof = crear_profesional(servicios=[self.servicio])
        self.client = APIClient()

    def test_servicios_y_profesionales(self):
        self.assertEqual(self.client.get('/api/servicios/').json()[0]['nombre'], 'Fisioterapia')
        datos = self.client.get(f'/api/profesionales/?servicio={self.servicio.pk}').json()
        self.assertEqual(datos[0]['id'], self.prof.pk)
        otro = crear_servicio('Masaje', 30)
        self.assertEqual(self.client.get(f'/api/profesionales/?servicio={otro.pk}').json(), [])

    def test_huecos_de_una_semana(self):
        lunes = proximo(0)
        r = self.client.get('/api/huecos/', {'profesional': self.prof.pk, 'servicio': self.servicio.pk,
                                             'desde': lunes.isoformat(), 'dias': 7})
        dias = r.json()['dias']
        self.assertEqual(len(dias), 7)
        self.assertEqual(dias[0]['fecha'], lunes.isoformat())
        self.assertEqual(dias[0]['huecos'][0][:16], f'{lunes.isoformat()}T09:00')
        self.assertEqual(dias[1]['huecos'], [])   # el martes no trabaja

    def test_huecos_del_pasado_vacios(self):
        ayer = timezone.localdate() - timedelta(days=1)
        r = self.client.get('/api/huecos/', {'profesional': self.prof.pk, 'servicio': self.servicio.pk,
                                             'desde': ayer.isoformat(), 'dias': 1})
        self.assertEqual(r.json()['dias'][0]['huecos'], [])

    def test_anonimo_no_puede_reservar(self):
        r = self.client.post('/api/citas/', {'profesional': self.prof.pk, 'servicio': self.servicio.pk,
                                             'inicio': local(proximo(0), 9).isoformat()}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get('/api/yo/').json(), {'autenticado': False})


class ApiPacienteTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=30)
        self.prof = crear_profesional(servicios=[self.servicio])
        self.paciente = crear_paciente()
        self.client = APIClient(enforce_csrf_checks=False)
        self.client.force_login(self.paciente.usuario)
        self.lunes = proximo(0)

    def reservar(self, h, m=0):
        return self.client.post('/api/citas/', {'profesional': self.prof.pk, 'servicio': self.servicio.pk,
                                                'inicio': local(self.lunes, h, m).isoformat()}, format='json')

    def test_reservar_y_listar(self):
        r = self.reservar(9)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['estado'], 'confirmada')
        citas = self.client.get('/api/citas/').json()
        self.assertEqual(len(citas), 1)
        self.assertTrue(self.client.get('/api/yo/').json()['puede_reservar'])

    def test_hueco_ocupado_devuelve_400_con_mensaje(self):
        self.reservar(9)
        r = self.reservar(9)
        self.assertEqual(r.status_code, 400)
        self.assertIn('no está disponible', r.json()['detail'])

    def test_solo_ve_sus_citas(self):
        otro = crear_paciente('otro')
        services.reservar(paciente=otro, profesional=self.prof, servicio=self.servicio,
                          inicio=local(self.lunes, 10), creada_por=otro.usuario)
        self.assertEqual(self.client.get('/api/citas/').json(), [])

    def test_cancelar_propia(self):
        cita_id = self.reservar(9).json()['id']
        r = self.client.post(f'/api/citas/{cita_id}/cancelar/')
        self.assertEqual(r.json()['estado'], 'cancelada')

    def test_no_cancela_la_de_otro(self):
        otro = crear_paciente('otro')
        cita = services.reservar(paciente=otro, profesional=self.prof, servicio=self.servicio,
                                 inicio=local(self.lunes, 10), creada_por=otro.usuario)
        self.assertEqual(self.client.post(f'/api/citas/{cita.pk}/cancelar/').status_code, 404)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.Estado.CONFIRMADA)

    def test_el_post_exige_csrf_con_sesion(self):
        cliente = APIClient(enforce_csrf_checks=True)
        cliente.force_login(self.paciente.usuario)
        r = cliente.post('/api/citas/', {'profesional': self.prof.pk, 'servicio': self.servicio.pk,
                                         'inicio': local(self.lunes, 9).isoformat()}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_profesional_no_puede_reservar_por_api(self):
        self.client.force_login(self.prof.usuario)
        self.assertEqual(self.reservar(9).status_code, 403)
