from django.test import TestCase
from unittest.mock import patch, AsyncMock
from asgiref.sync import async_to_sync

from crm import telegram_bot
from crm import models


class SimpleOrderFlowTests(TestCase):
    def test_qty_button_then_confirm_creates_planned_order_and_notifies(self):
        # Setup data
        region = models.Region.objects.create(name='RegionX')
        driver = models.Driver.objects.create(name='DriverX', phone='+992700000000', region=region)

        client = models.Client.objects.create(
            name='ClientX',
            phone='+992711111111',
            address='AddrX',
            telegram_chat_id=123456789,
            registration_status='approved',
            region=region,
        )

        product = models.Product.objects.create(name='Water', volume=19.0, price=150.00)

        # Fake update/context objects
        class FakeCallbackQuery:
            def __init__(self, data):
                self.data = data

            async def answer(self, *args, **kwargs):
                return None

            async def edit_message_text(self, *args, **kwargs):
                return None

        class FakeChat:
            def __init__(self, chat_id):
                self.id = chat_id

        class FakeUpdate:
            def __init__(self, chat_id, data):
                self.callback_query = FakeCallbackQuery(data)
                self.effective_chat = FakeChat(chat_id)
                self.effective_user = type('U', (), {'id': chat_id})

        class FakeContext:
            def __init__(self):
                self.user_data = {}

        ctx = FakeContext()

        # Patch notifications
        with patch('crm.telegram_helpers.notify_admins_new_order', new=AsyncMock()) as mock_admins, \
                patch('crm.telegram_helpers.notify_driver_new_order', new=AsyncMock()) as mock_driver:

            # 1) User presses qty button (e.g., qty_2)
            upd_qty = FakeUpdate(client.telegram_chat_id, 'qty_2')
            async_to_sync(telegram_bot.handle_callback_query)(upd_qty, ctx)

            # After qty selection, confirmation keyboard should be shown (we don't inspect message here)

            # 2) User presses confirm button -> simple_confirm_2
            upd_confirm = FakeUpdate(client.telegram_chat_id, 'simple_confirm_2')
            async_to_sync(telegram_bot.handle_callback_query)(upd_confirm, ctx)

            # Verify order created
            order = models.Order.objects.filter(client=client).first()
            self.assertIsNotNone(order, 'Order should be created')
            self.assertEqual(order.status, 'planned')

            # Driver should be assigned from region
            self.assertIsNotNone(order.driver, 'Driver should be assigned')
            self.assertEqual(order.driver.id, driver.id)

            # Notifications called
            mock_admins.assert_awaited()
            mock_driver.assert_awaited()
