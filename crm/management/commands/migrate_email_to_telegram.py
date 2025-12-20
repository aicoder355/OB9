from django.core.management.base import BaseCommand
from crm.models import Client, Driver
import re
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Attempts to migrate existing email values to telegram fields when appropriate.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not save changes, just report')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        client_migrated = 0
        driver_migrated = 0
        client_skipped = []
        driver_skipped = []

        # Helper to extract digits (possible chat id) or username
        digits_re = re.compile(r"\+?\d+")

        self.stdout.write('Scanning clients...')
        clients = Client.objects.exclude(email='').filter(telegram_chat_id__isnull=True)
        for c in clients:
            email = (c.email or '').strip()
            if not email:
                continue
            # If email is pure digits or +digits, treat as chat id
            m = digits_re.fullmatch(re.sub(r"\D", "", email))
            if m and len(email) <= 20:
                # numeric-looking value
                try:
                    chat = int(re.sub(r"\D", "", email))
                    self.stdout.write(f'Client {c.id}: setting telegram_chat_id={chat}')
                    if not dry_run:
                        c.telegram_chat_id = chat
                        c.save()
                    client_migrated += 1
                    continue
                except Exception as e:
                    client_skipped.append((c.id, email, str(e)))
                    continue

            # If value looks like a Telegram username (starts with @ or has no @domain), store as username
            if email.startswith('@') or ('@' not in email):
                username = email.lstrip('@')[:100]
                self.stdout.write(f'Client {c.id}: setting telegram_username={username}')
                if not dry_run:
                    c.telegram_username = username
                    c.save()
                client_migrated += 1
                continue

            client_skipped.append((c.id, email))

        self.stdout.write('Scanning drivers...')
        drivers = Driver.objects.exclude(email='').filter(telegram_chat_id__isnull=True)
        for d in drivers:
            email = (d.email or '').strip()
            if not email:
                continue
            m = digits_re.fullmatch(re.sub(r"\D", "", email))
            if m and len(email) <= 20:
                try:
                    chat = int(re.sub(r"\D", "", email))
                    self.stdout.write(f'Driver {d.id}: setting telegram_chat_id={chat}')
                    if not dry_run:
                        d.telegram_chat_id = chat
                        d.save()
                    driver_migrated += 1
                    continue
                except Exception as e:
                    driver_skipped.append((d.id, email, str(e)))
                    continue

            if email.startswith('@') or ('@' not in email):
                username = email.lstrip('@')[:100]
                self.stdout.write(f'Driver {d.id}: setting telegram_username={username}')
                if not dry_run:
                    # Driver model doesn't have telegram_username field; skip if absent
                    if hasattr(d, 'telegram_username'):
                        d.telegram_username = username
                        d.save()
                        driver_migrated += 1
                        continue
                    else:
                        driver_skipped.append((d.id, email, 'no telegram_username field'))
                        continue

            driver_skipped.append((d.id, email))

        self.stdout.write('--- Summary ---')
        self.stdout.write(f'Clients migrated: {client_migrated}')
        self.stdout.write(f'Drivers migrated: {driver_migrated}')
        if client_skipped:
            self.stdout.write(f'Clients skipped: {len(client_skipped)} (examples: {client_skipped[:5]})')
        if driver_skipped:
            self.stdout.write(f'Drivers skipped: {len(driver_skipped)} (examples: {driver_skipped[:5]})')
        self.stdout.write('Done.')
