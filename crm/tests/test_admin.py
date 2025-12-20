from django.test import TestCase
from django.contrib import admin
from django.urls import reverse
from crm import admin as crm_admin
from crm import models


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
