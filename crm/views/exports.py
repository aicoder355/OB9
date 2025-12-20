from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils.timezone import make_aware
from io import BytesIO
import csv
from datetime import timedelta, datetime

from ..models import Order, Container


@login_required
@permission_required('crm.view_order', raise_exception=True)
def export_orders_by_day_csv(request):
    today = timezone.now().date()
    end_date = today
    start_date = end_date - timedelta(days=6)  # 7 дней, включая сегодня
    orders_by_day = (Order.objects
                     .filter(order_date__date__range=[start_date, end_date])
                     .annotate(day=TruncDay('order_date'))
                     .values('day')
                     .annotate(count=Count('id'))
                     .order_by('day'))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_by_day.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Дата', 'Количество заказов'])
    
    orders_by_day_data = {entry['day'].strftime('%d.%m.%Y'): entry['count'] for entry in orders_by_day}
    days = [(start_date + timedelta(days=x)) for x in range(7)]
    for day in days:
        day_str = day.strftime('%d.%m.%Y')
        writer.writerow([day_str, orders_by_day_data.get(day_str, 0)])
    
    return response


@login_required
@permission_required('crm.view_order', raise_exception=True)
def export_revenue_by_month_csv(request):
    today = timezone.now().date()
    end_month = today.replace(day=1)  # Начало текущего месяца
    start_month = (end_month - timedelta(days=150)).replace(day=1)  # Примерно 5 месяцев назад + текущий
    revenue_by_month = (Order.objects
                        .filter(order_date__date__range=[start_month, end_month], status='delivered')
                        .annotate(month=TruncMonth('order_date'))
                        .values('month')
                        .annotate(revenue=Sum('quantity') * Sum('product__price'))
                        .order_by('month'))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="revenue_by_month.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Месяц', 'Выручка (руб.)'])
    
    revenue_by_month_data = {entry['month'].strftime('%m.%Y'): entry['revenue'] or 0 for entry in revenue_by_month}
    months = []
    current_month = start_month
    while current_month <= end_month:
        months.append(current_month)
        next_month = current_month.month + 1 if current_month.month < 12 else 1
        next_year = current_month.year if current_month.month < 12 else current_month.year + 1
        current_month = current_month.replace(month=next_month, year=next_year)
    for month in months:
        month_str = month.strftime('%m.%Y')
        writer.writerow([month_str, revenue_by_month_data.get(month_str, 0)])
    
    return response


@login_required
@permission_required('crm.view_order', raise_exception=True)
def export_orders_xlsx(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    region_id = request.GET.get('region')
    driver_id = request.GET.get('driver')

    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(order_date__gte=make_aware(datetime.strptime(date_from, '%Y-%m-%d')))
    if date_to:
        orders = orders.filter(order_date__lte=make_aware(datetime.strptime(date_to, '%Y-%m-%d')))
    if region_id:
        orders = orders.filter(client__region_id=region_id)
    if driver_id:
        orders = orders.filter(driver_id=driver_id)

    # Создаем DataFrame
    data = {
        'ID': [],
        'Дата': [],
        'Клиент': [],
        'Регион': [],
        'Адрес': [],
        'Продукт': [],
        'Количество': [],
        'Статус': [],
        'Водитель': []
    }

    for order in orders:
        data['ID'].append(order.id)
        data['Дата'].append(order.order_date.strftime('%d.%m.%Y %H:%M'))
        data['Клиент'].append(order.client.name)
        data['Регион'].append(order.client.region.name if order.client.region else 'Не указан')
        data['Адрес'].append(order.delivery_address)
        data['Продукт'].append(order.product.name)
        data['Количество'].append(order.quantity)
        data['Статус'].append(order.get_status_display())
        data['Водитель'].append(order.driver.name if order.driver else 'Не назначен')

    # Lazy import pandas to avoid heavy startup cost
    import pandas as pd
    df = pd.DataFrame(data)

    # Создаем Excel файл
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Заказы')

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=orders_report.xlsx'
    return response


@login_required
@permission_required('crm.view_container', raise_exception=True)
def export_containers_xlsx(request):
    region_id = request.GET.get('region')
    driver_id = request.GET.get('driver')

    containers = Container.objects.all()
    if region_id:
        containers = containers.filter(client__region_id=region_id)
    if driver_id:
        containers = containers.filter(client__orders__driver_id=driver_id).distinct()

    # Создаем DataFrame
    data = {
        'ID': [],
        'Продукт': [],
        'Клиент': [],
        'Регион': [],
        'Количество': [],
        'Местоположение': [],
    }

    for container in containers:
        data['ID'].append(container.id)
        data['Продукт'].append(container.product.name)
        data['Клиент'].append(container.client.name if container.client else '-')
        data['Регион'].append(container.client.region.name if container.client and container.client.region else 'Не указан')
        data['Количество'].append(container.quantity)
        data['Местоположение'].append('У клиента' if container.is_at_client else 'На складе')

    # Lazy import pandas
    import pandas as pd
    df = pd.DataFrame(data)

    # Создаем Excel файл
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Тара')

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=containers_report.xlsx'
    return response
