import os
import sys
from pathlib import Path

def main():
    # Ensure project root is on sys.path and current working directory
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    sys.path.insert(0, str(root))

    # Use Django management to run the dev server
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_delivery_crm.settings')
    from django.core.management import execute_from_command_line

    # mimic `python manage.py runserver 0.0.0.0:8000`
    execute_from_command_line([str(root / 'manage.py'), 'runserver', '0.0.0.0:8000'])

if __name__ == '__main__':
    main()
