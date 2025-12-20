from .models import Notification

class NotificationService:
    @staticmethod
    def create_notification(client, notification_type, title, message):
        return Notification.objects.create(
            client=client,
            notification_type=notification_type,
            title=title,
            message=message
        )
    

