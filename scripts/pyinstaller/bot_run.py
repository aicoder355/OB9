import os
import sys
from pathlib import Path
import asyncio

def main():
    # Ensure project root is on sys.path and current working directory
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    sys.path.insert(0, str(root))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_delivery_crm.settings')

    # Import and run the telegram bot Application
    from crm.telegram_bot import create_application

    app = create_application()
    # run_polling is blocking; call it directly
    app.run_polling()

if __name__ == '__main__':
    main()
