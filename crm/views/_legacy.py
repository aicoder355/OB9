from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count, Max
from django.db.models.functions import TruncDay, TruncMonth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_protect, csrf_exempt

import csv
from datetime import timedelta
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ..models import Client, Order, Product, Container, Driver, Region, Route, RouteOrder, ClientCategory, LoyaltyTransaction, Notification, LoyaltyProgram
from ..serializers import ClientSerializer, OrderSerializer, ContainerSerializer, DriverSerializer, RegionSerializer
from io import BytesIO
from datetime import datetime
from django.utils.timezone import make_aware

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'form': {'errors': True}})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    today = timezone.now().date()
    orders = Order.objects.filter(order_date__date=today)
    today_orders = orders.count()
    total_clients = Client.objects.count()
    delivered_bottles = sum(order.quantity for order in orders.filter(status='delivered'))
    today_revenue = sum(order.quantity * order.product.price for order in orders.filter(status='delivered'))
    
    total_containers = Container.objects.aggregate(total=Sum('quantity'))['total'] or 0
    containers_at_clients = Container.objects.filter(is_at_client=True).aggregate(total=Sum('quantity'))['total'] or 0
    containers_at_warehouse = total_containers - containers_at_clients

    # Проверка низкого уровня тары
    low_stock_products = Container.get_low_stock_products()
    if low_stock_products:
        low_stock_message = "Низкий уровень тары на складе: "
        low_stock_message += ", ".join([f"{p[0].name} ({p[1]} шт.)" for p in low_stock_products])
        messages.warning(request, low_stock_message)

    # Проверка просроченных заказов
    overdue_orders = Order.objects.filter(status='planned', order_date__lt=timezone.now() - timedelta(days=2))
    for order in overdue_orders:
        subject = 'Напоминание: Просроченный заказ'
        message = f'Заказ #{order.id} для клиента {order.client.name} просрочен. Статус: {order.get_status_display()}. Действия требуются.'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],  # Отправка админу
            fail_silently=True,
        )
        messages.warning(request, f'Отправлено напоминание об просроченном заказе #{order.id}.')

    # Данные для графика заказов по дням (последние 7 дней)
    end_date = today
    start_date = end_date - timedelta(days=6)  # 7 дней, включая сегодня
    orders_by_day = (Order.objects
                     .filter(order_date__date__range=[start_date, end_date])
                     .annotate(day=TruncDay('order_date'))
                     .values('day')
                     .annotate(count=Count('id'))
                     .order_by('day'))
    
    orders_by_day_data = {entry['day'].strftime('%d.%m.%Y'): entry['count'] for entry in orders_by_day}
    days = [(start_date + timedelta(days=x)).strftime('%d.%m.%Y') for x in range(7)]
    orders_by_day_counts = [orders_by_day_data.get(day, 0) for day in days]

    # Данные для графика выручки по месяцам (последние 6 месяцев)
    end_month = today.replace(day=1)  # Начало текущего месяца
    start_month = (end_month - timedelta(days=150)).replace(day=1)  # Примерно 5 месяцев назад + текущий
    revenue_by_month = (Order.objects
                        .filter(order_date__date__range=[start_month, end_month], status='delivered')
                        .annotate(month=TruncMonth('order_date'))
                        .values('month')
                        .annotate(revenue=Sum('quantity') * Sum('product__price'))
                        .order_by('month'))
    
    revenue_by_month_data = {entry['month'].strftime('%m.%Y'): entry['revenue'] or 0 for entry in revenue_by_month}
    months = []
    current_month = start_month
    while current_month <= end_month:
        months.append(current_month.strftime('%m.%Y'))
        next_month = current_month.month + 1 if current_month.month < 12 else 1
        next_year = current_month.year if current_month.month < 12 else current_month.year + 1
        current_month = current_month.replace(month=next_month, year=next_year)
    revenue_by_month_values = [revenue_by_month_data.get(month, 0) for month in months]

    return render(request, 'dashboard.html', {
        'orders': orders,
        'today_orders': today_orders,
        'total_clients': total_clients,
        'delivered_bottles': delivered_bottles,
        'today_revenue': today_revenue,
        'total_containers': total_containers,
        'containers_at_clients': containers_at_clients,
        'containers_at_warehouse': containers_at_warehouse,
        'low_stock_products': low_stock_products,
        'orders_by_day_labels': days,
        'orders_by_day_data': orders_by_day_counts,
        'revenue_by_month_labels': months,
        'revenue_by_month_data': revenue_by_month_values,
    })

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
def orders(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    orders = Order.objects.all().order_by('-order_date')
    
    if search_query:
        orders = orders.filter(client__name__icontains=search_query)
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'orders.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'clients': Client.objects.all(),
        'products': Product.objects.all(),
        'can_add_order': request.user.has_perm('crm.add_order'),
        'can_change_order': request.user.has_perm('crm.change_order'),
        'can_delete_order': request.user.has_perm('crm.delete_order'),
    })

