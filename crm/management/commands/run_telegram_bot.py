from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Run the integrated Telegram bot (polling). Use --dry-run to only construct the Application.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not start polling; only initialize the app.')
        parser.add_argument('--token', type=str, help='Optional: override TELEGRAM_BOT_TOKEN for this run')

    def handle(self, *args, **options):
        token = options.get('token') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        dry = options.get('dry_run', False)

        if not token:
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN is not set. Provide --token or set in .env/settings.'))
            return

        try:
            from crm.telegram_bot import create_application
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Failed to import bot code: {exc}'))
            return

        try:
            app = create_application(token)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Failed to create bot application: {exc}'))
            return

        self.stdout.write(self.style.SUCCESS('Telegram Application initialized.'))
        if dry:
            self.stdout.write('Dry run; not starting polling. Use without --dry-run to run.')
            return

        # Start polling (both Application and fallback PollingBot expose run_polling)
        self.stdout.write('Starting polling loop (Ctrl-C to stop)...')
        try:
            # If this is a python-telegram-bot Application
            if hasattr(app, 'run_polling'):
                app.run_polling()
            else:
                # Fallback PollingBot has run_polling too
                app.run_polling()
        except KeyboardInterrupt:
            self.stdout.write('\nPolling stopped by user')
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Bot polling failed: {exc}'))
from django.core.management.base import BaseCommand
import logging

# Import telegram app lazily inside handle() to avoid import-time side effects

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram bot (long-polling)'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot (long-polling)...')
        try:
            from crm.telegram_bot import create_application
            app = create_application()
        except Exception as e:
            logger.exception('Failed to create telegram application: %s', e)
            self.stderr.write(f'Error creating Telegram application: {e}')
            return
        try:
            # If a webhook is registered (or another getUpdates is running) delete it
            # to avoid Conflict: terminated by other getUpdates request.
            # Use a synchronous HTTP call to Telegram API to avoid messing with asyncio loops.
            try:
                from django.conf import settings
                import requests

                token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
                if token:
                    url = f'https://api.telegram.org/bot{token}/deleteWebhook'
                    resp = requests.post(url, params={'drop_pending_updates': True}, timeout=10)
                    if resp.ok:
                        self.stdout.write('Deleted existing Telegram webhook (if any) and dropped pending updates')
                    else:
                        logger.warning('deleteWebhook returned %s: %s', resp.status_code, resp.text)
                else:
                    logger.debug('TELEGRAM_BOT_TOKEN not set; skipping webhook deletion')
            except Exception:
                # If delete_webhook fails, log but continue to run polling — user may still see conflict
                logger.exception('Failed to delete existing webhook before polling')

            # This will block and run until interrupted
            app.run_polling()
        except KeyboardInterrupt:
            self.stdout.write('Telegram bot stopped by user')
        except Exception as e:
            logger.exception('Error while running telegram bot: %s', e)
            self.stderr.write(f'Error while running telegram bot: {e}')