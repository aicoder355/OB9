from unittest.mock import patch, AsyncMock
from asgiref.sync import async_to_sync

from django.test import TestCase

from crm.models import Region, Driver, Client, Product, Order
from crm import bot_handlers


class FakeCallbackQuery:
    def __init__(self, data):
        self.data = data
        self.edited_text = None

    async def answer(self):
        return None

    async def edit_message_text(self, text):
        self.edited_text = text


class FakeChat:
    def __init__(self, chat_id):
        self.id = chat_id


class FakeUpdate:
    def __init__(self, chat_id, data="confirm"):
        self.callback_query = FakeCallbackQuery(data)
        self.effective_chat = FakeChat(chat_id)


class FakeContext:
    def __init__(self, user_data):
        self.user_data = user_data


class BotOrderFlowTests(TestCase):
    def test_bot_order_defaults_to_planned_and_notifies_driver(self):
        # Создаём данные: регион, водитель, клиент, товар
        region = Region.objects.create(name="TestRegion")
        driver = Driver.objects.create(name="Ivan", phone="+992100000000", region=region)

        client = Client.objects.create(
            name="Client1",
            phone="+992199999999",
            address="Test address",
            telegram_chat_id=999999999,
            registration_status='approved',
            region=region,
        )

        product = Product.objects.create(name="Water", volume=19.0, price=100.00)

        # Подготавливаем контекст бота: выбран товар и количество
        context = FakeContext(user_data={"order_product_id": product.id, "order_quantity": 2})
        update = FakeUpdate(chat_id=client.telegram_chat_id, data="confirm")

        # Патчим отправку уведомлений, чтобы не выполнять внешние HTTP-запросы
        with patch(
            "crm.telegram_helpers.notify_admins_new_order",
            new=AsyncMock(),
        ) as mock_admins, patch(
            "crm.telegram_helpers.notify_driver_new_order",
            new=AsyncMock(),
        ) as mock_driver, patch(
            "crm.telegram_helpers.send_notification",
            return_value=True,
        ) as mock_send:

            # Вызываем корутину обработчика синхронно (без создания нового event loop),
            # чтобы избежать блокировок БД в тестовой транзакции
            async_to_sync(bot_handlers.order_confirm)(update, context)

            # Проверяем, что создан заказ для клиента
            order = Order.objects.filter(client=client).first()
            self.assertIsNotNone(order, "Ожидается создание заказа")

            # Статус должен быть 'planned'
            self.assertEqual(order.status, "planned")

            # Должен быть назначен водитель из региона
            self.assertIsNotNone(order.driver, "Ожидается назначенный водитель")
            self.assertEqual(order.driver.id, driver.id)

            # Проверяем, что уведомления были вызваны
            mock_admins.assert_awaited()
            mock_driver.assert_awaited()