@login_required
@permission_required('crm.add_order', raise_exception=True)
def create_order(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        status = request.POST.get('status')

        # Поиск клиента по номеру телефона
        client = Client.objects.filter(phone=phone).first()
        if not client:
            messages.error(request, f"Клиент с номером телефона {phone} не найден.")
            return redirect('orders')

        product = Product.objects.get(id=product_id)

        # Автоматическое заполнение адреса доставки
        delivery_address = f"{client.address}, {client.apartment or ''}, {client.floor or ''} этаж, {client.entrance or ''}".strip().replace(', ,', ',').replace(' ,', '')

        # Автоматическое прикрепление водителя по региону клиента
        driver = None
        if client.region and client.region.driver_set.exists():
            driver = client.region.driver_set.first()

        if status == 'delivered':
            if not Container.check_warehouse_stock(product, quantity):
                messages.error(request, f"Недостаточно тары ({product.name}) на складе для доставки.")
                return redirect('orders')

        order = Order.objects.create(
            client=client,
            product=product,
            quantity=quantity,
            status=status,
            delivery_address=delivery_address,
            driver=driver
        )

        if status == 'delivered':
            Container.objects.create(
                product=product,
                client=client,
                quantity=quantity,
                is_at_client=True
            )

            warehouse_container = Container.objects.filter(
                product=product, is_at_client=False
            ).first()
            if warehouse_container:
                warehouse_container.quantity -= quantity
                if warehouse_container.quantity <= 0:
                    warehouse_container.delete()
                else:
                    warehouse_container.save()

            # Отправка email клиенту
            subject = 'Ваш заказ доставлен'
            message = f'Уважаемый {order.client.name},\n\nВаш заказ #{order.id} успешно доставлен.\nДетали:\n- Продукт: {product.name}\n- Количество: {quantity}\n- Адрес: {delivery_address}\n- Водитель: {driver.name if driver else "Не назначен"}\n\nСпасибо за покупку!\nКоманда {settings.DEFAULT_FROM_EMAIL}'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [order.client.email],
                fail_silently=True,
            )
            messages.success(request, f"Заказ создан, тара ({quantity} x {product.name}) отправлена клиенту. Email отправлен.")

        else:
            messages.success(request, "Заказ создан.")

        return redirect('orders')
    return render(request, 'orders.html', {
        'clients': Client.objects.all(),
        'products': Product.objects.all(),
    })

