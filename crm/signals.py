import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Order
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance: Order, **kwargs):
    """Store old status and driver on instance for comparison in post_save."""
    if not instance.pk:
        instance._old_status = None
        instance._old_driver = None
        return
    try:
        old = Order.objects.only('status', 'driver').get(pk=instance.pk)
        instance._old_status = old.status
        instance._old_driver = old.driver
    except Order.DoesNotExist:
        instance._old_status = None
        instance._old_driver = None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created, **kwargs):
    """Send notifications when order is created, status changes, or driver is assigned."""
    try:
        # Notify client on order creation
        if created:
            client = instance.client
            chat_id = getattr(client, 'telegram_chat_id', None)
            if chat_id:
                text = (
                    f'✅ Ваш заказ #{instance.id} принят!\n\n'
                    f'Товар: {instance.product.name} x{instance.quantity}\n'
                    f'Сумма: {instance.total_amount}₽\n'
                    f'Адрес: {instance.delivery_address}\n\n'
                    f'Мы свяжемся с вами в ближайшее время.'
                )
                try:
                    from .telegram_helpers import send_notification
                    sent = send_notification(chat_id, text)
                    if not sent:
                        logger.warning('Failed to send order creation notification for order %s to chat %s', instance.id, chat_id)
                except Exception:
                    logger.exception('Failed to send order creation notification for order %s', instance.id)
            return
        
        # Notify on status change
        old_status = getattr(instance, '_old_status', None)
        new_status = instance.status
        if old_status != new_status:
            client = instance.client
            chat_id = getattr(client, 'telegram_chat_id', None)
            if chat_id:
                text = f'Статус вашего заказа #{instance.id} изменён: {instance.get_status_display()}'
                if instance.driver:
                    text += f'\nВодитель: {instance.driver.name}'
                try:
                    from .telegram_helpers import send_notification
                    sent = send_notification(chat_id, text)
                    if not sent:
                        logger.warning('Failed to send status change notification for order %s to chat %s', instance.id, chat_id)
                except Exception:
                    logger.exception('Failed to send status change notification for order %s', instance.id)
        
        # Notify driver when assigned (send buttons for per-order actions)
        old_driver = getattr(instance, '_old_driver', None)
        new_driver = instance.driver
        if old_driver != new_driver and new_driver:
            try:
                from .telegram_helpers import notify_driver_new_order
                async_to_sync(notify_driver_new_order)(instance)
            except Exception:
                logger.exception('Failed to send driver assignment notification for order %s', instance.id)
    except Exception:
        logger.exception('Error in order_post_save signal')
