from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from ..models import Client, Driver
from django.conf import settings


@login_required
@permission_required('crm.change_client', raise_exception=True)
def approve_client_registration(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    
    if client.registration_status == 'pending':
        client.registration_status = 'approved'
        client.save()
        
        if client.telegram_chat_id:
            from ..telegram_helpers import send_notification
            send_notification(
                client.telegram_chat_id,
                f"✅ Ваша регистрация подтверждена!\n\nТеперь вы можете делать заказы через бота."
            )
        
        messages.success(request, f"Регистрация клиента {client.name} подтверждена!")
    else:
        messages.warning(request, f"Клиент {client.name} уже обработан (статус: {client.get_registration_status_display()})")
    
    return redirect('clients')


@login_required
@permission_required('crm.change_client', raise_exception=True)
def reject_client_registration(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    
    if client.registration_status == 'pending':
        client.registration_status = 'rejected'
        client.save()
        
        if client.telegram_chat_id:
            from ..telegram_helpers import send_notification
            send_notification(
                client.telegram_chat_id,
                f"❌ К сожалению, ваша регистрация была отклонена."
            )
        
        messages.success(request, f"Регистрация клиента {client.name} отклонена.")
    else:
        messages.warning(request, f"Клиент {client.name} уже обработан (статус: {client.get_registration_status_display()})")
    
    return redirect('clients')


@login_required
@permission_required('crm.change_driver', raise_exception=True)
def generate_driver_access_code(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    code = driver.generate_access_code()
    driver.save()
    expiry_hours = getattr(settings, 'DRIVER_CODE_EXPIRY_HOURS', 24)
    messages.success(
        request,
        f"Код доступа для водителя {driver.name}: <strong>{code}</strong><br>Действителен {expiry_hours} часов."
    )
    return redirect('drivers')