@login_required
@permission_required('crm.change_order', raise_exception=True)
def edit_order(request):
    if request.method == 'POST':
        order = Order.objects.get(id=request.POST.get('order_id'))
        old_status = order.status  # Сохраняем старый статус для сравнения
        phone = request.POST.get('phone')
        product_id = request.POST.get('product')
        new_quantity = int(request.POST.get('quantity'))
        new_status = request.POST.get('status')

        # Поиск клиента по номеру телефона
        client = Client.objects.filter(phone=phone).first()
        if not client:
            messages.error(request, f"Клиент с номером телефона {phone} не найден.")
            return redirect('orders')

        product = Product.objects.get(id=product_id)

        # Автоматическое заполнение адреса доставки
        delivery_address = f"{client.address}, {client.apartment or ''}, {client.floor or ''} этаж, {client.entrance or ''}".strip().replace(', ,', ',').replace(' ,', '')

        # Автоматическое прикрепление водителя по региону клиента
        driver = None
        if client.region and client.region.driver_set.exists():
            driver = client.region.driver_set.first()

        # Если статус меняется на "Доставлен"
        if new_status == 'delivered' and old_status != 'delivered':
            if not Container.check_warehouse_stock(product, new_quantity):
                messages.error(request, f"Недостаточно тары ({product.name}) на складе для доставки.")
                return redirect('orders')

            # Создаём тару для клиента
            Container.objects.create(
                product=product,
                client=client,
                quantity=new_quantity,
                is_at_client=True
            )

            # Уменьшаем тару на складе
            warehouse_container = Container.objects.filter(
                product=product, is_at_client=False
            ).first()
            if warehouse_container:
                warehouse_container.quantity -= new_quantity
                if warehouse_container.quantity <= 0:
                    warehouse_container.delete()
                else:
                    warehouse_container.save()

            # Отправка email клиенту
            subject = 'Ваш заказ доставлен'
            message = f'Уважаемый {client.name},\n\nВаш заказ #{order.id} успешно доставлен.\nДетали:\n- Продукт: {product.name}\n- Количество: {new_quantity}\n- Адрес: {delivery_address}\n- Водитель: {driver.name if driver else "Не назначен"}\n\nСпасибо за покупку!\nКоманда {settings.DEFAULT_FROM_EMAIL}'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [client.email],
                fail_silently=True,
            )
            messages.success(request, f"Заказ обновлён, тара ({new_quantity} x {product.name}) отправлена клиенту. Email отправлен.")

        # Если статус меняется на "Отменён" и ранее был "Доставлен"
        elif new_status == 'canceled' and old_status == 'delivered':
            container = Container.objects.filter(
                product=product, client=client, is_at_client=True
            ).first()
            if container:
                container.is_at_client = False
                container.client_id = None
                container.save()

                # Добавляем тару обратно на склад
                warehouse_container = Container.objects.filter(
                    product=product, is_at_client=False
                ).first()
                if warehouse_container:
                    warehouse_container.quantity += container.quantity
                    warehouse_container.save()
                else:
                    Container.objects.create(
                        product=product,
                        quantity=container.quantity,
                        is_at_client=False
                    )
                messages.success(request, f"Заказ отменён, тара ({container.quantity} x {product.name}) возвращена на склад.")

        else:
            messages.success(request, "Заказ обновлён.")

        order.client = client
        order.product = product
        order.quantity = new_quantity
        order.status = new_status
        order.delivery_address = delivery_address
        order.driver = driver
        order.save()
        return redirect('orders')
    return redirect('orders')

@login_required
@permission_required('crm.delete_order', raise_exception=True)
def delete_order(request, order_id):
    order = Order.objects.get(id=order_id)
    order.delete()
    messages.success(request, "Заказ удалён.")
    return redirect('orders')

@login_required
def drivers(request):
    drivers_list = Driver.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        drivers_list = drivers_list.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    paginator = Paginator(drivers_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'drivers.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'can_add_driver': request.user.has_perm('crm.add_driver'),
        'can_change_driver': request.user.has_perm('crm.change_driver'),
        'can_delete_driver': request.user.has_perm('crm.delete_driver'),
        'regions': Region.objects.all(),  # Убедись, что эта строка есть
    })

