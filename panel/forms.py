"""
Formularios para el panel de administración (/panel/).
Validaciones estrictas en español, control de alcance por sucursal y manejo de entidades comerciales.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from barberos.models import Barbero
from catalogo.models import Servicio, CategoriaServicio, ServicioSucursal, ServicioBarbero
from sucursales.models import Sucursal
from panel.alcance import obtener_sucursales_permitidas

Usuario = get_user_model()


class BarberoForm(forms.ModelForm):
    """Formulario para creación y edición de perfiles de barbero desde el panel"""
    # Campos adicionales de la cuenta de usuario
    email = forms.EmailField(
        label='Correo Electrónico (Login)',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'})
    )
    first_name = forms.CharField(
        label='Nombre',
        required=True,
        widget=forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'})
    )
    last_name = forms.CharField(
        label='Apellido',
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'})
    )
    telefono = forms.CharField(
        label='Teléfono / WhatsApp',
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'placeholder': '+56 9 1234 5678'})
    )

    class Meta:
        model = Barbero
        fields = [
            'nombre_profesional', 'especialidad_principal', 'sucursales',
            'foto', 'bio', 'instagram', 'anios_experiencia', 'orden', 'activo'
        ]
        widgets = {
            'nombre_profesional': forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'especialidad_principal': forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'sucursales': forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1 text-xs text-ivory'}),
            'foto': forms.FileInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'instagram': forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'placeholder': 'usuario_sin_arroba'}),
            'anios_experiencia': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'min': 0}),
            'orden': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'min': 1}),
            'activo': forms.CheckboxInput(attrs={'class': 'rounded-none border-gold text-gold'}),
        }

    def __init__(self, *args, usuario_admin=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_admin = usuario_admin

        # Restringir las sucursales elegibles al alcance del usuario que gestiona
        if usuario_admin:
            permitidas = obtener_sucursales_permitidas(usuario_admin)
            self.fields['sucursales'].queryset = permitidas

        # Si estamos editando un barbero existente, poblar datos de su cuenta de usuario
        if self.instance and self.instance.pk and self.instance.usuario:
            self.fields['email'].initial = self.instance.usuario.email
            self.fields['first_name'].initial = self.instance.usuario.first_name
            self.fields['last_name'].initial = self.instance.usuario.last_name
            self.fields['telefono'].initial = self.instance.usuario.telefono

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        user_qs = Usuario.objects.filter(email=email)
        if self.instance and self.instance.pk and self.instance.usuario:
            user_qs = user_qs.exclude(pk=self.instance.usuario.pk)
        if user_qs.exists():
            raise ValidationError("Ya existe un usuario registrado con este correo electrónico.")
        return email

    def clean_sucursales(self):
        sucursales = self.cleaned_data.get('sucursales')
        if not sucursales:
            raise ValidationError("Debes asignar al menos una sucursal al barbero.")
        if self.usuario_admin and self.usuario_admin.es_admin_sucursal:
            permitidas = set(self.usuario_admin.sucursales_asignadas.values_list('id', flat=True))
            for s in sucursales:
                if s.id not in permitidas:
                    raise ValidationError(f"No tienes autorización para asignar la sede '{s.nombre}'.")
        return sucursales

    def save(self, commit=True):
        barbero = super().save(commit=False)
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data.get('last_name', '')
        telefono = self.cleaned_data.get('telefono', '')

        if not barbero.usuario_id:
            # Crear nueva cuenta de usuario con rol BARBERO
            usuario = Usuario.objects.create_user(
                email=email,
                password='Barbero2026!',
                first_name=first_name,
                last_name=last_name,
                telefono=telefono,
                rol=Usuario.Rol.BARBERO
            )
            barbero.usuario = usuario
        else:
            # Actualizar datos de usuario existente
            usuario = barbero.usuario
            usuario.email = email
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.telefono = telefono
            usuario.rol = Usuario.Rol.BARBERO
            usuario.save()

        if not barbero.slug:
            barbero.slug = slugify(barbero.nombre_profesional)

        if commit:
            barbero.save()
            self.save_m2m()

        return barbero


class ServicioForm(forms.ModelForm):
    """Formulario para creación y edición de servicios base (ADMIN_MAESTRO)"""
    class Meta:
        model = Servicio
        fields = [
            'nombre', 'categoria', 'descripcion', 'duracion_minutos', 'precio',
            'etiqueta', 'es_destacado', 'imagen', 'orden', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'categoria': forms.Select(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'min': 5, 'step': 5}),
            'precio': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'min': 0, 'step': 500}),
            'etiqueta': forms.TextInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'placeholder': 'Ej: Más solicitado, Signature'}),
            'es_destacado': forms.CheckboxInput(attrs={'class': 'rounded-none border-gold text-gold'}),
            'imagen': forms.FileInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none'}),
            'orden': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-2 text-ivory text-xs focus:border-gold focus:outline-none', 'min': 1}),
            'activo': forms.CheckboxInput(attrs={'class': 'rounded-none border-gold text-gold'}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio < 0:
            raise ValidationError("El precio no puede ser negativo.")
        return precio

    def clean_duracion_minutos(self):
        duracion = self.cleaned_data.get('duracion_minutos')
        if duracion is not None and duracion <= 0:
            raise ValidationError("La duración debe ser mayor a 0 minutos.")
        return duracion


class ServicioSucursalForm(forms.ModelForm):
    """Formulario para ajustar disponibilidad, precio y duración por sucursal"""
    class Meta:
        model = ServicioSucursal
        fields = ['disponible', 'precio_personalizado', 'duracion_personalizada']
        widgets = {
            'disponible': forms.CheckboxInput(attrs={'class': 'rounded-none border-gold text-gold'}),
            'precio_personalizado': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-1.5 text-ivory text-xs focus:border-gold focus:outline-none', 'placeholder': 'Dejar vacío para precio base'}),
            'duracion_personalizada': forms.NumberInput(attrs={'class': 'w-full bg-bg-dark border border-bg-border px-3 py-1.5 text-ivory text-xs focus:border-gold focus:outline-none', 'placeholder': 'Dejar vacío para duración base'}),
        }
