from django.test import TestCase
from django.contrib import admin
from crm import admin as crm_admin
from crm import models
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

import asyncio
from unittest.mock import patch, AsyncMock
from crm import bot_handlers


class AdminSiteTests(TestCase):
	def setUp(self):
		# Create minimal objects for tests
		self.region = models.Region.objects.create(name='TestRegion')
		self.product = models.Product.objects.create(name='Water', volume=19.0, price='100.00')
		self.client = models.Client.objects.create(
			name='Client A', phone='+992123456789', email='a@example.com', address='Addr', region=self.region
		)
		self.driver = models.Driver.objects.create(name='Driver A', phone='+992999888776')

	def test_models_registered_in_admin(self):
		# Ensure key models are registered in admin
		registered_models = set(admin.site._registry.keys())
		expected = {
			models.Product,
			models.Client,
			models.Order,
			models.Container,
			models.Driver,
			models.Region,
			models.LoyaltyProgram,
			models.ClientCategory,
			models.LoyaltyTransaction,
			models.Route,
			models.RouteOrder,
			models.Notification,
		}
		missing = [m.__name__ for m in expected if m not in registered_models]
		self.assertFalse(missing, f"Models not registered in admin: {missing}")

	def test_loyalty_transaction_order_link(self):
		# Create an order and a loyalty transaction linked to it
		order = models.Order.objects.create(
			client=self.client, product=self.product, quantity=1, delivery_address='Addr'
		)
		lt = models.LoyaltyTransaction.objects.create(
			client=self.client, points=10, transaction_type='earned', order=order, description='test'
		)
		admin_obj = crm_admin.LoyaltyTransactionAdmin(models.LoyaltyTransaction, admin.site)
		link = admin_obj.order_link(lt)
		# Should contain order id and the anchor tag
		self.assertIn(str(order.id), link)
		self.assertIn('<a', link)

	def test_order_delivery_confirmation_preview_without_file(self):
		order = models.Order.objects.create(
			client=self.client, product=self.product, quantity=1, delivery_address='Addr'
		)
		admin_obj = crm_admin.OrderAdmin(models.Order, admin.site)
		preview = admin_obj.delivery_confirmation_preview(order)
		self.assertEqual(preview, '-')

	def test_driver_active_orders_count(self):
		# Create orders with various statuses
		models.Order.objects.create(client=self.client, product=self.product, quantity=1, status='planned', delivery_address='Addr', driver=self.driver)
		models.Order.objects.create(client=self.client, product=self.product, quantity=1, status='in_progress', delivery_address='Addr', driver=self.driver)
		models.Order.objects.create(client=self.client, product=self.product, quantity=1, status='delivered', delivery_address='Addr', driver=self.driver)
		admin_obj = crm_admin.DriverAdmin(models.Driver, admin.site)
		count = admin_obj.active_orders_count(self.driver)
		self.assertEqual(count, 2)


class AdminRenderingTests(TestCase):
	def setUp(self):
		# Create superuser and login to access admin
		User = get_user_model()
		self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pass')
		self.client = Client()
		self.client.login(username='admin', password='pass')

	def test_order_changelist_renders(self):
		url = reverse('admin:crm_order_changelist')
		resp = self.client.get(url)
		# If template Context copying fails during render this will raise or return 500
		self.assertEqual(resp.status_code, 200)


class BotOrderFlowTests(TestCase):
	def test_bot_order_defaults_to_planned_and_notifies_driver(self):
		# Создаём данные: регион, водитель, клиент, товар
		region = models.Region.objects.create(name="TestRegion")
		driver = models.Driver.objects.create(name="Ivan", phone="+992100000000", region=region)

		client = models.Client.objects.create(
			name="Client1",
			phone="+992199999999",
			address="Test address",
			telegram_chat_id=999999999,
			registration_status='approved',
			region=region,
		)

		product = models.Product.objects.create(name="Water", volume=19.0, price=100.00)

		# Подготавливаем контекст бота: выбран товар и количество
		class FakeCallbackQuery:
			def __init__(self, data):
				self.data = data

			async def answer(self):
				return None

			async def edit_message_text(self, text):
				return None

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

		context = FakeContext(user_data={'order_product_id': product.id, 'order_quantity': 2})
		update = FakeUpdate(chat_id=client.telegram_chat_id, data='confirm')

		# Патчим отправку уведомлений, чтобы не выполнять внешние HTTP-запросы
		with patch('crm.telegram_helpers.notify_admins_new_order', new=AsyncMock()) as mock_admins, \
			 patch('crm.telegram_helpers.notify_driver_new_order', new=AsyncMock()) as mock_driver:

			# Вызываем корутину обработчика
			asyncio.run(bot_handlers.order_confirm(update, context))

			# Проверяем, что создан заказ для клиента
			order = models.Order.objects.filter(client=client).first()
			self.assertIsNotNone(order, "Ожидается создание заказа")

			# Статус должен быть 'planned'
			self.assertEqual(order.status, 'planned')

			# Должен быть назначен водитель из региона
			self.assertIsNotNone(order.driver, "Ожидается назначенный водитель")
			self.assertEqual(order.driver.id, driver.id)

			# Проверяем, что уведомления были вызваны
			mock_admins.assert_awaited()
			mock_driver.assert_awaited()