@login_required
@permission_required('crm.add_driver', raise_exception=True)
def create_driver(request):
    if request.method == 'POST':
        Driver.objects.create(
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email', ''),
            license_number=request.POST.get('license_number'),
            region_id=request.POST.get('region'),
            created_at=timezone.now()
        )
        messages.success(request, "Водитель добавлен.")
        return redirect('drivers')
    return render(request, 'drivers.html', {
        'regions': Region.objects.all(),
    })

@login_required
@permission_required('crm.change_driver', raise_exception=True)
def edit_driver(request):
    if request.method == 'POST':
        driver = Driver.objects.get(id=request.POST.get('driver_id'))
        driver.name = request.POST.get('name')
        driver.phone = request.POST.get('phone')
        driver.email = request.POST.get('email', '')
        driver.license_number = request.POST.get('license_number')
        driver.region_id = request.POST.get('region')
        driver.save()
        messages.success(request, "Водитель обновлён.")
        return redirect('drivers')
    return redirect('drivers')

@login_required
@permission_required('crm.delete_driver', raise_exception=True)
def delete_driver(request, driver_id):
    driver = Driver.objects.get(id=driver_id)
    driver.delete()
    messages.success(request, "Водитель удалён.")
    return redirect('drivers')

@login_required
def regions(request):
    search_query = request.GET.get('search', '')
    
    regions = Region.objects.prefetch_related('client_set').all().order_by('id')
    
    if search_query:
        regions = regions.filter(name__icontains=search_query)
    
    paginator = Paginator(regions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'regions.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'can_add_region': request.user.has_perm('crm.add_region'),
        'can_change_region': request.user.has_perm('crm.change_region'),
        'can_delete_region': request.user.has_perm('crm.delete_region'),
        'clients': Client.objects.all(),  # Добавляем список всех клиентов
        'regions': Region.objects.all(),  # Для формы добавления клиента
    })

@login_required
@permission_required('crm.add_region', raise_exception=True)
def create_region(request):
    if request.method == 'POST':
        Region.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            created_at=timezone.now()
        )
        messages.success(request, "Регион добавлен.")
        return redirect('regions')
    return redirect('regions')

@login_required
@permission_required('crm.change_region', raise_exception=True)
def edit_region(request):
    if request.method == 'POST':
        region = Region.objects.get(id=request.POST.get('region_id'))
        region.name = request.POST.get('name')
        region.description = request.POST.get('description', '')
        region.save()
        messages.success(request, "Регион обновлён.")
        return redirect('regions')
    return redirect('regions')

@login_required
@permission_required('crm.delete_region', raise_exception=True)
def delete_region(request, region_id):
    region = Region.objects.get(id=region_id)
    region.delete()
    messages.success(request, "Регион удалён.")
    return redirect('regions')

@login_required
def clients(request):
    search_query = request.GET.get('search', '')
    
    clients = Client.objects.select_related('region', 'category').all()
    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(tax_number__icontains=search_query)
        )
    
    # Добавляем агрегацию по заказам
    clients = clients.annotate(
        orders_count=Count('order'),
        total_orders_volume=Sum('order__quantity'),
        last_order_date=Max('order__order_date')
    ).order_by('-last_order_date', 'name')
    
    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'clients.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'regions': Region.objects.all(),
        'categories': ClientCategory.objects.all(),
        'can_add_client': request.user.has_perm('crm.add_client'),
        'can_change_client': request.user.has_perm('crm.change_client'),
        'can_delete_client': request.user.has_perm('crm.delete_client'),
    })

@login_required
@permission_required('crm.add_client', raise_exception=True)
def create_client(request):
    if request.method == 'POST':
        client_type = request.POST.get('client_type', 'individual')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        address = request.POST.get('address')
        apartment = request.POST.get('apartment', '')
        floor = request.POST.get('floor')
        entrance = request.POST.get('entrance', '')
        region_id = request.POST.get('region')
        notes = request.POST.get('notes', '')
        
        # Дополнительные поля для юридическContinue
