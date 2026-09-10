from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production-123456789'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'store',
    'accounts',
    'orders',
    'crispy_forms',
    'crispy_bootstrap5',
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

ROOT_URLCONF = 'helmet_store.urls'

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
                'store.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'helmet_store.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_REDIRECT_URL = 'store:home'
LOGOUT_REDIRECT_URL = 'store:home'
LOGIN_URL = 'accounts:login'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ========== PAYMENT GATEWAY SETTINGS (ADD THIS TO THE BOTTOM) ==========

# eSewa (Test/Live Keys)
ESEWA_MERCHANT_CODE = "EPAYTEST"
ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"  
ESEWA_SUCCESS_URL = "http://127.0.0.1:8000/orders/esewa-success/"
ESEWA_FAILURE_URL = "http://127.0.0.1:8000/orders/esewa-failure/"

# Khalti (Test/Live Keys)
# !!! IMPORTANT: Replace "test_secret_key_123456789" with your actual test key from the Khalti dashboard !!!
KHALTI_SECRET_KEY = "TEST:O7QxjFcdueNzAh9aBOsD"  
KHALTI_VERIFY_URL = "https://khalti.com/api/v2/payment/verify/"
KHALTI_INITIATE_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
KHALTI_RETURN_URL = "http://127.0.0.1:8000/orders/khalti-verify/"
KHALTI_WEBSITE_URL = "http://127.0.0.1:8000"  # Your site's domain