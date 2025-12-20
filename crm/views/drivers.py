from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from ..models import Order, Container


@login_required
def driver_dashboard(request):
    """
    Личный кабинет водителя: показывает только заказы, назначенные этому водителю.
    """
    # Проверяем связь с Driver через user
    driver = getattr(request.user, 'driver_profile', None)
    if not driver:
        messages.error(request, 'Вы не являетесь водителем.')
        return redirect('dashboard')
    
    # Получаем фильтр по статусу из GET параметров
    status_filter = request.GET.get('status', 'active')
    
    # Базовый queryset - все заказы водителя
    orders = Order.objects.filter(driver=driver).select_related('client', 'product')
    
    # Применяем фильтр по статусу
    if status_filter == 'new':
        orders = orders.filter(status='new')
    elif status_filter == 'planned':
        orders = orders.filter(status='planned')
    elif status_filter == 'in_progress':
        orders = orders.filter(status='in_progress')
    elif status_filter == 'delivered':
        orders = orders.filter(status='delivered')
    elif status_filter == 'canceled':
        orders = orders.filter(status='canceled')
    elif status_filter == 'active':
        # Активные заказы - все кроме доставленных и отмененных
        orders = orders.exclude(status__in=['delivered', 'canceled'])
    
    orders = orders.order_by('-order_date')
    
    # Подсчет заказов по статусам
    all_orders = Order.objects.filter(driver=driver)
    order_counts = {
        'all': all_orders.count(),
        'active': all_orders.exclude(status__in=['delivered', 'canceled']).count(),
        'new': all_orders.filter(status='new').count(),
        'planned': all_orders.filter(status='planned').count(),
        'in_progress': all_orders.filter(status='in_progress').count(),
        'delivered': all_orders.filter(status='delivered').count(),
        'canceled': all_orders.filter(status='canceled').count(),
    }
    
    return render(request, 'driver_dashboard.html', {
        'orders': orders,
        'status_filter': status_filter,
        'order_counts': order_counts,
        'driver': driver,
    })



@login_required
def driver_update_order(request, order_id):
    """
    API endpoint для обновления заказа водителем.
    Позволяет изменять статус, добавлять комментарий и загружать фото.
    """
    # Проверяем, что пользователь является водителем
    driver = getattr(request.user, 'driver_profile', None)
    if not driver:
        return JsonResponse({'success': False, 'error': 'Вы не являетесь водителем.'}, status=403)
    
    # Получаем заказ
    try:
        order = Order.objects.get(id=order_id, driver=driver)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Заказ не найден или не назначен вам.'}, status=404)
    
    if request.method == 'POST':
        # Обновляем статус, если передан
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            
            # Если статус изменился на "доставлен", записываем время доставки
            if new_status == 'delivered' and old_status != 'delivered':
                order.actual_delivery_time = timezone.now()
                
                # Проверяем наличие тары на складе
                if not Container.check_warehouse_stock(order.product, order.quantity):
                    return JsonResponse({
                        'success': False, 
                        'error': f'Недостаточно тары ({order.product.name}) на складе для доставки.'
                    }, status=400)
                
                # Создаём тару для клиента
                Container.objects.create(
                    product=order.product,
                    client=order.client,
                    quantity=order.quantity,
                    is_at_client=True
                )
                
                # Уменьшаем тару на складе
                warehouse_container = Container.objects.filter(
                    product=order.product, is_at_client=False
                ).first()
                if warehouse_container:
                    warehouse_container.quantity -= order.quantity
                    if warehouse_container.quantity <= 0:
                        warehouse_container.delete()
                    else:
                        warehouse_container.save()
        
        # Обновляем комментарий водителя, если передан
        driver_comment = request.POST.get('driver_comment')
        if driver_comment is not None:
            order.driver_comment = driver_comment
        
        # Обрабатываем загрузку фото
        if 'delivery_confirmation' in request.FILES:
            order.delivery_confirmation = request.FILES['delivery_confirmation']
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Заказ успешно обновлен',
            'order': {
                'id': order.id,
                'status': order.status,
                'status_display': order.get_status_display(),
                'driver_comment': order.driver_comment,
                'has_photo': bool(order.delivery_confirmation),
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)
