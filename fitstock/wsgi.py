import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitstock.settings')

application = get_wsgi_application()

# Vercel a besoin de cette variable
app = application