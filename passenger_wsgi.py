import os, sys

site_user_root_dir = '/home/h/hazb1nh2/finik-i-myata.rf/public_html'

# Добавляем пользовательские site-packages для Python 3.10
user_site_packages = os.path.expanduser('~/.local/lib/python3.10/site-packages')
if os.path.exists(user_site_packages):
    sys.path.insert(0, user_site_packages)

# Также проверяем другие версии на случай если нужно
for version in ['3.10', '3.9', '3.8', '3.7', '3.6']:
    alt_path = os.path.expanduser(f'~/.local/lib/python{version}/site-packages')
    if os.path.exists(alt_path) and alt_path not in sys.path:
        sys.path.insert(0, alt_path)

# Добавляем папку проекта
sys.path.insert(0, site_user_root_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qrmenu.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
