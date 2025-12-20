
# ============= TELEGRAM BOT INTEGRATION VIEWS =============

@login_required
@permission_required('crm.change_client', raise_exception=True)
def approve_client_registration(request, client_id):
    """Подтверждение регистрации клиента из Telegram"""
    client = get_object_or_404(Client, id=client_id)
    
    if client.registration_status == 'pending':
        client.registration_status = 'approved'
        client.save()
        
        # Отправляем уведомление клиенту в Telegram
        if client.telegram_chat_id:
            from .telegram_helpers import send_notification
                send_notification(
                    client.telegram_chat_id,
                    f"✅ Ваша регистрация подтверждена!\n\n"
                    f"Теперь вы можете делать заказы через бота. Нажав на /start"
                )
        
        messages.success(request, f"Регистрация клиента {client.name} подтверждена!")
    else:
        messages.warning(request, f"Клиент {client.name} уже обработан (статус: {client.get_registration_status_display()})")
    
    return redirect('clients')


@login_required
@permission_required('crm.change_client', raise_exception=True)
def reject_client_registration(request, client_id):
    """Отклонение регистрации клиента из Telegram"""
    client = get_object_or_404(Client, id=client_id)
    
    if client.registration_status == 'pending':
        client.registration_status = 'rejected'
        client.save()
        
        # Отправляем уведомление клиенту в Telegram
        if client.telegram_chat_id:
            from .telegram_helpers import send_notification
            send_notification(
                client.telegram_chat_id,
                f"❌ К сожалению, ваша регистрация была отклонена.\n\n"
                f"Пожалуйста, свяжитесь с администратором для уточнения деталей."
            )
        
        messages.success(request, f"Регистрация клиента {client.name} отклонена.")
    else:
        messages.warning(request, f"Клиент {client.name} уже обработан (статус: {client.get_registration_status_display()})")
    
    return redirect('clients')


@login_required
@permission_required('crm.change_driver', raise_exception=True)
def generate_driver_access_code(request, driver_id):
    """Генерация кода доступа для водителя"""
    driver = get_object_or_404(Driver, id=driver_id)
    
    # Генерируем код доступа
    code = driver.generate_access_code()
    driver.save()
    
    # Формируем сообщение для отображения
    expiry_hours = getattr(settings, 'DRIVER_CODE_EXPIRY_HOURS', 24)
    messages.success(
        request,
        f"Код доступа для водителя {driver.name}: <strong>{code}</strong><br>"
        f"Действителен {expiry_hours} часов.<br>"
        f"Водитель должен использовать /driver_login в Telegram боте."
    )
    
    return redirect('drivers')
