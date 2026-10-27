from django.urls import path

from . import api

urlpatterns = [
    # API REST (la usa React)
    path('api/servicios/', api.ServicioList.as_view(), name='api_servicios'),
    path('api/profesionales/', api.ProfesionalList.as_view(), name='api_profesionales'),
    path('api/huecos/', api.huecos, name='api_huecos'),
    path('api/yo/', api.yo, name='api_yo'),
    path('api/citas/', api.CitaListCreate.as_view(), name='api_citas'),
    path('api/citas/<int:pk>/cancelar/', api.cancelar, name='api_cancelar'),
]
