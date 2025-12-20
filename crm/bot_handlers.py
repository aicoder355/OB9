"""Telegram bot handlers for client and driver interactions"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from asgiref.sync import sync_to_async

from .models import Client, Driver, Order, Product
from .bot_keyboards import (
    get_client_main_menu,
    get_driver_main_menu,
    get_products_keyboard,
    get_quantity_keyboard,
    get_order_actions_keyboard,
    get_confirmation_keyboard,
    get_address_confirmation_keyboard,
    get_sort_keyboard,
    get_driver_simple_actions,
)

logger = logging.getLogger(__name__)

# Conversation states
REGISTRATION_NAME, REGISTRATION_PHONE, REGISTRATION_ADDRESS = range(3)
ORDER_PRODUCT, ORDER_QUANTITY, ORDER_ADDRESS_CONFIRM = range(3, 6)
DRIVER_LOGIN_CODE = 6
COMMENT_INPUT = 7

# ============= CLIENT HANDLERS =============

async def start_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start для клиентов"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).first)()
    if client:
        if client.registration_status == 'pending':
            await update.message.reply_text(
                f"Здравствуйте, {client.name}!\n\n"
                "Ваша регистрация ожидает подтверждения администратором.\n"
                "Мы уведомим вас, когда сможете начать делать заказы."
            )
        elif client.registration_status == 'approved':
            await update.message.reply_text(
                f"Добро пожаловать, {client.name}! 👋\n\n"
                "Выберите действие из меню ниже:",
                reply_markup=get_client_main_menu()
            )
        else:
            await update.message.reply_text(
                "К сожалению, ваша регистрация была отклонена.\n"
                "Пожалуйста, свяжитесь с администратором."
            )
    else:
        await update.message.reply_text(
            f"Здравствуйте, {user.first_name}! 👋\n\n"
            "Добро пожаловать в бот доставки воды!\n\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "Используйте команду /register"
        )

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации клиента"""
    chat_id = update.effective_chat.id
    exists = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).exists)()
    if exists:
        await update.message.reply_text("Вы уже зарегистрированы!")
        return ConversationHandler.END
    await update.message.reply_text(
        "Начнём регистрацию! 📝\n\n"
        "Как вас зовут? (Введите ваше имя)"
    )
    return REGISTRATION_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение имени при регистрации"""
    context.user_data['registration_name'] = update.message.text
    await update.message.reply_text(
        "Отлично! 👍\n\n"
        "Теперь введите ваш номер телефона в формате: +998901234567"
    )
    return REGISTRATION_PHONE

async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение телефона при регистрации"""
    phone = update.message.text.strip()
    exists = await sync_to_async(Client.objects.filter(phone=phone).exists)()
    if exists:
        await update.message.reply_text(
            "Этот номер телефона уже зарегистрирован!\n"
            "Используйте /start для входа."
        )
        return ConversationHandler.END
    context.user_data['registration_phone'] = phone
    await update.message.reply_text(
        "Отлично! 👍\n\n"
        "Теперь введите ваш адрес доставки:\n"
        "(Например: г. Худжанд, ул. Шерози 123, кв. 45)"
    )
    return REGISTRATION_ADDRESS

async def register_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение адреса и завершение регистрации"""
    address = update.message.text
    chat_id = update.effective_chat.id
    username = update.effective_user.username or ""
    try:
        client = await sync_to_async(Client.objects.create)(
            name=context.user_data['registration_name'],
            phone=context.user_data['registration_phone'],
            address=address,
            telegram_chat_id=chat_id,
            telegram_username=username,
            registration_status='pending',
            email=''  # Пустой email
        )
        await update.message.reply_text(
            "✅ Регистрация успешно завершена!\n\n"
            f"Имя: {client.name}\n"
            f"Телефон: {client.phone}\n"
            f"Адрес: {client.address}\n\n"
            "Ваша заявка отправлена на рассмотрение администратору.\n"
            "Мы уведомим вас, когда регистрация будет подтверждена."
        )
        from .telegram_helpers import notify_admins_new_client
        await notify_admins_new_client(client)
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        await update.message.reply_text(
            "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )
    return ConversationHandler.END

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать каталог товаров"""
    products = await sync_to_async(list)(Product.objects.all())
    if not products:
        await update.message.reply_text("К сожалению, товары пока недоступны.")
        return
    text = "📋 Наш каталог:\n\n"
    for product in products:
        text += f"🔹 {product.name}\n"
        text += f"   Объём: {product.volume}л\n"
        text += f"   Цена: {product.price}₽\n\n"
    text += "Для заказа используйте команду /order или кнопку '🛒 Сделать заказ'"
    await update.message.reply_text(text)

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало оформления заказа"""
    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id, registration_status='approved').first)()
    if not client:
        await update.message.reply_text(
            "Для оформления заказа необходимо зарегистрироваться.\n"
            "Используйте команду /register"
        )
        return ConversationHandler.END
    # Auto-select the default product: prefer 19L bottles if available
    product = await sync_to_async(Product.objects.filter(volume=19).first)()
    if not product:
        # fallback to product with '19' in name
        product = await sync_to_async(Product.objects.filter(name__icontains='19').first)()
    if not product:
        # ultimate fallback to the first product in the catalog
        product = await sync_to_async(Product.objects.first)()

    if not product:
        await update.message.reply_text("К сожалению, товары пока недоступны.")
        return ConversationHandler.END

    # Save selected product and move directly to quantity selection (skip product choice)
    context.user_data['order_product_id'] = product.id
    await update.message.reply_text(
        "Выберите количество или введите вручную:",
        reply_markup=get_quantity_keyboard()
    )
    return ORDER_QUANTITY


async def simple_order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простой поток заказа: сразу запрашиваем количество у клиента."""
    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id, registration_status='approved').first)()
    if not client:
        await update.message.reply_text(
            "Для оформления заказа необходимо зарегистрироваться.\n"
            "Используйте команду /register"
        )
        return
    # Устанавливаем флаг простого заказа и показываем клавиатуру количества
    context.user_data['simple_order'] = True
    await update.message.reply_text(
        "Выберите количество или введите вручную:",
        reply_markup=get_quantity_keyboard()
    )
    return

