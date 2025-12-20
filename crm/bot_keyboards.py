"""
Telegram bot keyboards and inline buttons
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def get_client_main_menu():
    """Главное меню для клиента"""
    keyboard = [
        [KeyboardButton("📋 Каталог товаров"), KeyboardButton("🛒 Сделать заказ")],
        [KeyboardButton("📦 Мои заказы"), KeyboardButton("ℹ️ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_driver_main_menu():
    """Главное меню для водителя"""
    keyboard = [
        [KeyboardButton("📋 Мои доставки"), KeyboardButton("🔄 Обновить")],
        [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🚪 Выход")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_products_keyboard(products):
    """Inline клавиатура с товарами"""
    keyboard = []
    for product in products:
        button_text = f"{product.name} - {product.price}₽"
        callback_data = f"product_{product.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def get_quantity_keyboard():
    """Inline клавиатура для выбора количества"""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="qty_1"),
            InlineKeyboardButton("2", callback_data="qty_2"),
            InlineKeyboardButton("3", callback_data="qty_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="qty_4"),
            InlineKeyboardButton("5", callback_data="qty_5"),
            InlineKeyboardButton("10", callback_data="qty_10"),
        ],
        [InlineKeyboardButton("✏️ Другое", callback_data="qty_other")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_actions_keyboard(order_id, is_driver=False):
    """Inline клавиатура с действиями для заказа"""
    if is_driver:
        keyboard = [
            [InlineKeyboardButton("🚗 В пути", callback_data=f"status_{order_id}_in_progress")],
            [InlineKeyboardButton("✅ Доставлен", callback_data=f"status_{order_id}_delivered")],
            [InlineKeyboardButton("❌ Отменён", callback_data=f"status_{order_id}_canceled")],
            [InlineKeyboardButton("📝 Добавить комментарий", callback_data=f"comment_{order_id}")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("ℹ️ Подробнее", callback_data=f"details_{order_id}")],
            [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")],
        ]
    
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action, item_id):
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_address_confirmation_keyboard():
    """Клавиатура для подтверждения адреса"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить адрес", callback_data="confirm_address")],
        [InlineKeyboardButton("✏️ Изменить адрес", callback_data="change_address")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sort_keyboard():
    """Клавиатура для выбора сортировки заказов водителя"""
    keyboard = [
        [
            InlineKeyboardButton("🔤 По адресу", callback_data="sort_address"),
            InlineKeyboardButton("🕐 По времени", callback_data="sort_time"),
        ],
        [InlineKeyboardButton("❌ Закрыть", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard():
    """Простая клавиатура отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


def get_driver_simple_actions(order_id):
    """Compact inline keyboard for drivers: Deliver and Cancel"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Доставить", callback_data=f"confirm_deliver_{order_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"confirm_cancel_{order_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
