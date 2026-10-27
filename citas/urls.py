from django.urls import path

from . import api, views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('entrar/', views.inicio_rol, name='inicio_rol'),
    path('reservar/', views.reservar, name='reservar'),

    # API REST (la usa React)
    path('api/servicios/', api.ServicioList.as_view(), name='api_servicios'),
    path('api/profesionales/', api.ProfesionalList.as_view(), name='api_profesionales'),
    path('api/huecos/', api.huecos, name='api_huecos'),
    path('api/yo/', api.yo, name='api_yo'),
    path('api/citas/', api.CitaListCreate.as_view(), name='api_citas'),
    path('api/citas/<int:pk>/cancelar/', api.cancelar, name='api_cancelar'),
]

urlpatterns += [
    path('agenda/', views.agenda, name='agenda'),
    path('recepcion/', views.recepcion, name='recepcion'),
    path('recepcion/nueva-cita/', views.nueva_cita, name='nueva_cita'),
    path('recepcion/bloqueo/', views.nuevo_bloqueo, name='nuevo_bloqueo'),
    path('panel/', views.panel, name='panel'),
    path('citas/<int:pk>/marcar/', views.marcar_cita, name='marcar_cita'),
    path('citas/<int:pk>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
]