async def order_product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора товара"""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Заказ отменён.")
        return ConversationHandler.END
    # Expect callback like 'product_<id>' — validate to avoid ValueError
    if not query.data.startswith('product_'):
        await query.answer()
        return ConversationHandler.END
    try:
        product_id = int(query.data.split('_')[1])
    except Exception:
        await query.answer()
        return ConversationHandler.END
    product = await sync_to_async(Product.objects.get)(id=product_id)
    context.user_data['order_product_id'] = product_id
    await query.edit_message_text(
        f"Вы выбрали: {product.name}\n"
        f"Цена: {product.price}₽\n\n"
        "Выберите количество:",
        reply_markup=get_quantity_keyboard()
    )
    return ORDER_QUANTITY

async def order_quantity_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора количества"""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Заказ отменён.")
        return ConversationHandler.END
    # If user selected 'Другое', prompt for numeric input and stay in the same state
    if query.data == 'qty_other':
        context.user_data['awaiting_order_quantity'] = True
        await query.edit_message_text("Пожалуйста, введите количество (целое число):")
        return ORDER_QUANTITY

    quantity = int(query.data.split('_')[1])
    context.user_data['order_quantity'] = quantity
    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.get)(telegram_chat_id=chat_id)
    product = await sync_to_async(Product.objects.get)(id=context.user_data['order_product_id'])
    total = product.price * quantity
    await query.edit_message_text(
        f"📦 Ваш заказ:\n\n"
        f"Товар: {product.name}\n"
        f"Количество: {quantity} шт.\n"
        f"Сумма: {total}₽\n\n"
        f"Адрес доставки:\n{client.address}\n\n"
        "Подтвердите адрес или измените его:",
        reply_markup=get_address_confirmation_keyboard()
    )
    return ORDER_ADDRESS_CONFIRM


