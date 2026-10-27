from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Bloqueo, Cita, Horario, Paciente, Profesional, Servicio, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('Rol en la clínica', {'fields': ('rol',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Rol en la clínica', {'fields': ('rol',)}),)


class HorarioInline(admin.TabularInline):
    model = Horario
    extra = 1


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'especialidad', 'activo')
    list_filter = ('activo',)
    filter_horizontal = ('servicios',)
    inlines = [HorarioInline]


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'telefono', 'fecha_nacimiento')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'usuario__email', 'telefono')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'duracion_min', 'precio', 'activo')
    list_editable = ('activo',)


@admin.register(Bloqueo)
class BloqueoAdmin(admin.ModelAdmin):
    list_display = ('profesional', 'inicio', 'fin', 'motivo')
    list_filter = ('profesional',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('inicio', 'paciente', 'profesional', 'servicio', 'estado')
    list_filter = ('estado', 'profesional', 'servicio')
    date_hierarchy = 'inicio'
    search_fields = ('paciente__usuario__first_name', 'paciente__usuario__last_name')
