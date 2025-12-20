from django.test import TestCase
from unittest.mock import patch
from asgiref.sync import async_to_sync

from crm import telegram_bot
from crm.models import Region, Driver, Client, Product, Order


class SyncToAsyncLocalTest(TestCase):
    def test_handle_callback_query_status_does_not_raise_unboundlocal(self):
        # Setup minimal objects
        region = Region.objects.create(name='TestRegion')
        driver = Driver.objects.create(name='DriverTest', phone='+992700000000', region=region)
        # Assign telegram_chat_id so pressing_driver lookup succeeds
        driver.telegram_chat_id = 555666777
        driver.save()

        client = Client.objects.create(
            name='ClientTest',
            phone='+992711111111',
            address='AddrTest',
            telegram_chat_id=111222333,
            registration_status='approved',
            region=region,
        )

        product = Product.objects.create(name='Water', volume=19.0, price=100.00)

        order = Order.objects.create(
            client=client,
            product=product,
            quantity=1,
            status='planned',
            driver=driver,
            delivery_address=client.address,
        )

        # Build fake update/context matching handler expectations
        class FakeCallbackQuery:
            def __init__(self, data):
                self.data = data

            async def answer(self, *args, **kwargs):
                return None

            async def edit_message_text(self, *args, **kwargs):
                return None

        class FakeUser:
            def __init__(self, id):
                self.id = id

        class FakeChat:
            def __init__(self, id):
                self.id = id

        class FakeUpdate:
            def __init__(self, chat_id, user_id, data):
                self.callback_query = FakeCallbackQuery(data)
                self.effective_user = FakeUser(user_id)
                self.effective_chat = FakeChat(chat_id)

        class FakeContext:
            def __init__(self):
                self.user_data = {}

        # Use the driver's telegram_chat_id as the pressing user id
        # Use a single-token status (e.g. 'delivered') to avoid multi-part parsing in handler
        upd = FakeUpdate(chat_id=driver.telegram_chat_id, user_id=driver.telegram_chat_id, data=f'status_{order.id}_delivered')
        ctx = FakeContext()

        # Patch send_notification to avoid external calls
        with patch('crm.telegram_bot.send_notification', return_value=None) as mock_send:
            # Call the async handler synchronously; previously this path raised UnboundLocalError
            async_to_sync(telegram_bot.handle_callback_query)(upd, ctx)

        # Refresh and assert status changed to delivered
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
