import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run telegram bot using python-telegram-bot Application.run_webhook'

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8000)))
        parser.add_argument('--path', type=str, default=os.environ.get('TELEGRAM_WEBHOOK_PATH', '/telegram/webhook/'))

    def handle(self, *args, **options):
        port = options['port']
        path = options['path']

        from crm.telegram_bot import create_application

        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            self.stderr.write('TELEGRAM_BOT_TOKEN is not set')
            return

        webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL') or getattr(settings, 'TELEGRAM_WEBHOOK_URL', None)
        if not webhook_url:
            self.stderr.write('TELEGRAM_WEBHOOK_URL is not set; you can still run webhook server without registering URL')

        app = create_application(token)

        self.stdout.write(self.style.SUCCESS(f'Starting webhook server on 0.0.0.0:{port}{path}'))
        try:
            # run_webhook will set the webhook URL if webhook_url is provided
            app.run_webhook(listen='0.0.0.0', port=port, webhook_url=webhook_url, webhook_path=path)
        except Exception as exc:
            logger.exception('Webhook server failed: %s', exc)
            self.stderr.write(f'Webhook server failed: {exc}')