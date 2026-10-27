from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'ClinicaCitas · Administración'
admin.site.site_title = 'ClinicaCitas'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/', include('django.contrib.auth.urls')),
    path('', include('citas.urls')),
]
