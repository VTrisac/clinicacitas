from datetime import datetime, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from citas import services
from citas.models import Bloqueo, Cita, Paciente, Usuario

from .factories import crear_paciente, crear_profesional, crear_servicio, crear_usuario, proximo


def local(fecha, h, m=0):
    return timezone.make_aware(datetime.combine(fecha, time(h, m)))


class RegistroYAccesoTests(TestCase):
    def test_registro_crea_paciente_y_entra(self):
        r = self.client.post(reverse('registro'), {
            'username': 'nuevo', 'first_name': 'Nuevo', 'last_name': 'Paciente', 'email': 'nuevo@test.com',
            'telefono': '600111222', 'password1': 'Una-clave-larga-9', 'password2': 'Una-clave-larga-9'})
        self.assertRedirects(r, reverse('reservar'))
        u = Usuario.objects.get(username='nuevo')
        self.assertEqual(u.rol, Usuario.Rol.PACIENTE)
        self.assertTrue(Paciente.objects.filter(usuario=u).exists())

    def test_cada_rol_va_a_su_pantalla(self):
        casos = [(crear_paciente().usuario, 'reservar'),
                 (crear_profesional('pro').usuario, 'agenda'),
                 (crear_usuario('rec', Usuario.Rol.RECEPCION), 'recepcion')]
        for usuario, destino in casos:
            self.client.force_login(usuario)
            self.assertRedirects(self.client.get(reverse('inicio_rol')), reverse(destino), fetch_redirect_response=False)

    def test_paciente_no_entra_en_recepcion_ni_agenda(self):
        self.client.force_login(crear_paciente().usuario)
        for nombre in ('recepcion', 'agenda', 'panel'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)

    def test_paginas_publicas(self):
        crear_profesional(servicios=[crear_servicio()])
        self.assertContains(self.client.get(reverse('inicio')), 'Fisioterapia')
        r = self.client.get(reverse('reservar'))
        self.assertContains(r, 'reserva-root')
        self.assertIn('csrftoken', r.cookies)


class PersonalTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=30)
        self.prof = crear_profesional(servicios=[self.servicio])
        self.paciente = crear_paciente()
        self.recepcion = crear_usuario('rec', Usuario.Rol.RECEPCION)
        self.lunes = proximo(0)

    def test_recepcion_ve_huecos_y_da_cita(self):
        self.client.force_login(self.recepcion)
        datos = {'paciente': self.paciente.pk, 'servicio': self.servicio.pk, 'profesional': self.prof.pk,
                 'fecha': self.lunes.isoformat()}
        r = self.client.get(reverse('nueva_cita'), datos)
        self.assertContains(r, '09:00')
        r = self.client.post(reverse('nueva_cita'), {**datos, 'inicio': f'{self.lunes.isoformat()}T09:30'})
        self.assertEqual(r.status_code, 302)
        cita = Cita.objects.get()
        self.assertEqual(cita.inicio, local(self.lunes, 9, 30))
        self.assertEqual(cita.creada_por, self.recepcion)

    def test_recepcion_ve_la_agenda_del_dia(self):
        services.reservar(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                          inicio=local(self.lunes, 10), creada_por=self.recepcion)
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse('recepcion'), {'fecha': self.lunes.isoformat()})
        self.assertContains(r, str(self.paciente))

    def test_bloqueo_avisa_de_citas_afectadas(self):
        services.reservar(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                          inicio=local(self.lunes, 10), creada_por=self.recepcion)
        self.client.force_login(self.recepcion)
        r = self.client.post(reverse('nuevo_bloqueo'), {
            'profesional': self.prof.pk, 'inicio': f'{self.lunes.isoformat()}T09:00',
            'fin': f'{self.lunes.isoformat()}T12:00', 'motivo': 'Formación'}, follow=True)
        self.assertEqual(Bloqueo.objects.count(), 1)
        self.assertContains(r, '1 cita(s) dentro del bloqueo')

    def test_profesional_ve_su_agenda(self):
        services.reservar(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                          inicio=local(self.lunes, 10), creada_por=self.recepcion)
        self.client.force_login(self.prof.usuario)
        r = self.client.get(reverse('agenda'), {'fecha': self.lunes.isoformat()})
        self.assertContains(r, '10:00')

    def test_volver_no_permite_redirigir_fuera(self):
        cita = services.reservar(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                                 inicio=local(self.lunes, 10), creada_por=self.recepcion)
        self.client.force_login(self.recepcion)
        r = self.client.post(reverse('cancelar_cita', args=[cita.pk]), {'volver': 'https://malicioso.example/'})
        self.assertEqual(r.url, reverse('inicio_rol'))

    def test_panel(self):
        admin = crear_usuario('jefa', Usuario.Rol.ADMIN)
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('panel')), str(self.prof))
