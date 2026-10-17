"""
Formularios de autenticación, registro y perfil de usuario para Demo Barber Club.
"""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.utils.translation import gettext_lazy as _
from cuentas.models import Usuario


class LoginForm(forms.Form):
    """Formulario de inicio de sesión con email y contraseña"""
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
            'placeholder': 'tu@correo.cl',
            'autocomplete': 'email',
            'required': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'required': True
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            self.user = authenticate(username=email, password=password)
            if not self.user:
                # Comprobar si existe el usuario para limitar intentos
                try:
                    user_obj = Usuario.objects.get(email__iexact=email)
                    user_obj.intentos_fallidos_login += 1
                    user_obj.save(update_fields=['intentos_fallidos_login'])
                except Usuario.DoesNotExist:
                    pass
                raise forms.ValidationError(
                    _('Correo electrónico o contraseña incorrectos. Por favor intenta nuevamente.')
                )
            if not self.user.is_active:
                raise forms.ValidationError(_('Esta cuenta se encuentra inactiva. Contacta al soporte.'))
        return cleaned_data


class RegistroForm(forms.ModelForm):
    """Formulario de registro para clientes con diseño minimalista"""
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
            'placeholder': 'Mínimo 6 caracteres',
            'autocomplete': 'new-password'
        })
    )
    confirmar_password = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
            'placeholder': 'Repite tu contraseña',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
                'placeholder': 'Ej. Carlos'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
                'placeholder': 'Ej. Muñoz'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
                'placeholder': 'carlos@ejemplo.cl'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold focus:ring-1 focus:ring-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim transition-colors',
                'placeholder': '+56 9 1234 5678'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError(_('Ya existe una cuenta registrada con este correo electrónico.'))
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirmar_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirmar_password', _('Las contraseñas no coinciden.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.rol = Usuario.Rol.CLIENTE
        user.username = user.email
        if commit:
            user.save()
        return user


class PerfilUsuarioForm(forms.ModelForm):
    """Formulario para que el cliente actualice sus datos en 'Mi Cuenta'"""
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'telefono', 'notas_cliente', 'foto_perfil']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold text-ivory px-4 py-2.5 text-sm rounded-none'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold text-ivory px-4 py-2.5 text-sm rounded-none'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold text-ivory px-4 py-2.5 text-sm rounded-none'
            }),
            'notas_cliente': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold text-ivory px-4 py-2.5 text-sm rounded-none',
                'placeholder': 'Tus preferencias habituales: ej. Low Fade, barba perfilada con navaja.'
            }),
        }


class RecuperarClaveForm(PasswordResetForm):
    """Formulario para solicitar restablecimiento de contraseña"""
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-bg-dark border border-bg-border focus:border-gold text-ivory px-4 py-3 text-sm rounded-none placeholder-ivory-dim',
            'placeholder': 'tu@correo.cl'
        })
    )
