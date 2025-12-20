import logging
import requests
import asyncio
from typing import Optional
from asgiref.sync import sync_to_async

from django.conf import settings

# Lazy-import telegram types to avoid import-time side-effects
Update = None
ApplicationBuilder = None
CommandHandler = None
MessageHandler = None
CallbackQueryHandler = None
ConversationHandler = None
ContextTypes = None
filters = None

from .models import Order, Client
from .telegram_helpers import send_notification, notify_admins_new_client, notify_admins_new_order, notify_driver_new_order

logger = logging.getLogger(__name__)


def _get_token() -> str:
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN is not set in settings')
    return token


# `send_notification` and async notification helpers are provided by
# `crm.telegram_helpers` and imported above to keep `telegram_bot.py` focused
# on building the python-telegram-bot Application and handlers.


async def notify_admins_new_client(client):
    """Уведомление администраторов о новом клиенте"""
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
    """Уведомление администраторов о новом заказе"""
    admin_ids = getattr(settings, 'TELEGRAM_ADMIN_CHAT_IDS', [])
    if not admin_ids:
        return
    
    text = (
        f"🛒 Новый заказ #{order.id}!\n\n"
        f"Клиент: {order.client.name}\n"
        f"Телефон: {order.client.phone}\n"
        f"Товар: {order.product.name} x{order.quantity}\n"
        f"Сумма: {order.total_amount}₽\n"
        f"Адрес: {order.delivery_address}\n\n"
        f"Назначьте водителя в админ-панели."
    )
    
    for admin_id in admin_ids:
        send_notification(admin_id, text)


async def notify_driver_new_order(order):
    """Уведомление водителя о новом заказе"""
    if not order.driver or not order.driver.telegram_chat_id:
        return
    
    text = (
        f"📦 Вам назначен новый заказ #{order.id}\n\n"
        f"Клиент: {order.client.name}\n"
        f"Телефон: {order.client.phone}\n"
        f"Адрес: {order.delivery_address}\n"
        f"Товар: {order.product.name} x{order.quantity}\n"
        f"Сумма: {order.total_amount}₽\n\n"
        f"Используйте /my_deliveries для просмотра всех заказов."
    )
    
    send_notification(order.driver.telegram_chat_id, text)


async def start(update, context) -> None:
    """Handler for /start"""
    from .bot_handlers import start_client
    await start_client(update, context)


async def help_command(update, context) -> None:
    """Handler for /help"""
    chat_id = update.effective_chat.id
    
    # Проверяем, водитель или клиент
    from .models import Driver
    driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=chat_id, telegram_verified=True).first)()
    
    if driver:
        text = (
            "🚗 Команды для водителя:\n\n"
            "/my_deliveries - Мои доставки\n"
            "/help - Эта справка\n\n"
            "Используйте кнопки для управления заказами."
        )
    else:
        text = (
            "📱 Доступные команды:\n\n"
            "👤 Для клиентов:\n"
            "/start - Начать работу\n"
            "/register - Регистрация\n"
            "/catalog - Каталог товаров\n"
            "/order - Сделать заказ\n"
            "/myorders - Мои заказы\n\n"
            "🚗 Для водителей:\n"
            "/driver_login - Авторизация водителя\n"
            "/my_deliveries - Мои доставки\n\n"
            "/help - Эта справка"
        )
    
    await context.bot.send_message(chat_id=chat_id, text=text)


