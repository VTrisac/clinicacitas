from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Bloqueo, Paciente, Profesional, Servicio, Usuario


class RegistroPacienteForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellidos', max_length=150)
    email = forms.EmailField(label='Email')
    telefono = forms.RegexField(label='Teléfono', regex=r'^\+?\d{9,15}$',
                                error_messages={'invalid': 'Escribe un teléfono válido (solo números).'})

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Usuario.Rol.PACIENTE
        usuario.save()
        Paciente.objects.create(usuario=usuario, telefono=self.cleaned_data['telefono'])
        return usuario


class CitaRecepcionForm(forms.Form):
    paciente = forms.ModelChoiceField(queryset=Paciente.objects.select_related('usuario'))
    servicio = forms.ModelChoiceField(queryset=Servicio.objects.filter(activo=True))
    profesional = forms.ModelChoiceField(queryset=Profesional.objects.filter(activo=True).select_related('usuario'))
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def clean(self):
        datos = super().clean()
        prof, serv = datos.get('profesional'), datos.get('servicio')
        if prof and serv and not prof.servicios.filter(pk=serv.pk).exists():
            raise forms.ValidationError(f'{prof} no ofrece {serv.nombre}.')
        return datos


class BloqueoForm(forms.ModelForm):
    class Meta:
        model = Bloqueo
        fields = ['profesional', 'inicio', 'fin', 'motivo']
        widgets = {
            'inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
