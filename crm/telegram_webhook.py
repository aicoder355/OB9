import json
import logging
import asyncio

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .telegram_bot import create_application
from telegram import Update

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    """Django view to accept Telegram webhook POSTs and dispatch to the bot Application.

    This view expects Telegram JSON payload and will create the bot Application
    and run its update handling for the incoming Update.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        logger.exception('Invalid JSON in Telegram webhook')
        return HttpResponse(status=400)

    try:
        update = Update.de_json(data, None)
    except Exception:
        logger.exception('Failed to build telegram.Update from JSON')
        return HttpResponse(status=400)

    try:
        app = create_application()
    except Exception:
        logger.exception('Failed to create telegram Application')
        return HttpResponse(status=500)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # app.process_update is a coroutine that dispatches the update to handlers
        coro = app.process_update(update)
        loop.run_until_complete(coro)
    except Exception:
        logger.exception('Failed to process Telegram update')
        return HttpResponse(status=500)

    return JsonResponse({'ok': True})
