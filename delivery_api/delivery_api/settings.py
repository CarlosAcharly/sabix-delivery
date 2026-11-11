# delivery_api/settings.py
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',

    # Local apps
    'users',   
    'common',   
    'django_filters',  
    'products',  
    'orders',
    'notifications',
    'chat',
    'channels',
    'storages', # ✅ AWS S3
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
            "symmetric_encryption_keys": [SECRET_KEY],
            "capacity": 1000,
            "expiry": 60,
            "channel_capacity": {
                "http.request": 200,
                "websocket.send": 100,
                "websocket.receive": 100,
            },
        },
    },
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ✅ Debe ir primero
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'delivery_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'delivery_api.wsgi.application'
ASGI_APPLICATION = 'delivery_api.asgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'delivery_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# =============================================
# AWS S3 CONFIGURATION (Para imágenes de productos)
# =============================================

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-2')

# Dominio personalizado para las imágenes
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

# Opciones recomendadas para archivos públicos (sin autenticación extra en la URL)
AWS_DEFAULT_ACL = None  
AWS_QUERYSTRING_AUTH = False 

# Media files (Imágenes) - Apuntan a AWS S3
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Static files (CSS, JavaScript, Images) - Se quedan en el servidor
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configuración de Django 4.2+ para el almacenamiento
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
            "default_acl": None,
            "querystring_auth": False,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================
# CORS Configuration - CORREGIDA PARA WEBSOCKETS
# =============================================

# ✅ Permitir todos los orígenes para pruebas (luego limitar en producción)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Headers adicionales para CORS (incluyendo WebSockets)
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-app-type',
    'upgrade',         
    'connection',      
    'sec-websocket-key',
    'sec-websocket-version',
]

CORS_EXPOSE_HEADERS = [
    'content-disposition',
    'content-length',
    'content-type',
]

# Métodos permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# =============================================
# Django REST Framework Configuration
# =============================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# =============================================
# FIREBASE CONFIGURATION
# =============================================

# Configuración de Firebase
FIREBASE_CREDENTIALS_FILE = os.path.join(
    BASE_DIR, 
    'firebase', 
    'sabixdelivery-firebase-adminsdk-fbsvc-3572815d44.json'
)

# Intentar inicializar Firebase
try:
    import firebase_admin
    from firebase_admin import credentials
    
    if os.path.exists(FIREBASE_CREDENTIALS_FILE):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
        firebase_app = firebase_admin.initialize_app(cred)
        print("✅ Firebase inicializado correctamente")
    else:
        print(f"⚠️ Archivo de credenciales Firebase no encontrado")
        print(f"📌 Ruta esperada: {FIREBASE_CREDENTIALS_FILE}")
except Exception as e:
    print(f"❌ Error inicializando Firebase: {e}")