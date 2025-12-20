import logging
import requests
from django.conf import settings
from asgiref.sync import sync_to_async

from .models import Order, Client

logger = logging.getLogger(__name__)


def _get_token() -> str:
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN is not set in settings')
    return token


def send_notification(chat_id: int | str, text: str, reply_markup: dict | None = None) -> bool:
    token = _get_token()
    if not token:
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'

    try:
        if isinstance(chat_id, str) and chat_id.strip() == '':
            logger.error('Empty chat_id passed to send_notification')
            return False
    except Exception:
        logger.exception('Invalid chat_id type')
        return False

    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True,
    }
    if reply_markup is not None:
        # If caller passed an InlineKeyboardMarkup object, convert to dict
        try:
            if hasattr(reply_markup, 'to_dict'):
                payload['reply_markup'] = reply_markup.to_dict()
            else:
                payload['reply_markup'] = reply_markup
        except Exception:
            payload['reply_markup'] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            try:
                logger.error('Telegram sendMessage failed (%s): %s', resp.status_code, resp.text)
            except Exception:
                logger.exception('Failed to read Telegram response body')
            return False

        data = resp.json()
        ok = data.get('ok', False)
        if not ok:
            logger.error('Telegram API returned not ok: %s', data)
        return ok
    except Exception:
        logger.exception('Failed to send telegram message')
        return False


async def notify_admins_new_client(client):
    admin_ids = getattr(settings, 'TELEGRAM_ADMIN_CHAT_IDS', [])
    if not admin_ids:
        return
    
    text = (
        f"🆕 Новая регистрация!\n\n"
        f"Имя: {client.name}\n"
        f"Телефон: {client.phone}\n"
        f"Адрес: {client.address}\n"
        f"Username: @{client.telegram_username or 'не указан'}\n\n"
        f"ID клиента: {client.id}\n"
        f"Для подтверждения откройте админ-панель."
    )
    
    for admin_id in admin_ids:
        send_notification(admin_id, text)


async def notify_admins_new_order(order):
    admin_ids = getattr(settings, 'TELEGRAM_ADMIN_CHAT_IDS', [])
    if not admin_ids:
        return
    
    text = (
        f"🛒 Новый заказ #{order.id}!\n\n"
        f"Клиент: {order.client.name}\n"
        f"Телефон: {order.client.phone}\n"
        f"Товар: {order.product.name} x{order.quantity}\n"
        f"Сумма: {getattr(order, 'total_amount', '')}₽\n"
        f"Адрес: {order.delivery_address}\n\n"
        f"Назначьте водителя в админ-панели."
    )
    
    for admin_id in admin_ids:
        send_notification(admin_id, text)


async def notify_driver_new_order(order):
    if not order.driver or not order.driver.telegram_chat_id:
        return
    
    text = (
        f"📦 Вам назначен новый заказ #{order.id}\n\n"
        f"Клиент: {order.client.name}\n"
        f"Телефон: {order.client.phone}\n"
        f"Адрес: {order.delivery_address}\n"
        f"Товар: {order.product.name} x{order.quantity}\n"
        f"Сумма: {getattr(order, 'total_amount', '')}₽\n\n"
        f"Используйте /my_deliveries для просмотра всех заказов."
    )
    # Use compact driver keyboard (deliver / cancel) for cleaner UI
    try:
        from .bot_keyboards import get_driver_simple_actions
        reply_markup = get_driver_simple_actions(order.id)
    except Exception:
        # Fallback to simple dict keyboard
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Доставлен", "callback_data": f"confirm_deliver_{order.id}"},
                    {"text": "❌ Отменён", "callback_data": f"confirm_cancel_{order.id}"},
                ]
            ]
        }

    send_notification(order.driver.telegram_chat_id, text, reply_markup=reply_markup)
