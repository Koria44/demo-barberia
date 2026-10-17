"""
Django settings for demo_barber project.
Plataforma web de lujo para barberías (reservas, tienda, cuentas y dashboard).
Configuración adaptada para leer variables sensibles desde .env y soporte multi-entorno.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Clave secreta y modo depuración
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-demo-barber-default-dev-key-change-in-production'
)
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Modelo de Usuario personalizado
AUTH_USER_MODEL = 'cuentas.Usuario'

# Aplicaciones instaladas
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del proyecto Demo Barber
    'cuentas.apps.CuentasConfig',
    'sucursales.apps.SucursalesConfig',
    'barberos.apps.BarberosConfig',
    'catalogo.apps.CatalogoConfig',
    'reservas.apps.ReservasConfig',
    'tienda.apps.TiendaConfig',
    'contenido.apps.ContenidoConfig',
    'panel.apps.PanelConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'demo_barber.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'contenido.context_processors.site_context',
                'panel.context_processors.panel_scope_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'demo_barber.wsgi.application'

# Base de datos
# Por defecto SQLite para desarrollo local, preparado para PostgreSQL con variables en .env
DB_ENGINE = os.environ.get('DB_ENGINE', '')
if DB_ENGINE == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'demo_barber_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Validadores de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internacionalización y Localización para Chile
LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'es-cl')
TIME_ZONE = os.environ.get('TIME_ZONE', 'America/Santiago')
USE_I18N = True
USE_TZ = True

# Archivos estáticos y multimedia
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Redirecciones y autenticación
LOGIN_URL = 'cuentas:login'
LOGIN_REDIRECT_URL = 'cuentas:redirect_por_rol'
LOGOUT_REDIRECT_URL = 'sitio_publico:inicio'

# Correo electrónico (en desarrollo se imprime en la consola)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Demo Barber Club <contacto@demobarberclub.cl>')

# Clave primaria por defecto
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
