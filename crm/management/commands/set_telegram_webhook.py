from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import os


class Command(BaseCommand):
    help = 'Set Telegram webhook URL from TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL env vars'

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.environ.get('TELEGRAM_BOT_TOKEN')
        webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL') or getattr(settings, 'TELEGRAM_WEBHOOK_URL', None)

        if not token:
            self.stderr.write('TELEGRAM_BOT_TOKEN is not set')
            return
        if not webhook_url:
            self.stderr.write('TELEGRAM_WEBHOOK_URL is not set (set env var)')
            return

        url = f'https://api.telegram.org/bot{token}/setWebhook'
        resp = requests.post(url, data={'url': webhook_url})
        try:
            data = resp.json()
        except Exception:
            self.stderr.write(f'Failed to parse response: {resp.text}')
            return

        if data.get('ok'):
            self.stdout.write(self.style.SUCCESS(f'Webhook set: {webhook_url}'))
        else:
            self.stderr.write(f'Failed to set webhook: {data}')
