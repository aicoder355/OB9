from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, Sum

from ..models import Container, Client, Product


@login_required
def containers(request):
    search_query = request.GET.get('search', '')
    
    containers_qs = Container.objects.all().order_by('id')
    
    if search_query:
        containers_qs = containers_qs.filter(Q(product__name__icontains=search_query) | Q(client__name__icontains=search_query))
    
    paginator = Paginator(containers_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    low_stock_products = Container.get_low_stock_products()
    if low_stock_products:
        messages.warning(request, f"Низкий уровень тары на складе: {', '.join([f'{p[0].name} ({p[1]} шт.)' for p in low_stock_products])}")

    low_stock_container_ids = []
    for container in page_obj:
        if not container.is_at_client:
            for product, quantity in low_stock_products:
                if container.product.id == product.id and quantity < 10:
                    low_stock_container_ids.append(container.id)
                    break

    return render(request, 'containers.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'clients': Client.objects.all(),
        'products': Product.objects.all(),
        'can_add_container': request.user.has_perm('crm.add_container'),
        'can_change_container': request.user.has_perm('crm.change_container'),
        'can_delete_container': request.user.has_perm('crm.delete_container'),
        'low_stock_products': low_stock_products,
        'low_stock_container_ids': low_stock_container_ids,
    })


@login_required
@permission_required('crm.add_container', raise_exception=True)
def create_container(request):
    if request.method == 'POST':
        client_id = request.POST.get('client') or None
        Container.objects.create(
            product_id=request.POST.get('product'),
            client_id=client_id,
            quantity=request.POST.get('quantity'),
            is_at_client=request.POST.get('is_at_client') == 'True'
        )
        messages.success(request, "Тара добавлена.")
        return redirect('containers')
    return redirect('containers')


@login_required
@permission_required('crm.change_container', raise_exception=True)
def edit_container(request):
    if request.method == 'POST':
        container = Container.objects.get(id=request.POST.get('container_id'))
        container.product_id = request.POST.get('product')
        container.client_id = request.POST.get('client') or None
        container.quantity = request.POST.get('quantity')
        container.is_at_client = request.POST.get('is_at_client') == 'True'
        container.save()
        messages.success(request, "Тара обновлена.")
        return redirect('containers')
    return redirect('containers')


@login_required
@permission_required('crm.change_container', raise_exception=True)
def return_container(request, container_id):
    container = Container.objects.get(id=container_id)
    if container.is_at_client:
        container.is_at_client = False
        container.client_id = None
        container.save()
        messages.success(request, "Тара возвращена на склад.")
    return redirect('containers')


@login_required
@permission_required('crm.change_container', raise_exception=True)
def bulk_return_containers(request):
    if request.method == 'POST':
        client_id = request.POST.get('client')
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))

        client = Client.objects.get(id=client_id)
        product = Product.objects.get(id=product_id)

        containers = Container.objects.filter(client=client, product=product, is_at_client=True)
        total_quantity = containers.aggregate(total=Sum('quantity'))['total'] or 0

        if quantity > total_quantity:
            messages.error(request, f"У клиента {client.name} недостаточно тары ({product.name}) для возврата.")
            return redirect('containers')

        if quantity == total_quantity:
            containers.delete()
        else:
            for container in containers:
                if quantity <= 0:
                    break
                if container.quantity <= quantity:
                    quantity -= container.quantity
                    container.delete()
                else:
                    container.quantity -= quantity
                    container.save()
                    quantity = 0

        warehouse_container = Container.objects.filter(product=product, is_at_client=False).first()
        if warehouse_container:
            warehouse_container.quantity += (total_quantity - quantity)
            warehouse_container.save()
        else:
            Container.objects.create(
                product=product,
                quantity=(total_quantity - quantity),
                is_at_client=False
            )

        messages.success(request, f"Возвращено {total_quantity - quantity} x {product.name} на склад.")
        return redirect('containers')

    return render(request, 'containers.html', {
        'clients': Client.objects.all(),
        'products': Product.objects.all(),
    })


@login_required
@permission_required('crm.delete_container', raise_exception=True)
def delete_container(request, container_id):
    container = Container.objects.get(id=container_id)
    container.delete()
    messages.success(request, "Тара удалена.")
    return redirect('containers')
