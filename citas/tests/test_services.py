from datetime import datetime, time, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from citas import services
from citas.models import Bloqueo, Cita, Horario, Usuario

from .factories import crear_paciente, crear_profesional, crear_servicio, crear_usuario, proximo


def local(fecha, h, m=0):
    return timezone.make_aware(datetime.combine(fecha, time(h, m)))


class HuecosTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=45)
        self.prof = crear_profesional(servicios=[self.servicio])   # lunes 9:00-13:00
        self.lunes = proximo(0)

    def test_huecos_en_pasos_de_15_minutos_que_caben_en_la_franja(self):
        huecos = services.huecos_libres(self.prof, self.servicio, self.lunes)
        self.assertEqual(huecos[0], local(self.lunes, 9))
        self.assertEqual(huecos[1], local(self.lunes, 9, 15))
        self.assertEqual(huecos[-1], local(self.lunes, 12, 15))   # 12:15 + 45 min = 13:00
        self.assertEqual(len(huecos), 14)

    def test_sin_horario_ese_dia_no_hay_huecos(self):
        self.assertEqual(services.huecos_libres(self.prof, self.servicio, proximo(1)), [])

    def test_servicio_que_el_profesional_no_ofrece(self):
        otro = crear_servicio('Masaje', 30)
        self.assertEqual(services.huecos_libres(self.prof, otro, self.lunes), [])

    def test_una_cita_quita_los_huecos_que_se_solapan(self):
        paciente = crear_paciente()
        services.reservar(paciente=paciente, profesional=self.prof, servicio=self.servicio,
                          inicio=local(self.lunes, 10), creada_por=paciente.usuario)
        huecos = services.huecos_libres(self.prof, self.servicio, self.lunes)
        # 9:30 acabaría a las 10:15 y la cita ocupa 10:00-10:45
        self.assertIn(local(self.lunes, 9, 15), huecos)
        self.assertNotIn(local(self.lunes, 9, 30), huecos)
        self.assertNotIn(local(self.lunes, 10, 30), huecos)
        self.assertIn(local(self.lunes, 10, 45), huecos)

    def test_una_cita_cancelada_libera_el_hueco(self):
        paciente = crear_paciente()
        cita = services.reservar(paciente=paciente, profesional=self.prof, servicio=self.servicio,
                                 inicio=local(self.lunes, 10), creada_por=paciente.usuario)
        cita.estado = Cita.Estado.CANCELADA
        cita.save()
        self.assertIn(local(self.lunes, 10), services.huecos_libres(self.prof, self.servicio, self.lunes))

    def test_bloqueo_quita_huecos(self):
        Bloqueo.objects.create(profesional=self.prof, inicio=local(self.lunes, 9),
                               fin=local(self.lunes, 11), motivo='Formación')
        huecos = services.huecos_libres(self.prof, self.servicio, self.lunes)
        self.assertEqual(huecos[0], local(self.lunes, 11))

    def test_dos_franjas_el_mismo_dia(self):
        Horario.objects.create(profesional=self.prof, dia_semana=0, hora_inicio=time(16), hora_fin=time(17))
        huecos = services.huecos_libres(self.prof, self.servicio, self.lunes)
        self.assertIn(local(self.lunes, 16), huecos)
        self.assertNotIn(local(self.lunes, 16, 30), huecos)   # no cabe antes de las 17:00

    def test_margen_minimo_de_antelacion(self):
        ahora = local(self.lunes, 9, 50)
        huecos = services.huecos_libres(self.prof, self.servicio, self.lunes, ahora=ahora)
        self.assertEqual(huecos[0], local(self.lunes, 11))   # 9:50 + 60 min -> primer paso 11:00


class ReservarTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=30)
        self.prof = crear_profesional(servicios=[self.servicio])
        self.paciente = crear_paciente()
        self.lunes = proximo(0)

    def reservar(self, h, m=0, paciente=None):
        paciente = paciente or self.paciente
        return services.reservar(paciente=paciente, profesional=self.prof, servicio=self.servicio,
                                 inicio=local(self.lunes, h, m), creada_por=paciente.usuario)

    def test_reserva_calcula_el_fin(self):
        cita = self.reservar(9)
        self.assertEqual(cita.fin - cita.inicio, timedelta(minutes=30))
        self.assertEqual(cita.estado, Cita.Estado.CONFIRMADA)

    def test_no_se_puede_reservar_un_hueco_ocupado(self):
        self.reservar(9)
        with self.assertRaises(ValidationError):
            self.reservar(9, 15, paciente=crear_paciente('otro'))

    def test_no_se_puede_reservar_fuera_del_horario(self):
        with self.assertRaises(ValidationError):
            self.reservar(15)

    def test_no_se_puede_reservar_una_hora_no_alineada(self):
        with self.assertRaises(ValidationError):
            self.reservar(9, 7)

    def test_la_validacion_del_modelo_impide_solapes(self):
        self.reservar(9)
        cita = Cita(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                    inicio=local(self.lunes, 9, 15), fin=local(self.lunes, 9, 45))
        with self.assertRaises(ValidationError):
            cita.full_clean()


class CancelarYMarcarTests(TestCase):
    def setUp(self):
        self.servicio = crear_servicio(duracion=30)
        self.prof = crear_profesional(servicios=[self.servicio])
        self.paciente = crear_paciente()
        self.lunes = proximo(0)
        self.cita = services.reservar(paciente=self.paciente, profesional=self.prof, servicio=self.servicio,
                                      inicio=local(self.lunes, 10), creada_por=self.paciente.usuario)

    def test_paciente_cancela_su_cita_con_antelacion(self):
        services.cancelar(self.cita, self.paciente.usuario, ahora=local(self.lunes, 10) - timedelta(days=2))
        self.assertEqual(self.cita.estado, Cita.Estado.CANCELADA)

    def test_paciente_no_cancela_online_a_ultima_hora(self):
        with self.assertRaises(ValidationError):
            services.cancelar(self.cita, self.paciente.usuario, ahora=local(self.lunes, 8))

    def test_recepcion_cancela_a_ultima_hora(self):
        recepcion = crear_usuario('recepcion', Usuario.Rol.RECEPCION)
        services.cancelar(self.cita, recepcion, ahora=local(self.lunes, 9, 55))
        self.assertEqual(self.cita.estado, Cita.Estado.CANCELADA)

    def test_otro_paciente_no_puede_cancelar(self):
        with self.assertRaises(PermissionDenied):
            services.cancelar(self.cita, crear_paciente('intruso').usuario)

    def test_profesional_marca_atendida_despues_de_empezar(self):
        services.marcar(self.cita, self.prof.usuario, Cita.Estado.ATENDIDA, notas='Bien',
                        ahora=local(self.lunes, 10, 40))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.Estado.ATENDIDA)
        self.assertEqual(self.cita.notas, 'Bien')

    def test_no_se_marca_antes_de_empezar(self):
        with self.assertRaises(ValidationError):
            services.marcar(self.cita, self.prof.usuario, Cita.Estado.NO_PRESENTADA, ahora=local(self.lunes, 9))

    def test_otro_profesional_no_puede_marcar(self):
        otro = crear_profesional('luis')
        with self.assertRaises(PermissionDenied):
            services.marcar(self.cita, otro.usuario, Cita.Estado.ATENDIDA, ahora=local(self.lunes, 11))

    def test_estadisticas(self):
        services.marcar(self.cita, self.prof.usuario, Cita.Estado.NO_PRESENTADA, ahora=local(self.lunes, 11))
        fila = services.estadisticas(self.lunes, self.lunes)[0]
        self.assertEqual(fila['citas'], 1)
        self.assertEqual(fila['ocupacion'], round(100 * 30 / 240))
        self.assertEqual(fila['tasa_no_presentados'], 100)