async def handle_text_message(update, context):
    """Обработка текстовых сообщений (кнопки меню)"""
    # Сначала проверяем, находится ли водитель в состоянии ввода комментария
    handled = await _handle_driver_comment_message(update, context)
    if handled:
        return

    text = update.message.text

    # Если мы ожидаем количество для простого заказа — обрабатываем ввод (manual entry)
    if context.user_data.get('awaiting_order_quantity'):
        qty_text = update.message.text.strip()
        try:
            quantity = int(qty_text)
            if quantity <= 0:
                raise ValueError()
        except Exception:
            await update.message.reply_text('Пожалуйста, введите корректное целое положительное число.')
            return

        # Сохраняем выбранное количество и показываем экран подтверждения
        context.user_data.pop('awaiting_order_quantity', None)
        context.user_data['simple_order_quantity'] = quantity

        chat_id = update.effective_chat.id
        from asgiref.sync import sync_to_async as _sync_to_async
        from .models import Client, Product
        from .bot_keyboards import get_confirmation_keyboard

        client = await _sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).first)()
        product = await _sync_to_async(Product.objects.first)()
        if not client or not product:
            await update.message.reply_text('Ошибка: не найден клиент или товар.')
            return

        total = product.price * quantity
        confirm_text = (
            f"📦 Подтвердите заказ:\n\n"
            f"Товар: {product.name}\n"
            f"Количество: {quantity}\n"
            f"Сумма: {total}₽\n"
            f"Адрес доставки:\n{client.address}"
        )

        keyboard = get_confirmation_keyboard('simple_order', quantity)
        await update.message.reply_text(confirm_text, reply_markup=keyboard)
        return

    if text == "📋 Каталог товаров":
        from .bot_handlers import catalog
        await catalog(update, context)
    elif text == "🛒 Сделать заказ":
        from .bot_handlers import simple_order_start
        await simple_order_start(update, context)
    elif text == "📦 Мои заказы":
        from .bot_handlers import my_orders
        await my_orders(update, context)
    elif text == "📋 Мои доставки" or text == "🔄 Обновить":
        from .bot_handlers import my_deliveries
        await my_deliveries(update, context)
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🚪 Выход":
        chat_id = update.effective_chat.id
        from .models import Driver
        driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=chat_id).first)()
        if driver:
            driver.telegram_chat_id = None
            driver.telegram_verified = False
            await sync_to_async(driver.save)()
            await update.message.reply_text("Вы вышли из системы.")


