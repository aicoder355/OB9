from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q

from ..models import Notification, Client


@login_required
def notifications_list(request):
    if request.user.is_staff:
        notifications = Notification.objects.all()
    elif hasattr(request.user, 'driver_profile'):
        notifications = Notification.objects.filter(
            Q(client__in=Client.objects.filter(region__driver=request.user.driver_profile)) |
            Q(order__driver=request.user.driver_profile)
        )
    else:
        try:
            client = Client.objects.get(user=request.user)
            notifications = Notification.objects.filter(client=client)
        except Client.DoesNotExist:
            notifications = Notification.objects.none()

    notifications = notifications.select_related('client').order_by('-created_at')

    return render(request, 'notifications.html', {
        'notifications': notifications
    })


@login_required
def mark_notification_read(request, notification_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        if request.user.is_staff:
            notification = Notification.objects.get(id=notification_id)
        elif hasattr(request.user, 'driver_profile'):
            driver_clients = Client.objects.filter(region__driver=request.user.driver_profile)
            notification = Notification.objects.filter(
                id=notification_id
            ).filter(
                Q(client__in=driver_clients) |
                Q(order__driver=request.user.driver_profile)
            ).first()
            if not notification:
                raise Notification.DoesNotExist()
        else:
            client = Client.objects.get(user=request.user)
            notification = Notification.objects.get(id=notification_id, client=client)

        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
        
    except (Notification.DoesNotExist, Client.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
