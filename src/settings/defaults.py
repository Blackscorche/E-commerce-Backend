from pathlib import Path
from datetime import timedelta
from decimal import Decimal
from decouple import config
from decimal import Decimal

BASE_DIR = Path(__file__).parents[1]

PROJECT_ENVIRONMENT = config("PROJECT_ENVIRONMENT", default="development")

SECRET_KEY = config("DJANGO_SECRET_KEY")

DEBUG = PROJECT_ENVIRONMENT == "development"

ALLOWED_HOSTS = (
    ["0.0.0.0", "localhost", "testserver"]
    if PROJECT_ENVIRONMENT == "development"
    else config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")])
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "taggit",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",  # Add this for JWT support
    "rest_framework_simplejwt.token_blacklist",  # For JWT blacklisting
    "django_filters",
    "dj_rest_auth",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "dj_rest_auth.registration",
    "src.apps.accounts",
    "src.apps.payments",
    "src.apps.newsletter",
    "src.apps.products",
    "src.apps.cart",
    "src.apps.orders",
]

SITE_ID = 1

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "src.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # `allauth` needs this from django
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "src.wsgi.application"

# Database configuration
if PROJECT_ENVIRONMENT == "production":
    # PostgreSQL for production (Railway, Docker, etc.)
    # Railway provides both POSTGRES_* and PG* variables, prefer PG* format
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("PGDATABASE", default=config("POSTGRES_DB", default="railway")),
            "USER": config("PGUSER", default=config("POSTGRES_USER", default="postgres")),
            "PASSWORD": config("PGPASSWORD", default=config("POSTGRES_PASSWORD", default="")),
            "HOST": config("PGHOST", default=config("POSTGRES_HOST", default="localhost")),
            "PORT": config("PGPORT", default=config("POSTGRES_PORT", default="5432")),
        }
    }
else:
    # SQLite for development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "Europe/London"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# CUSTOM SETTINGS

TAGGIT_CASE_INSENSITIVE = True

# CORS settings
if PROJECT_ENVIRONMENT == "production":
    # In production, only allow specific frontend URL
    CORS_ALLOWED_ORIGINS = config(
        "CORS_ALLOWED_ORIGINS",
        default="https://e-commerce-frontend-lyart-seven.vercel.app",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )
    CORS_ORIGIN_ALLOW_ALL = False
else:
    # In development, allow all origins
    CORS_ORIGIN_ALLOW_ALL = True

# authentication related stuff
AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": (
        # 'rest_framework.permissions.IsAuthenticated',
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"

REST_AUTH_SERIALIZERS = {
    "USER_DETAILS_SERIALIZER": "accounts.api.serializers.CustomUserDetailsSerializer",
    "LOGIN_SERIALIZER": "accounts.api.serializers.CustomLoginSerializer",
}

REST_AUTH_REGISTER_SERIALIZERS = {
    "REGISTER_SERIALIZER": "accounts.api.serializers.CustomRegisterSerializer",
}



SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'jwt-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'jwt-refresh-token',
    'JWT_AUTH_HTTPONLY': False,
    'SESSION_LOGIN': False,
    'LOGIN_SERIALIZER': 'dj_rest_auth.serializers.LoginSerializer',
    'TOKEN_SERIALIZER': 'dj_rest_auth.serializers.TokenSerializer',
    'JWT_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'JWT_SERIALIZER_WITH_EXPIRATION': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'JWT_TOKEN_CLAIMS_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Paystack settings
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = config("PAYSTACK_PUBLIC_KEY")
PAYSTACK_WEBHOOK_SECRET = config("PAYSTACK_WEBHOOK_SECRET", default=PAYSTACK_SECRET_KEY)

# Frontend URL for callbacks
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# Payment settings
PAYMENT_SETTINGS = {
    'DEFAULT_CURRENCY': 'NGN',
    'SUPPORTED_CURRENCIES': ['NGN', 'USD', 'GBP', 'EUR'],
    'MIN_PAYMENT_AMOUNT': Decimal('1.00'),
    'MAX_PAYMENT_AMOUNT': Decimal('50000000.00'),  # 50 million
    'ENABLE_WEBHOOKS': True,
    'WEBHOOK_TIMEOUT': 30,  # seconds
    'RETRY_FAILED_WEBHOOKS': True,
    'MAX_WEBHOOK_RETRIES': 3,
    'ENABLE_FRAUD_DETECTION': True,
    'MAX_PAYMENT_ATTEMPTS_PER_HOUR': 10,
    'ENABLE_REFUNDS': True,
    'AUTO_REFUND_TIMEOUT_HOURS': 48,  # Auto-refund after 48 hours if not processed
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if PROJECT_ENVIRONMENT != "production":
    STATIC_URL = "/static/"
    STATIC_ROOT = BASE_DIR / "static"

    # Media files
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"


if PROJECT_ENVIRONMENT == "production":
    INSTALLED_APPS += ["storages"]

    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]
    STATICFILES_STORAGE = "src.storage_backends.StaticStorage"
    DEFAULT_FILE_STORAGE = "src.storage_backends.MediaStorage"

    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
    AWS_PRELOAD_METADATA = True
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    ADMIN_MEDIA_PREFIX = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/admin/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