async def handle_callback_query(update, context):
    """Обработка callback запросов от inline кнопок"""
    query = update.callback_query
    data = query.data
    
    # Обработка статусов заказов
    if data.startswith('status_'):
        parts = data.split('_')
        order_id = int(parts[1])
        new_status = parts[2]

        try:
            order = await sync_to_async(Order.objects.select_related('client', 'driver').get)(id=order_id)

            # Проверяем, что кнопку нажимает назначенный водитель
            from .models import Driver
            pressed_by_chat = update.effective_user.id
            pressing_driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=pressed_by_chat).first)()
            if not pressing_driver or not order.driver or pressing_driver.id != order.driver.id:
                await query.answer("Вы не назначены на этот заказ.", show_alert=True)
                return

            order.status = new_status
            await sync_to_async(order.save)()

            await query.answer("Статус обновлён!")
            await query.edit_message_text(
                f"✅ Статус заказа #{order_id} изменён на: {order.get_status_display()}"
            )

            # Уведомляем клиента (signals также обработают это, но здесь краткое уведомление)
            if order.client.telegram_chat_id:
                send_notification(
                    order.client.telegram_chat_id,
                    f"Статус вашего заказа #{order_id} изменён: {order.get_status_display()}"
                )
        except Order.DoesNotExist:
            await query.answer("Заказ не найден!")
        return

    # Обработка выбора количества в упрощённом потоке заказа
    if data.startswith('qty_'):
        # Если пользователь выбрал "Другое" — переводим в текстовый ввод
        if data == 'qty_other':
            context.user_data['awaiting_order_quantity'] = True
            await query.answer()
            await query.edit_message_text("Пожалуйста, введите количество (целое число):")
            return

        try:
            quantity = int(data.split('_')[1])
        except Exception:
            await query.answer()
            return

        # Показываем экран подтверждения простого заказа
        chat_id = update.effective_chat.id
        from .models import Client, Product

        client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).first)()
        product = await sync_to_async(Product.objects.first)()
        if not client or not product:
            await query.answer('Ошибка: не найден клиент или товар.', show_alert=True)
            return

        total = product.price * quantity
        confirm_text = (
            f"📦 Подтвердите заказ:\n\n"
            f"Товар: {product.name}\n"
            f"Количество: {quantity}\n"
            f"Сумма: {total}₽\n"
            f"Адрес доставки:\n{client.address}"
        )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        # Создаём клавиатуру подтверждения с кнопкой 'Заказать'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('Заказать', callback_data=f'simple_confirm_{quantity}'), InlineKeyboardButton('❌ Отмена', callback_data='cancel')]
        ])
        await query.answer()
        await query.edit_message_text(confirm_text, reply_markup=keyboard)
        # Сохраняем временно выбранное количество
        context.user_data['simple_order_quantity'] = quantity
        return
    
    # Обработка комментариев
    elif data.startswith('comment_'):
        order_id = int(data.split('_')[1])
        context.user_data['comment_order_id'] = order_id
        await query.answer()
        await query.edit_message_text(
            f"Введите комментарий для заказа #{order_id}:"
        )
    
    # Обработка подтверждения доставки водителем
    elif data.startswith('confirm_deliver_'):
        order_id = int(data.split('_')[2])
        try:
            order = await sync_to_async(Order.objects.select_related('client', 'driver').get)(id=order_id)
            
            # Проверяем, что кнопку нажимает назначенный водитель
            from .models import Driver
            pressed_by_chat = update.effective_user.id
            pressing_driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=pressed_by_chat).first)()
            if not pressing_driver or not order.driver or pressing_driver.id != order.driver.id:
                await query.answer("Вы не назначены на этот заказ.", show_alert=True)
                return
            
            order.status = 'delivered'
            await sync_to_async(order.save)()
            
            await query.answer("Заказ отмечен как доставлен!")
            await query.edit_message_text(
                f"✅ Заказ #{order.id} успешно доставлен!\n"
                f"Адрес: {order.delivery_address}"
            )
            
            # Уведомляем клиента
            if order.client.telegram_chat_id:
                send_notification(
                    order.client.telegram_chat_id,
                    f"✅ Ваш заказ #{order.id} был доставлен. Спасибо за заказ!"
                )
        except Order.DoesNotExist:
            await query.answer("Заказ не найден!", show_alert=True)
    
    # Обработка отмены заказа водителем
    elif data.startswith('confirm_cancel_'):
        order_id = int(data.split('_')[2])
        try:
            order = await sync_to_async(Order.objects.select_related('client', 'driver').get)(id=order_id)
            
            # Проверяем, что кнопку нажимает назначенный водитель
            from .models import Driver
            pressed_by_chat = update.effective_user.id
            pressing_driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=pressed_by_chat).first)()
            if not pressing_driver or not order.driver or pressing_driver.id != order.driver.id:
                await query.answer("Вы не назначены на этот заказ.", show_alert=True)
                return
            
            order.status = 'canceled'
            await sync_to_async(order.save)()
            
            await query.answer("Заказ отменён")
            await query.edit_message_text(
                f"❌ Заказ #{order.id} отменён\n"
                f"Адрес: {order.delivery_address}"
            )
            
            # Уведомляем клиента
            if order.client.telegram_chat_id:
                send_notification(
                    order.client.telegram_chat_id,
                    f"❌ Ваш заказ #{order.id} был отменён водителем."
                )
        except Order.DoesNotExist:
            await query.answer("Заказ не найден!", show_alert=True)
    
    # Обработка сортировки
    elif data.startswith('sort_'):
        from .bot_handlers import handle_sort_callback
        await handle_sort_callback(update, context)
    
    elif data == "cancel":
        await query.answer()
        await query.edit_message_text("Отменено.")

    # Подтверждение простого заказа (кнопка 'Заказать')
    if data.startswith('simple_confirm_'):
        try:
            quantity = int(data.split('_')[-1])
        except Exception:
            await query.answer()
            return

        # Создаём заказ
        chat_id = update.effective_chat.id
        from .models import Client, Product, Driver, Order as _Order

        client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).first)()
        if not client or client.registration_status != 'approved':
            await query.answer('Вы не зарегистрированы или не подтверждены для заказов.', show_alert=True)
            return

        product = await sync_to_async(Product.objects.first)()
        if not product:
            await query.answer('Товары временно недоступны.', show_alert=True)
            return

        driver = None
        if getattr(client, 'region_id', None):
            driver = await sync_to_async(Driver.objects.filter(region_id=client.region_id).first)()

        try:
            order = await sync_to_async(_Order.objects.create)(
                client=client,
                product=product,
                quantity=quantity,
                delivery_address=client.address,
                total_amount=product.price * quantity,
                payment_amount=product.price * quantity,
                status='planned',
                driver=driver,
            )
            await query.answer('Заказ создан')
            await query.edit_message_text(f'✅ Заказ #{order.id} успешно создан!\nСумма: {order.total_amount}₽')

            from .telegram_helpers import notify_admins_new_order, notify_driver_new_order
            await notify_admins_new_order(order)
            if driver:
                await notify_driver_new_order(order)
        except Exception as e:
            logger.exception('Error creating simple confirmed order: %s', e)
            await query.answer('Ошибка при создании заказа.', show_alert=True)
            await query.edit_message_text('Произошла ошибка при создании заказа. Попробуйте позже.')
        finally:
            # Очистим временные данные
            context.user_data.pop('simple_order', None)
            context.user_data.pop('simple_order_quantity', None)
            context.user_data.pop('awaiting_order_quantity', None)
        return


