from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, Sum, Count, Max
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import make_aware
from datetime import datetime

from ..models import Order, Client, Product, Route, RouteOrder, Container, Region, Driver


@login_required
def orders(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    orders_qs = Order.objects.all().order_by('-order_date')
    
    if search_query:
        orders_qs = orders_qs.filter(client__name__icontains=search_query)
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
    
    paginator = Paginator(orders_qs, 10)
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

        client = Client.objects.filter(phone=phone).first()
        if not client:
            messages.error(request, f"Клиент с номером телефона {phone} не найден.")
            return redirect('orders')

        product = Product.objects.get(id=product_id)

        delivery_address = f"{client.address}, {client.apartment or ''}, {client.floor or ''} этаж, {client.entrance or ''}".strip().replace(', ,', ',').replace(' ,', '')

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
        phone = request.POST.get('phone')
        product_id = request.POST.get('product')
        new_quantity = int(request.POST.get('quantity'))
        new_status = request.POST.get('status')

        client = Client.objects.filter(phone=phone).first()
        if not client:
            messages.error(request, f"Клиент с номером телефона {phone} не найден.")
            return redirect('orders')

        product = Product.objects.get(id=product_id)

        delivery_address = f"{client.address}, {client.apartment or ''}, {client.floor or ''} этаж, {client.entrance or ''}".strip().replace(', ,', ',').replace(' ,', '')

        driver = None
        if client.region and client.region.driver_set.exists():
            driver = client.region.driver_set.first()

        order.client = client
        order.product = product
        order.quantity = new_quantity
        order.status = new_status
        order.delivery_address = delivery_address
        order.driver = driver
        order.save()
        messages.success(request, "Заказ обновлён.")
        return redirect('orders')
    return redirect('orders')


@login_required
@permission_required('crm.delete_order', raise_exception=True)
def delete_order(request, order_id):
    order = Order.objects.get(id=order_id)
    order.delete()
    messages.success(request, "Заказ удалён.")
    return redirect('orders')


def create_route(request):
    if request.method == 'POST':
        order_ids = request.POST.getlist('orders')
        if order_ids:
            route = Route.objects.create()
            for i, order_id in enumerate(order_ids, start=1):
                RouteOrder.objects.create(
                    route=route,
                    order=Order.objects.get(id=order_id),
                    order_number=i
                )
            return redirect('route_detail', route_id=route.id)
    
    orders_qs = Order.objects.filter(status='planned')
    return render(request, 'create_route.html', {'orders': orders_qs})


def route_detail(request, route_id):
    route = Route.objects.prefetch_related('routeorder_set__order').get(id=route_id)
    return render(request, 'route_detail.html', {'route': route})


def routes(request):
    return render(request, 'routes.html')


def reports(request):
    """Render reports page with filters and orders list.

    Provides `regions`, `drivers`, `orders`, and `is_driver` in context so the
    template can safely decide which reports/exports to show.
    """
    regions = Region.objects.all()
    drivers = Driver.objects.all()

    orders = Order.objects.all().order_by('-order_date')

    # Detect whether current user is a driver and get related Driver object safely
    is_driver = False
    driver_obj = None
    try:
        # Accessing the reverse one-to-one related object may raise
        # `Driver.DoesNotExist` if absent; catch broadly to keep template safe.
        driver_obj = request.user.driver_profile
        if driver_obj:
            is_driver = True
    except Exception:
        is_driver = False

    # Apply filters from query params (only for non-driver users)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    region_id = request.GET.get('region')
    driver_id = request.GET.get('driver')

    if is_driver and driver_obj:
        orders = orders.filter(driver=driver_obj)
    else:
        # Filter by date strings in YYYY-MM-DD format if provided
        if date_from:
            try:
                df = datetime.strptime(date_from, '%Y-%m-%d').date()
                orders = orders.filter(order_date__date__gte=df)
            except Exception:
                pass
        if date_to:
            try:
                dt = datetime.strptime(date_to, '%Y-%m-%d').date()
                orders = orders.filter(order_date__date__lte=dt)
            except Exception:
                pass
        if region_id:
            orders = orders.filter(client__region_id=region_id)
        if driver_id:
            orders = orders.filter(driver_id=driver_id)
    # Пагинация
    paginator = Paginator(orders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Собираем строку запроса без параметра page, чтобы добавлять к ссылкам пагинации
    base_qs = request.GET.copy()
    if 'page' in base_qs:
        base_qs.pop('page')
    querystring = base_qs.urlencode()

    return render(request, 'reports.html', {
        'regions': regions,
        'drivers': drivers,
        'orders': page_obj.object_list,
        'is_driver': is_driver,
        'page_obj': page_obj,
        'querystring': querystring,
    })
