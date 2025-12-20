from django.core.management.base import BaseCommand
from crm.models import Driver


class Command(BaseCommand):
    help = 'Generate access code for driver to login via Telegram bot'

    def add_arguments(self, parser):
        parser.add_argument('driver_id', type=int, help='Driver ID')

    def handle(self, *args, **options):
        driver_id = options['driver_id']
        
        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            self.stderr.write(f'Driver with ID {driver_id} not found')
            return
        
        code = driver.generate_access_code()
        
        self.stdout.write(self.style.SUCCESS(
            f'\n'
            f'✅ Access code generated for driver: {driver.name}\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'CODE: {code}\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'Valid for 24 hours\n'
            f'\n'
            f'Driver should use /driver_login in Telegram bot\n'
            f'and enter this code.\n'
        ))