async def _handle_driver_comment_message(update, context):
    """Если водитель в состоянии ввода комментария, сохранить его в заказе."""
    chat_id = update.effective_chat.id
    from .models import Driver
    driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=chat_id, telegram_verified=True).first)()
    if not driver:
        return False

    comment_order_id = context.user_data.pop('comment_order_id', None)
    if not comment_order_id:
        return False

    text = update.message.text.strip()
    try:
        order = await sync_to_async(Order.objects.get)(id=comment_order_id)
    except Order.DoesNotExist:
        await update.message.reply_text("Заказ не найден.")
        return True

    # Проверяем, что водитель назначен на заказ
    if not order.driver or order.driver.id != driver.id:
        await update.message.reply_text("Вы не назначены на этот заказ.")
        return True

    order.driver_comment = text
    await sync_to_async(order.save)()

    await update.message.reply_text(f"Комментарий сохранён для заказа #{order.id}.")
    return True


def create_application(token: Optional[str] = None):
    """Create and return a python-telegram-bot Application with handlers registered.

    Usage (in management command):
        app = create_application()
        app.run_polling()
    """
    token = token or _get_token()
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')

    # Import telegram objects lazily to avoid import-time side-effects
    global Update, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
    if ApplicationBuilder is None:
        from telegram import Update as _Update
        from telegram.ext import (
            ApplicationBuilder as _ApplicationBuilder,
            CommandHandler as _CommandHandler,
            MessageHandler as _MessageHandler,
            CallbackQueryHandler as _CallbackQueryHandler,
            ConversationHandler as _ConversationHandler,
            ContextTypes as _ContextTypes,
            filters as _filters
        )
        Update = _Update
        ApplicationBuilder = _ApplicationBuilder
        CommandHandler = _CommandHandler
        MessageHandler = _MessageHandler
        CallbackQueryHandler = _CallbackQueryHandler
        ConversationHandler = _ConversationHandler
        ContextTypes = _ContextTypes
        filters = _filters

    # Ensure there is an asyncio event loop in the main thread (fixes Windows RuntimeError)
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        app = ApplicationBuilder().token(token).build()
        
        # Import handlers
        from .bot_handlers import (
            register_start, register_name, register_phone, register_address,
            order_start, order_product_selected, order_quantity_selected, order_quantity_text, order_confirm,
            driver_login_start, driver_login_code,
            catalog, my_orders, my_deliveries,
            cancel,
            REGISTRATION_NAME, REGISTRATION_PHONE, REGISTRATION_ADDRESS,
            ORDER_PRODUCT, ORDER_QUANTITY, ORDER_ADDRESS_CONFIRM,
            DRIVER_LOGIN_CODE,
        )
        
        # Registration conversation
        registration_conv = ConversationHandler(
            entry_points=[CommandHandler('register', register_start)],
            states={
                REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
                REGISTRATION_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)],
                REGISTRATION_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_address)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Order conversation
        order_conv = ConversationHandler(
            entry_points=[
                CommandHandler('order', order_start),
                MessageHandler(filters.Regex('^🛒 Сделать заказ$'), order_start)
            ],
            states={
                ORDER_PRODUCT: [CallbackQueryHandler(order_product_selected, pattern='^product_')],
                # ORDER_QUANTITY accepts both inline button callbacks (qty_1, qty_2, ...) and
                # textual input when user chooses '✏️ Другое' (qty_other).
                ORDER_QUANTITY: [
                    CallbackQueryHandler(order_quantity_selected, pattern='^(qty_|cancel)'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, order_quantity_text),
                ],
                ORDER_ADDRESS_CONFIRM: [CallbackQueryHandler(order_confirm, pattern='^(confirm_address|change_address|cancel)$')],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_message=False,
        )
        
        # Driver login conversation
        driver_login_conv = ConversationHandler(
            entry_points=[CommandHandler('driver_login', driver_login_start)],
            states={
                DRIVER_LOGIN_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, driver_login_code)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Add conversation handlers
        app.add_handler(registration_conv)
        app.add_handler(order_conv)
        app.add_handler(driver_login_conv)
        
        # Add command handlers
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('catalog', catalog))
        app.add_handler(CommandHandler('myorders', my_orders))
        app.add_handler(CommandHandler('my_deliveries', my_deliveries))
        
        # Add callback query handler
        app.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Add text message handler (for menu buttons)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        return app
    except Exception as exc:
        # Fallback: implement a minimal getUpdates-based polling loop using HTTP calls.
        logger.warning('ApplicationBuilder failed (%s). Using HTTP getUpdates fallback.', exc)

        import time

        class PollingBot:
            def __init__(self, token):
                self.token = token
                self.offset = None
                self.base_url = f'https://api.telegram.org/bot{self.token}'

            def _get_updates(self, timeout=20):
                params = {'timeout': timeout}
                if self.offset:
                    params['offset'] = self.offset
                try:
                    r = requests.get(self.base_url + '/getUpdates', params=params, timeout=timeout + 5)
                    r.raise_for_status()
                    data = r.json()
                    if data.get('ok'):
                        return data.get('result', [])
                except Exception:
                    logger.exception('Error fetching updates')
                return []

            def _handle_message(self, message):
                chat = message.get('chat') or {}
                chat_id = chat.get('id')
                text = message.get('text', '') or ''
                if not text or not chat_id:
                    return

                parts = text.strip().split()
                cmd = parts[0].lstrip('/').lower()

                if cmd == 'start':
                    user_first = (message.get('from') or {}).get('first_name', '')
                    reply = f'Привет, {user_first}!\nЯ бот сервиса доставки воды.\nИспользуйте /help для списка команд.'
                    send_notification(chat_id, reply)
                elif cmd == 'help':
                    reply = (
                        "📱 Доступные команды:\n\n"
                        "/start - Начать работу\n"
                        "/register - Регистрация\n"
                        "/catalog - Каталог товаров\n"
                        "/help - Эта справка"
                    )
                    send_notification(chat_id, reply)

            def run_polling(self):
                logger.info('Starting simple HTTP long-polling loop')
                try:
                    while True:
                        updates = self._get_updates()
                        for upd in updates:
                            update_id = upd.get('update_id')
                            if update_id is not None:
                                self.offset = update_id + 1

                            message = upd.get('message') or upd.get('edited_message')
                            if message:
                                self._handle_message(message)
                        time.sleep(0.5)
                except KeyboardInterrupt:
                    logger.info('Polling stopped by user')
                except Exception:
                    logger.exception('Polling loop failed')

        return PollingBot(token)
