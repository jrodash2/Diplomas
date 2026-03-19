import os
import sys

# Ruta a tu entorno virtual
VENV_PATH = r"C:\Users\Administrador\Documents\UPCV\venv"

# Agrega el entorno virtual al sys.path
site_packages = os.path.join(VENV_PATH, 'Lib', 'site-packages')
sys.path.insert(0, site_packages)

# Asegura que la app también vea el proyecto
project_path = r"C:\Users\Administrador\Documents\UPCV\upcv_app"
sys.path.insert(0, project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'upcv_app.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
