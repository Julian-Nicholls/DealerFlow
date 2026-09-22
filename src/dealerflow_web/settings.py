from pathlib import Path
import os
BASE_DIR=Path(__file__).resolve().parents[2]
SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY","dealerflow-local-development-key")
DEBUG=os.environ.get("DJANGO_DEBUG","1").lower() in {"1","true","yes"}
ALLOWED_HOSTS=[x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS","localhost,127.0.0.1").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS","").split(",") if x.strip()]
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","dealerflow_web.dashboard"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="dealerflow_web.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="dealerflow_web.wsgi.application"
ASGI_APPLICATION="dealerflow_web.asgi.application"
db=Path(os.environ.get("DEALERFLOW_DB_PATH",BASE_DIR/"data"/"db.sqlite3")); db.parent.mkdir(parents=True,exist_ok=True)
DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":db}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE="en-ca"; TIME_ZONE="America/Toronto"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; STATIC_ROOT=BASE_DIR/"staticfiles"
STORAGES={"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
DEALERFLOW_SCENARIO_DIR=BASE_DIR/"scenarios"