async def order_quantity_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle textual quantity input when user selected 'Другое' (qty_other).

    This accepts a plain text message with an integer quantity, validates it,
    and proceeds to the address confirmation step (ORDER_ADDRESS_CONFIRM).
    """
    qty_text = update.message.text.strip()
    try:
        quantity = int(qty_text)
        if quantity <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('Пожалуйста, введите корректное целое положительное число.')
        return ORDER_QUANTITY

    context.user_data.pop('awaiting_order_quantity', None)
    context.user_data['order_quantity'] = quantity

    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.get)(telegram_chat_id=chat_id)
    product = await sync_to_async(Product.objects.get)(id=context.user_data.get('order_product_id'))
    total = product.price * quantity

    await update.message.reply_text(
        f"📦 Ваш заказ:\n\n"
        f"Товар: {product.name}\n"
        f"Количество: {quantity} шт.\n"
        f"Сумма: {total}₽\n\n"
        f"Адрес доставки:\n{client.address}\n\n"
        "Подтвердите адрес или измените его:",
        reply_markup=get_address_confirmation_keyboard()
    )
    return ORDER_ADDRESS_CONFIRM

async def order_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и создание заказа"""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Заказ отменён.")
        return ConversationHandler.END
    if query.data == "change_address":
        await query.edit_message_text("Введите новый адрес доставки:")
        return ORDER_ADDRESS_CONFIRM
    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.get)(telegram_chat_id=chat_id)
    product = await sync_to_async(Product.objects.get)(id=context.user_data['order_product_id'])
    quantity = context.user_data['order_quantity']
    try:
        driver = None
        if getattr(client, 'region_id', None):
            driver = await sync_to_async(Driver.objects.filter(region_id=client.region_id).first)()
        order = await sync_to_async(Order.objects.create)(
            client=client,
            product=product,
            quantity=quantity,
            delivery_address=client.address,
            total_amount=product.price * quantity,
            payment_amount=product.price * quantity,
            status='planned',
            driver=driver
        )
        await query.edit_message_text(
            f"✅ Заказ #{order.id} успешно создан!\n\n"
            f"Товар: {product.name}\n"
            f"Количество: {quantity} шт.\n"
            f"Сумма: {order.total_amount}₽\n"
            f"Адрес: {order.delivery_address}\n\n"
            "Мы свяжемся с вами в ближайшее время!"
        )
        from .telegram_helpers import notify_admins_new_order, notify_driver_new_order
        await notify_admins_new_order(order)
        if driver:
            await notify_driver_new_order(order)
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        await query.edit_message_text("Произошла ошибка при создании заказа. Пожалуйста, попробуйте позже.")
    return ConversationHandler.END

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы клиента"""
    chat_id = update.effective_chat.id
    client = await sync_to_async(Client.objects.filter(telegram_chat_id=chat_id).first)()
    if not client:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /register")
        return
    orders = await sync_to_async(list)(
        Order.objects.filter(client=client).exclude(status='delivered').select_related('product', 'driver').order_by('-order_date')[:10]
    )
    if not orders:
        await update.message.reply_text("У вас пока нет активных заказов.")
        return
    text = "📦 Ваши заказы:\n\n"
    for order in orders:
        text += f"Заказ #{order.id}\n"
        text += f"Товар: {order.product.name} x{order.quantity}\n"
        text += f"Статус: {order.get_status_display()}\n"
        text += f"Сумма: {order.total_amount}₽\n"
        if order.driver:
            text += f"Водитель: {order.driver.name}\n"
        text += "\n"
    await update.message.reply_text(text)

# ============= DRIVER HANDLERS =============

async def driver_login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало авторизации водителя"""
    await update.message.reply_text(
        "🚗 Авторизация водителя\n\n"
        "Введите код доступа, полученный от администратора:"
    )
    return DRIVER_LOGIN_CODE

async def driver_login_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка кода доступа водителя"""
    code = update.message.text.strip().upper()
    chat_id = update.effective_chat.id
    driver = await sync_to_async(Driver.objects.filter(access_code=code).first)()
    if not driver:
        await update.message.reply_text(
            "❌ Неверный код доступа.\n"
            "Пожалуйста, проверьте код и попробуйте снова."
        )
        return ConversationHandler.END
    is_valid = await sync_to_async(driver.is_access_code_valid)(code)
    if not is_valid:
        await update.message.reply_text(
            "❌ Код доступа истёк.\n"
            "Пожалуйста, запросите новый код у администратора."
        )
        return ConversationHandler.END
    driver.telegram_chat_id = chat_id
    driver.telegram_verified = True
    driver.access_code = None
    await sync_to_async(driver.save)()
    await update.message.reply_text(
        f"✅ Добро пожаловать, {driver.name}!\n\n"
        "Вы успешно авторизованы как водитель.",
        reply_markup=get_driver_main_menu()
    )
    return ConversationHandler.END

async def my_deliveries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы водителя"""
    chat_id = update.effective_chat.id
    driver = await sync_to_async(Driver.objects.filter(telegram_chat_id=chat_id, telegram_verified=True).first)()
    if not driver:
        await update.message.reply_text(
            "Вы не авторизованы как водитель.\n"
            "Используйте /driver_login"
        )
        return
    sort_by = context.user_data.get('sort_by', 'time')
    if sort_by == 'address':
        orders = await sync_to_async(list)(
            Order.objects.filter(driver=driver).exclude(status='delivered').select_related('client', 'product').order_by('delivery_address')
        )
    else:
        orders = await sync_to_async(list)(
            Order.objects.filter(driver=driver).exclude(status='delivered').select_related('client', 'product').order_by('order_date')
        )
    if not orders:
        await update.message.reply_text(
            "У вас пока нет назначенных заказов.",
            reply_markup=get_sort_keyboard()
        )
        return
    for order in orders:
        text = (
            f"📦 Заказ #{order.id} — {order.delivery_address}\n"
            f"📞 {order.client.phone}   Кол-во: {order.quantity}"
        )
        await update.message.reply_text(
            text,
            reply_markup=get_driver_simple_actions(order.id)
        )
    await update.message.reply_text("Выберите сортировку:", reply_markup=get_sort_keyboard())

async def handle_sort_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора сортировки"""
    query = update.callback_query
    await query.answer()
    if query.data == "sort_address":
        context.user_data['sort_by'] = 'address'
        await query.answer("Сортировка по адресу")
    elif query.data == "sort_time":
        context.user_data['sort_by'] = 'time'
        await query.answer("Сортировка по времени")
    await my_deliveries(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END
